from pathlib import Path
import json,os,re,unreal as u
ROOT=Path(__file__).resolve().parents[2];OUT=Path(os.environ['KZ_PARRY_PHOTO_OUT'])
BASE='/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Reference';DEST=BASE+'/PP_Player_Parry_Reference'
LIB=u.MaterialEditingLibrary;EAL=u.EditorAssetLibrary
H={};s=(ROOT/'Scripts/Art/author_monster_hit_flash_20261012.py').read_text(encoding='utf-8').split('\ntry:\n    flash = particle()')[0]
exec(compile(s,'cascade_helpers','exec'),H);H.update(OUT=OUT,DEST=DEST)
ps=u.load_asset(DEST);assert ps
t=H['export'](ps,'Before.t3d');converted=[];enabled=[]
for match in re.finditer(r'^      Begin Object Name="([^\"]+)" .*?^      End Object',t,re.M|re.S):
    if not match.group(1).startswith('ParticleLODLevel'):continue
    path=re.search(r"ExportPath=\"[^']+'([^']+)'",match.group(0)).group(1)
    lod=u.load_object(None,path);assert lod
    if 'ParticleModuleTypeDataGpu' in match.group(0):
        H['set_owned'](lod,'TypeDataModule','None');converted.append(path)
    # Original flare-circle emitters are disabled. Photo reconstruction enables only those two.
    if any(x in path for x in ['ParticleSpriteEmitter_2.','ParticleSpriteEmitter_13.']):
        H['set_owned'](lod,'bEnabled','True');enabled.append(path)
        ref=re.search(r'RequiredModule="[^\x27]+\x27([^\x27]+)\x27"',match.group(0)).group(1)
        req=u.load_object(None,ref if ref.startswith('/') else ps.get_path_name().split(':')[0]+':'+ref.split(':')[-1]);assert req
        H['set_owned'](req,'bEnabled','True')
H['rebuild'](ps);assert EAL.save_loaded_asset(ps,only_if_is_dirty=False)

m=u.load_asset(BASE+'/M_FM_fluid_A');nodes=list(LIB.get_material_expressions(m))
sample=next(n for n in nodes if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='Tex_OPA')
pc=LIB.create_material_expression(m,u.MaterialExpressionParticleColor)
edge=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'Parry photo TEMP continuous card edge' in str(n.get_editor_property('description')))
def custom(code,inputs,typ):
    a=LIB.create_material_expression(m,u.MaterialExpressionCustom);a.set_editor_property('code',code);a.set_editor_property('output_type',typ)
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    a.set_editor_property('inputs',pins);return a
def link(a,p,b,q):assert LIB.connect_material_expressions(a,p,b,q)
alpha=custom('return saturate(Alpha)*saturate(Density)*Edge;',['Alpha','Density','Edge'],u.CustomMaterialOutputType.CMOT_FLOAT1)
link(pc,'A',alpha,'Alpha');link(sample,'R',alpha,'Density');link(edge,'',alpha,'Edge')
assert LIB.connect_material_property(alpha,'',u.MaterialProperty.MP_OPACITY)
for existing in nodes:
    if isinstance(existing,u.MaterialExpressionCustom) and str(existing.get_editor_property('code')).startswith(('return normalize(float3','return 1.0+Strength')):
        link(alpha,'',existing,'Mask')
tint=next(n for n in nodes if isinstance(n,u.MaterialExpressionVectorParameter) and str(n.get_editor_property('parameter_name'))=='ParryPhotoTint')
color=custom('return Density*max(Color.r,max(Color.g,Color.b))*Tint;',['Density','Color','Tint'],u.CustomMaterialOutputType.CMOT_FLOAT3)
link(sample,'R',color,'Density');link(pc,'RGB',color,'Color');link(tint,'',color,'Tint')
assert LIB.connect_material_property(color,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
assert not list(LIB.recompile_material(m));assert EAL.save_loaded_asset(m,only_if_is_dirty=False)
for name in ['FMI_fluid_A_15','FMI_fluid_A_12','FMI_fluid_A_11','FMI_fluid_A_13']:
    mi=u.load_asset(BASE+'/MI_'+name);LIB.set_material_instance_scalar_parameter_value(mi,'ParryRefractionIOROffset',0)
    assert EAL.save_loaded_asset(mi,only_if_is_dirty=False)
(OUT/'Repair.json').write_text(json.dumps({'status':'passed','cpu_adapted_lods':converted,'photo_enabled_original_disabled_circles':enabled,'tuning_source':'Assistant reconstruction; source GPU rendering not visible; enabled original disabled rings and reconstructed source R-density alpha. Not native source pixel parity.'},indent=2),encoding='utf-8')
