"""Local flash alpha/material and outward contact clearance, not blood tuning."""
from pathlib import Path
import hashlib,json,re,shutil,unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Metadata/HitFlashCorrection_20261012'
HELP={}
source=(ROOT/'Scripts/Art/author_monster_hit_flash_20261012.py').read_text(encoding='utf-8').split('\ntry:\n    flash = particle()')[0]
exec(compile(source,'hit_flash_definitions_only','exec'),HELP)
set_owned=HELP['set_owned'];new=HELP['new'];dist=HELP['dist'];token=HELP['token'];export=HELP['export'];rebuild=HELP['rebuild']
EAL=u.EditorAssetLibrary;LIB=u.MaterialEditingLibrary
plan=json.loads((OUT/'Authored.json').read_text(encoding='utf-8'))
assert not (OUT/'VisibilityRefined.json').exists()
mi_path='/Game/_Art/Effects/Combat/AttackContact/M_Monster_HitFlameFlash'
assert not (OUT/'VisibilityRefined.json').exists()
mi=u.load_asset(mi_path) if EAL.does_asset_exist(mi_path) else u.AssetToolsHelpers.get_asset_tools().create_asset('M_Monster_HitFlameFlash',mi_path.rsplit('/',1)[0],u.Material,u.MaterialFactoryNew());assert mi
# The only saved candidate was created by this task; resume graph authoring
# from that exact owned path after a pre-save particle-binding failure.
LIB.delete_all_material_expressions(mi)
mi.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
mi.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
mi.set_editor_property('two_sided',True)
LIB.set_material_usage(mi,u.MaterialUsage.MATUSAGE_PARTICLE_SPRITES)
def node(cls):return LIB.create_material_expression(mi,cls,0,0)
def link(a,out,b,inp):assert LIB.connect_material_expressions(a,out,b,inp)
tex=node(u.MaterialExpressionTextureSample)
tex.set_editor_property('texture',u.load_asset('/Game/_Art/Effects/Shared/Textures/BBQ_Texture/Flare/FT_Flare_004_LSY'))
tex.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR if tex.get_editor_property('texture').get_editor_property('srgb') else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
pc=node(u.MaterialExpressionParticleColor)
alpha=node(u.MaterialExpressionMultiply);link(tex,'R',alpha,'A');link(pc,'A',alpha,'B')
depth=node(u.MaterialExpressionDepthFade);depth_pins=list(LIB.get_material_expression_input_names(depth));assert len(depth_pins)==2;link(alpha,'',depth,str(depth_pins[0]))
distance=node(u.MaterialExpressionScalarParameter);distance.set_editor_property('parameter_name','HitFlashDepthFadeCm');distance.set_editor_property('default_value',8)
link(distance,'',depth,str(depth_pins[1]))
uv=node(u.MaterialExpressionTextureCoordinate)
edge=node(u.MaterialExpressionCustom);i=u.CustomInput();i.set_editor_property('input_name','UV');edge.set_editor_property('inputs',[i]);edge.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
edge.set_editor_property('code','float2 d=min(UV,1.0-UV); return smoothstep(0.0,0.04,min(d.x,d.y));')
link(uv,'',edge,'UV')
opacity=node(u.MaterialExpressionMultiply);link(depth,'',opacity,'A');link(edge,'',opacity,'B')
assert LIB.connect_material_property(opacity,'',u.MaterialProperty.MP_OPACITY)
colour=node(u.MaterialExpressionMultiply);link(tex,'R',colour,'A');link(pc,'RGB',colour,'B')
power=node(u.MaterialExpressionScalarParameter);power.set_editor_property('parameter_name','HitFlashEmissivePower');power.set_editor_property('default_value',12)
glow=node(u.MaterialExpressionMultiply);link(colour,'',glow,'A');link(power,'',glow,'B')
inverse=node(u.MaterialExpressionEyeAdaptationInverse);link(glow,'',inverse,'LightValueInput')
assert LIB.connect_material_property(inverse,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
assert not list(LIB.recompile_material(mi))
EAL.set_metadata_tag(mi,'KZHitFlashVisibility','Source OPA_Depthfade300cm -> TEMP8cm; additive flash. Shared parry material unchanged. TEMP40cm outward static particle clearance avoids occlusion inside capsule/body.')
assert EAL.save_loaded_asset(mi,only_if_is_dirty=False)
changes=[]
for path,key in [(plan['particle']['path'],'Flash'),(plan['blood_binding']['path'],'Blood')]:
    asset=u.load_asset(path);assert asset
    f=ROOT/('Content/'+path.removeprefix('/Game/')+'.uasset')
    backup=OUT/'BeforeVisibility'/f.relative_to(ROOT);backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,backup)
    before=hashlib.sha256(f.read_bytes()).hexdigest()
    assert before==(plan['particle']['sha256'] if key=='Flash' else plan['blood_binding']['after'])
    text=export(asset,key+'BeforeVisibility.t3d')
    exports={name:path for name,path in re.findall(r'Name="([^"]+)" ExportPath="[^\']+\'([^\']+)\'"',text)}
    def resolve(p):
        if not p.startswith('/'):
            p=exports.get(p.rsplit(':',1)[-1].rsplit('.',1)[-1],asset.get_path_name()+':'+p)
        obj=u.load_object(None,p);assert obj,p
        return obj
    for index,name in [(1,'Blue'),(14,'Purple'),(2,'Red')]:
        emitter_name='KZHitFlash'+name if key=='Blood' else 'ParticleSpriteEmitter_'+str(index)
        e=u.load_object(None,asset.get_path_name()+':'+emitter_name)
        lod=u.load_object(None,e.get_path_name()+'.ParticleLODLevel_0')
        block=re.search(r'^   Begin Object Name="'+emitter_name+r'" .*?^   End Object',text,re.M|re.S).group(0)
        required_path=re.search(r'RequiredModule="[^\']+\'([^\']+)\'"',block).group(1)
        req=resolve(required_path);req.set_editor_property('Material',mi)
        loc=new('ParticleModuleLocation',asset,('KZHitFlash'+name+'_Location' if key=='Blood' else 'HitFlashLocation_'+str(index)))
        dist(loc,'StartLocation','DistributionVectorConstant',{'Constant':'(X=40,Y=0,Z=0)'})
        module_paths=re.findall(r'Modules\(\d+\)="[^\']+\'([^\']+)\'"',block)
        modules=[resolve(p) for p in module_paths]
        assert len(modules)==5 and all(modules)
        modules=[m for m in modules if m.get_class().get_name()!='ParticleModuleParameterDynamic']
        assert len(modules)==4
        set_owned(lod,'Modules','('+','.join(token(m) for m in modules+[loc])+')')
    rebuild(asset)
    assert EAL.save_loaded_asset(asset,only_if_is_dirty=False)
    after=hashlib.sha256(f.read_bytes()).hexdigest()
    changes.append({'path':path,'before':before,'after':after})
    if key=='Flash':plan['particle']['sha256']=after
    else:plan['blood_binding']['after']=after
plan['visibility']={'material':mi_path,'source_depth_fade_cm':300,'temporary_depth_fade_cm':8,
                    'temporary_outward_offset_cm':40,'temporary_emissive_power':12,'temporary_edge_feather_uv':.04,
                    'texture_source':'/Game/_Art/Effects/Shared/Textures/BBQ_Texture/Flare/FT_Flare_004_LSY',
                    'blend':'Additive','moving_sparks':False}
shutil.copy2(OUT/'Authored.json',OUT/'AuthoredBeforeVisibility.json')
(OUT/'Authored.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
(OUT/'VisibilityRefined.json').write_text(json.dumps({'status':'passed','changes':changes,**plan['visibility']},indent=2),encoding='utf-8')
print('HIT_FLASH_VISIBILITY_REFINED')
