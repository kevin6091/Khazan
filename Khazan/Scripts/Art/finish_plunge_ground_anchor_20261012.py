"""Keep landing debris under the actual feet when the blade overlaps a wall."""
from pathlib import Path
import os,json,hashlib,shutil,unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=Path(os.environ['KZ_COMBAT_FINISH_OUT'])
path='/Game/_Art/Player/Animation/InGame/DAS/FallAttack/AM_DAS_FallAttack'
file=ROOT/('Content/'+path.removeprefix('/Game/')+'.uasset')
planfile=ROOT/'Metadata/CombatFinishFollowup_20261012/Authored.json';plan=json.loads(planfile.read_text(encoding='utf-8'))
row=next(r for r in plan['montages'] if r['path']==path);assert hashlib.sha256(file.read_bytes()).hexdigest()==row['after']
shutil.copy2(file,OUT/'Before.uasset');shutil.copy2(planfile,OUT/'AuthoredBefore.json')
montage=u.load_asset(path);count=0
for event in u.AnimationLibrary.get_animation_notify_events(montage):
    parent=event.get_editor_property('notify')
    if not isinstance(parent,u.KZAnimNotify_CombatEffect):continue
    for child in [parent]+list(parent.get_editor_property('BatchedEffects')):
        if str(child.get_editor_property('EventId'))=='KZExtra_PlungeGround':
            child.set_editor_property('SourceSocket','None');child.set_editor_property('RelativeLocation',u.Vector(0,0,0));count+=1
assert count==2
assert u.EditorAssetLibrary.save_loaded_asset(montage,only_if_is_dirty=False)
row['after']=hashlib.sha256(file.read_bytes()).hexdigest()
next(r for r in plan['extra_effects'] if r['id']=='KZExtra_PlungeGround')['socket']='None'
plan['plunge_ground_anchor_revision']='Actual grounded actor feet; prevents a weapon-tip XY inside walls from suppressing landing dust. Explicit presentation adapter, no gameplay collision change.'
planfile.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'Applied.json').write_text(json.dumps({'asset':path,'changed_fields':['SourceSocket','RelativeLocation'],'start_end_objects':count,'sha256':row['after'],'policy':plan['plunge_ground_anchor_revision']},indent=2),encoding='utf-8')
