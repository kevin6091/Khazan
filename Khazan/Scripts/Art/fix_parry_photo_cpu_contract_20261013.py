"""Correct two GPU-to-CPU sprite contracts observed by the native test."""
from pathlib import Path
import json,os,re,shutil,unreal as u
ROOT=Path(__file__).resolve().parents[2];OUT=Path(os.environ['KZ_PARRY_PHOTO_OUT'])
BASE='/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Reference';DEST=BASE+'/PP_Player_Parry_Reference'
EAL=u.EditorAssetLibrary;LIB=u.MaterialEditingLibrary
for name in ['PP_Player_Parry_Reference','M_Parry_Distortion']:
    shutil.copy2(ROOT/('Content/'+BASE.removeprefix('/Game/')+'/'+name+'.uasset'),OUT/(name+'_Before.uasset'))
H={};s=(ROOT/'Scripts/Art/author_monster_hit_flash_20261012.py').read_text(encoding='utf-8').split('\ntry:\n    flash = particle()')[0]
exec(compile(s,'cascade_helpers','exec'),H);H.update(OUT=OUT,DEST=DEST)
ps=u.load_asset(DEST);before=H['export'](ps,'Before.t3d')
changed=[]
for idx in [2,13]:
    block=next(x.group(0) for x in re.finditer(r'^      Begin Object Name="([^\"]+)" .*?^      End Object',before,re.M|re.S) if ('ParticleSpriteEmitter_'+str(idx)+'.ParticleLODLevel') in x.group(0)[:500])
    ref=re.search(r'Modules\(\d+\)="/Script/Engine.ParticleModuleSize\x27([^\x27]+)\x27"',block).group(1)
    size=u.load_object(None,ref if ref.startswith('/') else ps.get_path_name()+':'+ref.split(':')[-1]);assert size
    # Original GPU start size is (250,0,0). Explicit equal CPU axes avoid a
    # zero-height card. Half extent is assistant TEMP camera/footprint tuning.
    H['dist'](size,'StartSize','DistributionVectorConstant',{'Constant':'(X=125,Y=125,Z=125)'})
    changed.append(size.get_path_name())
H['rebuild'](ps);assert EAL.save_loaded_asset(ps,only_if_is_dirty=False)
m=u.load_asset(BASE+'/M_Parry_Distortion')
mask=next(n for n in LIB.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('code')).startswith('float r=length(UV'))
age=LIB.create_material_expression(m,u.MaterialExpressionParticleRelativeTime)
assert LIB.connect_material_expressions(age,'',mask,'Alpha')
# Native source refrac ParticleColor.A is exactly zero. The original shader
# does not expose its mask contract. A finite relative-age envelope replaces
# that incompatible CPU assumption, without changing the source lifetime.
mask.set_editor_property('code','float r=length(UV*2-1);return exp(-4*r*r)*(1-smoothstep(.82,1,r))*saturate(1-Alpha);')
mask.set_editor_property('description','Assistant TEMP distortion age envelope; source refrac ParticleColor.A=0; border normal flat/IOR1, source lifespan retained')
assert not list(LIB.recompile_material(m));assert EAL.save_loaded_asset(m,only_if_is_dirty=False)
(OUT/'Contract.json').write_text(json.dumps({'status':'saved','rhi_pending':True,'circle_size_modules':changed,'source_gpu_start_size_cm':[250,0,0],'temporary_cpu_start_size_cm':[125,125,125],'reason':'Explicit square axes and current camera footprint; not original size parity','native_refraction_alpha_observed':0,'distortion_fade':'1-ParticleRelativeTime; source particle life unchanged, assistant TEMP'},indent=2),encoding='utf-8')
