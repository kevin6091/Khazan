"""Use the existing actual-viewport test driver with the scoped case catalog."""
from pathlib import Path
import os, json
import unreal

main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
out=Path(os.environ['KZ_MONSTER_REPAIR_OUT'])
probe=json.loads((main/'Metadata/GiantVFX_20261013/Probe02/Probe.json').read_text(encoding='utf-8'))
mode=os.environ.get('KZ_GIANT_REVIEW','before')
authored=main/'Metadata/GiantVFX_20261013/AssetAuthor02/Author.json'
particle_map=json.loads(authored.read_text(encoding='utf-8'))['particles'] if authored.exists() else {}
cases=[]
if mode=='patterns':
    for family in ['ApesStoneHandElite','Yetuga']:
        data=next(f for f in probe['families'] if f['family']==family)
        for term in ['NormalAtk01_Step1','DempseyRoll_Step1','JumpAtk_Step1','FastBall_Step1','IceBreath_Step1','Armageddon_Step1']:
            p=next((n['id'] for n in data['nodes'] if n['id']==term),None)
            if p:cases.append([family+'_'+p,family,'pattern',p])
for family in ['ApesStoneHandElite','Yetuga']:
    if mode in ['patterns','field','dust']:continue
    sequences=[p for p in probe['sequences'] if '/'+family+'/' in p and any(x in p for x in ['/Attack/','/Movement/','/Locomotion/','/Move/'])]
    if mode in ['before','focus']:
        chosen=[]
        for term in ['Walk_F','Smash','IceBreath','JumpAtk','DempseyRoll','FastBall','Roar']:
            match=next((p for p in sequences if term in p and not any(t in p for t in ['End','Back','Stun'])),None)
            if match and match not in chosen:chosen.append(match)
        sequences=chosen[:5]
    for p in sequences:
        cases.append([p.split('.')[-1],family,'animation',p])
if mode in ['all','quality','focus','dust']:
    for p in probe['systems']:
        if mode=='dust' and 'Slashdust_HalfCircle_Left_01' not in p:continue
        if mode in ['quality','focus'] and not any(s in p for s in ['Footstep_Strong_01','Smash_strong_01','Smash_normal_01','Charge_01_2','Mouth_Dust_02','FP_Roar_001','Rock_Explosion_01','Slashdust_HalfCircle_Left']):continue
        cases.append([p.split('.')[-1],'Yetuga','particle',particle_map.get(p,p)])
for family in ['ApesStoneHandElite','Yetuga']:
    ids=['COI_ApesStoneHand_E_FastBall_OBJ'] if family=='ApesStoneHandElite' else ['COI_Yetuga_FastBall_OBJ','COI_Yetuga_IceBreath_Field_OBJ']
    for name in ids:cases.append([name,family,'field' if 'Field_OBJ' in name else 'object',name])
if mode=='field':cases=[c for c in cases if 'Field_OBJ' in c[0]]
if mode=='dust':cases=[c for c in cases if c[2]=='particle']
assert cases
(out/'GiantReviewCases.tsv').write_text('\n'.join('\t'.join(c) for c in cases),encoding='utf-8')
source=(main/'Scripts/Engineering/monster_presentation_repair_editor_driver_20261011.py').read_text(encoding='utf-8')
source=source.replace("Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')]", "Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan'),Path('C:/Users/user/Desktop/GitProject/Khazan_GiantVFXWork_20261013/Khazan')]")
if os.environ.get('KZ_GIANT_SPARSE_FIXTURE')=='1':
    source=source.replace('START=time.monotonic();started=', "actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)\nfor actor in actors.get_all_level_actors():\n    if isinstance(actor,unreal.KZMonster):actors.destroy_actor(actor)\nreport['fixture']='Unsaved owned editor world removes unrelated placed NPCs; native test spawns actual saved giant BPs. No asset/map save.'\nSTART=time.monotonic();started=")
exec(compile(source,__file__,'exec'),globals())
