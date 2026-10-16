import runpy,pathlib,json,unreal
out=pathlib.Path(r'C:/Users/user/Desktop/GitProject/Khazan/Khazan/Metadata/CombatReaction_20261008')
d=json.loads((out/'AnimationClassification.json').read_text(encoding='utf8'))
assets=[{'asset':r['current_path'],'expects_root_motion':False,'motion_bones':['Root']} for r in d['player']['reaction_source_clips'] if 'DamageAir' in r['current_path']]
assets += [{'asset':r['CurrentAsset'],'expects_root_motion':False,'motion_bones':['Root']} for r in d['enemy_clips'] if r['Family']=='Swordsman' and '/Damage_Air_F_Up' in r['CurrentAsset']]
runpy.run_path(r'C:/Users/user/.codex/skills/unreal-root-motion-repair/scripts/audit_root_motion.py',init_globals={'ROOT_MOTION_AUDIT_ASSETS':assets,'ROOT_MOTION_AUDIT_REPORT':str(out/'InPlaceReactionRootAudit.json')},run_name='__main__')
