from pathlib import Path
import hashlib,json,os,stat,shutil,subprocess
MAIN=Path(__file__).resolve().parents[2];WORK=MAIN.parent.parent/'Khazan_SlamDistortWork_20261012/Khazan';OUT=MAIN/'Metadata/AnimationTimingKnockback_20261012'
assert not (OUT/'KnockbackBaseline.json').exists()
source=(MAIN/'Scripts/Animation/prepare_animation_fps_repair_20261012.py').read_text(encoding='utf-8')
start=source.index('def writable(');end=source.index('\npaths=',start)
exec(compile(source[start:end],__file__,'exec'))
rows={}
for family in ['Swordsman','SwordShield','HeavySwordsman','HalberdElite']:
    folder='Content/Monsters/'+family+'/Data';writable(folder)
    rel=folder+'/DA_Character_'+family+'.uasset';rows[rel]=hashlib.sha256((MAIN/rel).read_bytes()).hexdigest()
    d=OUT/'KnockbackBefore'/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(MAIN/rel,d);shutil.copyfile(MAIN/rel,WORK/rel)
writable('Content/Data/Character/Reactions')
(OUT/'KnockbackBaseline.json').write_text(json.dumps({'files':rows,'new_asset':'Content/Data/Character/Reactions/CF_Monster_Knockback_Deceleration.uasset','tuning':'Assistant TEMP normalized curve 2u-u*u; current distances and reaction deadline retained'},indent=2)+'\n',encoding='utf-8')
print('KNOCKBACK_ASSETS_STAGED',len(rows))
