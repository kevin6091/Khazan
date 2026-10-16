"""Build actual finite animation patterns, retaining SB event provenance where present."""
from pathlib import Path
import ast, csv, json
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Metadata/EnemyAnimationOrganization_20261007'
renames=json.loads((OUT/'RenamePlan.json').read_text(encoding='utf-8'))['rows']
inv=json.loads((OUT/'Inventory.json').read_text(encoding='utf-8'))
library={r['OriginalPackage']:r for r in csv.DictReader((ROOT/'Content/_Art/Enemies/HeinMach/Metadata/AnimationStructure_20260909/AnimationLibrary.csv').open(encoding='utf-8-sig'))}
SOURCE=ROOT/'Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/Source'
events=json.loads((ROOT/'Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/PlaybackEventTimes.json').read_text(encoding='utf-8-sig'))['events']
# Reuse the exact current read-only parser; do not execute its historic authoring main.
tree=ast.parse((ROOT/'Scripts/Engineering/prepare_monster_animation_manifest.py').read_text(encoding='utf-8-sig'))
scope=dict(ROOT=ROOT,SOURCE=SOURCE,library=library,events=events,json=json)
for fn in [n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['load','reference_package','summarize_skill']]:
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(ROOT/'Scripts/Engineering/prepare_monster_animation_manifest.py'),'exec'),scope)
audits={}
for family,paths in inv['skill_sources'].items():
    audits[family]=[]
    for p in paths:
        if '/Skill/' not in p: continue
        try: audits[family].append(scope['summarize_skill'](ROOT/p))
        except Exception as e: audits[family].append(dict(skill=Path(p).stem,source_file=p,unavailable=str(e)))
(OUT/'AllSavedSkillAudit.json').write_text(json.dumps(audits,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

old=json.loads((ROOT/'Metadata/MonsterAI_20261006/AuthoringPlan.json').read_text(encoding='utf-8'))
patterns={p['family']:list(p['attacks']) for p in old}
used={f:{s['playback'] for p in ps for s in p['steps']} for f,ps in patterns.items()}
supplement={
 'Swordsman': [('Rush',['RushAttack_Start','RushAttack_Loop','RushAttack_Hit','RushAttack_End'],True),('Kick',['Push_Kick_Ready','Push_Kick_Loop','Push_Kick'],True)],
 'SwordShield': [],
 'HeavySwordsman': [('SwordSting',['SwordSting_Step1','SwordSting_Step2','SwordSting_Step3'],False),('SwordSwingTurnL',['SwordSwing_Turn_L'],True),('SwordSwingTurnR',['SwordSwing_Turn_R'],True)],
 'HalberdElite': [
  ('Swing',['Swing_01_New','Swing_02_New','Swing_03_New'],False),
  ('Pierce',['Pierce_01','Pierce_02'],False),('Push',['Push_01','Push_02'],False),
  ('EarlyPushFollowup',['Early_Push_01','Early_Push_02'],False),
  ('RoundAttack',['RoundAttack_Start','RoundAttack'],True),
  ('DownUpperSlash',['DownUpperSlash_01','DownUpperSlash_02'],False),
  ('SprintSwing',['SprintSwing_Start','SprintSwing_Loop','SprintSwing_End'],True),
  ('EarlySprintSwing',['SprintSwing_Start','SprintSwing_Loop','Early_SprintSwing_End'],True),
  ('BackDashCounter',['BackDashCounter_Start','BackDashCounter_Atk'],True),
  ('GuardCounterDown',['GuardCounter_Start','GuardCounter_Loop','GuardCounter_Down'],True),
  ('GuardCounterUpper',['GuardCounter_Start','GuardCounter_Loop','GuardCounter_Upper'],True),
  ('GuardCounterRecovery',['GuardCounter_Start','GuardCounter_Loop','GuardCounter_Failed'],True),
  ('ChargeAttack',['ChargeAttack_Start','ChargeAttack_Loop','ChargeAttack_End'],True),
  ('ChargeAttackFast',['ChargeAttack_Start_Fast','ChargeAttack_Loop','ChargeAttack_End_New'],True),
  ('Smash',['Smash_Start','Smash_End_New'],True),
  ('TurnAttack',['TurnAttack'],True),('TurnAttackFast',['TurnAttack_Fast'],True),
 ]}
all_rows={r['old']:r for r in renames if r['scope']=='ArtLibrary'}
result=[]
for family,entries in supplement.items():
    family_rows={r['label']:r for r in all_rows.values() if r['family']==family}
    for ident,names,continuous in entries:
        rows=[family_rows[n] for n in names]
        steps=[]
        for index,row in enumerate(rows):
            source_steps=[s for skill in audits[family] for s in skill.get('steps',[]) if s['playback']==row['old']]
            raw=source_steps[0] if source_steps else {}
            lib=library[row['original_package']]
            next_row=rows[index+1] if index+1<len(rows) else None
            # Use a matching authored next-step notify if this saved SB has one.
            matching=[]
            for skill in audits[family]:
                by_id={s['step']:s for s in skill.get('steps',[])}
                for s in skill.get('steps',[]):
                    if s['playback']!=row['old']:continue
                    for event in s['event_transitions']:
                        if next_row and event['next_step'] in by_id and by_id[event['next_step']]['playback']==next_row['old']:
                            matching.append(event)
            duration=float(lib['Seconds'])
            step=dict(step=f'Step{index+1}',original_package=row['original_package'],playback=row['new'],original_playback=row['old'],
                      seconds=duration,anim_play_rate=raw.get('anim_play_rate') or 1.0,anim_loop_count=1,
                      transition_seconds=min(e['playback_seconds'] for e in matching) if matching else duration,
                      target_step=f'Step{index+2}' if next_row else None,
                      timing_origin='OriginalSBNotify' if matching else 'Full imported playback duration',
                      original_loop_count=raw.get('anim_loop_count'),event_evidence=matching,
                      game_destination=f'/Game/Monsters/{family}/Animations/InGame/Attack/'+row['name'])
            steps.append(step);used[family].add(row['old'])
        result.append(dict(family=family,id=ident,continuous=continuous,steps=steps,
                           source_skills=[s['source_file'] for s in audits[family] if any(a['playback'] in {r['old'] for r in rows} for a in s.get('steps',[]))],
                           policy='Animation-only finite path; hit/guard/target event producers are not implemented',
                           blend_in=next((s.get('blend_alpha') for s in source_steps if s.get('blend_alpha') is not None),0.2),
                           blend_out=0.2))
missing={f:[r['label'] for r in all_rows.values() if r['family']==f and r['category']=='Attack' and r['old'] not in used[f]] for f in patterns}
assert not any(missing.values()),missing
for row in result:
    # Clip rate/FPS are preserved. Segment rates are source SB values or engine unit playback.
    if row['continuous']:
        row['timing_note']='Mandatory preparation/one finite loop/strike/recovery form one Ability node; no random windup-only cancellation.'
assert len({(r['family'],r['id']) for r in result})==len(result)
(OUT/'AttackExpansionPlan.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
(OUT/'AttackCoverage.json').write_text(json.dumps(dict(existing_patterns={f:len(ps) for f,ps in patterns.items()},new_patterns={f:sum(r['family']==f for r in result) for f in patterns},missing_attack_clips=missing,
 covered={f:sorted(ps) for f,ps in used.items()}),indent=2),encoding='utf-8')
print(json.dumps(dict(new_patterns=len(result),families={f:sum(r['family']==f for r in result) for f in patterns},missing=missing)))
