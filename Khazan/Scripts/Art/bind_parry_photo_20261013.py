"""Bind parry-only source-derived effect, refraction and original camera values."""
from pathlib import Path
import hashlib,json,os,re,shutil,unreal as u
ROOT=Path(__file__).resolve().parents[2];OUT=Path(os.environ['KZ_PARRY_PHOTO_OUT'])
BASE='/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Reference'
EAL=u.EditorAssetLibrary;LIB=u.MaterialEditingLibrary
report={'status':'running','saved':[]}

def save(a):
    assert EAL.save_loaded_asset(a,only_if_is_dirty=False)
    f=ROOT/('Content/'+a.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset')
    report['saved'].append({'path':a.get_path_name(),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})

try:
    # Refraction has zero normal offset and a neutral index outside its opacity.
    m=u.load_asset(BASE+'/M_FM_fluid_A');assert m
    alpha=LIB.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY)
    aout=LIB.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_OPACITY)
    assert alpha
    def node(cls):return LIB.create_material_expression(m,cls)
    def link(a,p,b,q):assert LIB.connect_material_expressions(a,p,b,q)
    normal=node(u.MaterialExpressionTextureSampleParameter2D);normal.set_editor_property('parameter_name','Tex_Refrac')
    normal.set_editor_property('texture',u.load_asset('/Game/_Art/Effects/Shared/Textures/Noise/FT_PerlinNoise_RG'))
    normal.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    def custom(code,inputs,typ):
        c=node(u.MaterialExpressionCustom);c.set_editor_property('code',code);c.set_editor_property('output_type',typ)
        ins=[]
        for name in inputs:
            i=u.CustomInput();i.set_editor_property('input_name',name);ins.append(i)
        c.set_editor_property('inputs',ins);return c
    n=custom('return normalize(float3((Noise.rg*2-1)*saturate(Mask),1));',['Noise','Mask'],u.CustomMaterialOutputType.CMOT_FLOAT3)
    link(normal,'RGB',n,'Noise');link(alpha,aout,n,'Mask');assert LIB.connect_material_property(n,'',u.MaterialProperty.MP_NORMAL)
    refr=custom('return 1.0+Strength*saturate(Mask);',['Strength','Mask'],u.CustomMaterialOutputType.CMOT_FLOAT1)
    strength=node(u.MaterialExpressionScalarParameter);strength.set_editor_property('parameter_name','ParryRefractionIOROffset');strength.set_editor_property('default_value',.06)
    link(strength,'',refr,'Strength');link(alpha,aout,refr,'Mask');assert LIB.connect_material_property(refr,'',u.MaterialProperty.MP_REFRACTION)
    EAL.set_metadata_tag(m,'KZParryRefraction','Assistant TEMP IOR offset .06; neutral outside continuous alpha; source ring/noise texture bindings retained')
    assert not list(LIB.recompile_material(m));save(m)

    src=ROOT/'Saved/Extracted/InGame_Playback_20261002/Metadata/BBQ/Content/_Kazan_/Design/Kazan/Skill/DualAxeSword/Common/Guard/AC_Kazan_DualAxeSword_Com_Guard_Suc_Just_L.json'
    data=json.loads(src.read_text(encoding='utf-8-sig'))
    mod=next(x for x in data if x.get('Type')=='xxCameraMod_Shake')['Properties']
    anim=next(x for x in data if x.get('Type')=='AnimComposite')['Properties']
    notify=next(n for n in anim['Notifies'] if 'CameraMod' in str(n))
    factory=u.BlueprintFactory();factory.set_editor_property('parent_class',u.LegacyCameraShake)
    camera=u.AssetToolsHelpers.get_asset_tools().create_asset('BP_Parry_SourceCameraShake',BASE,u.Blueprint,factory);assert camera
    u.BlueprintEditorLibrary.compile_blueprint(camera)
    cdo=u.get_default_object(EAL.load_blueprint_class(camera.get_path_name()))
    cdo.set_editor_property('single_instance',True)
    cdo.set_editor_property('oscillation_duration',notify['Duration'])
    cdo.set_editor_property('oscillation_blend_in_time',mod['FadeIn']['BlendTime'])
    cdo.set_editor_property('oscillation_blend_out_time',mod['FadeOut']['BlendTime'])
    loc=cdo.get_editor_property('loc_oscillation');y=loc.get_editor_property('y')
    y.set_editor_property('amplitude',mod['LocOscillation']['Y']['Amplitude']*mod['FinalScale'])
    y.set_editor_property('frequency',mod['LocOscillation']['Y']['Frequency'])
    zero=getattr(type(y.get_editor_property('initial_offset')),'EOO_OFFSET_ZERO')
    y.set_editor_property('initial_offset',zero);loc.set_editor_property('y',y);cdo.set_editor_property('loc_oscillation',loc)
    fov=cdo.get_editor_property('fov_oscillation');fov.set_editor_property('amplitude',mod['FOVOscillation']['Amplitude']*mod['FinalScale'])
    fov.set_editor_property('frequency',mod['FOVOscillation']['Frequency']);fov.set_editor_property('initial_offset',zero)
    cdo.set_editor_property('fov_oscillation',fov)
    EAL.set_metadata_tag(camera,'KZOriginalCameraSource',str(src.relative_to(ROOT))+':xxCameraMod_Shake_0/Notify.Duration; FinalScale applied once to amplitudes; finite LegacyCameraShake adaptation')
    u.BlueprintEditorLibrary.compile_blueprint(camera);save(camera)
    report['camera_source']={'file':str(src.relative_to(ROOT)),'properties':mod,'notify_duration':notify['Duration'],'calculated_y_amplitude_cm':-10,'calculated_fov_amplitude_degrees':.3,'native_original_camera_mode_parity':'unconfirmed; LegacyCameraShake adaptation'}

    guard=u.load_asset('/Game/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard');assert guard
    file=ROOT/'Content/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard.uasset'
    shutil.copy2(file,OUT/'GA_Player_Guard_Before.uasset')
    report['guard_before_sha256']=hashlib.sha256(file.read_bytes()).hexdigest()
    defaults=u.get_default_object(EAL.load_blueprint_class(guard.get_path_name()))
    defaults.set_editor_property('ParryImpactEffect',u.load_asset(BASE+'/PP_Player_Parry_Reference'))
    defaults.set_editor_property('ParryCameraShake',EAL.load_blueprint_class(camera.get_path_name()))
    u.BlueprintEditorLibrary.compile_blueprint(guard);save(guard)
    player=u.load_asset('/Game/Data/Character/DA_CharacterDefinition_Player')
    assert player.get_editor_property('HitReactions').get_editor_property('ImpactEffect') is None
    report['player_received_hit_effect']=None
    report['status']='passed'
except Exception as exc:
    report['status']='failed';report['error']=str(exc);raise
finally:
    (OUT/'Binding.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
