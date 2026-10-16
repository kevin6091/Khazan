"""Read-only fresh Main audit of effective variants, texture channels and retired trials."""
from pathlib import Path
import unreal,os,json,traceback
OUT=Path(os.environ['KZ_BLOOD_REFERENCE_OUT']);lib=unreal.MaterialEditingLibrary
d={'status':'running','asset_saves':0,'monsters':[],'materials':[],'retired_trial_referencers':{}}
try:
    for family in ['Swordsman','SwordShield','HeavySwordsman','HalberdElite','ApesStoneHandElite','Yetuga']:
        c=unreal.load_class(None,'/Game/Bluprints/Monsters/BP_Monster_'+family+'.BP_Monster_'+family+'_C');assert c
        a=unreal.get_default_object(c);blood=a.get_editor_property('HitBloodEffect');ground=a.get_editor_property('HitBloodDecalMaterial')
        assert blood.get_name()=='FP_Monster_HitBloodReference' and ground.get_name()=='M_Monster_HitBloodGround'
        d['monsters'].append({'family':family,'particle':blood.get_path_name(),'ground_material':ground.get_path_name(),'projector_cm':str(a.get_editor_property('HitBloodDecalSize')),'hold_seconds':a.get_editor_property('HitBloodDecalHoldSeconds'),'fade_seconds':a.get_editor_property('HitBloodDecalFadeSeconds'),'trace_cm':a.get_editor_property('HitBloodGroundTraceDistance')})
    for name in ['M_Monster_HitBloodGround','M_Monster_HitBloodFluid']:
        m=unreal.load_asset('/Game/_Art/Effects/Combat/Blood/'+name);assert m
        nodes=lib.get_material_expressions(m);tex=[];code=[]
        for n in nodes:
            if isinstance(n,unreal.MaterialExpressionTextureSampleParameter2D):
                t=n.get_editor_property('texture');assert not t.get_editor_property('srgb');assert n.get_editor_property('sampler_type')==unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
                tex.append({'asset':t.get_path_name(),'srgb':False,'sampler':'LinearColor','never_stream':t.get_editor_property('never_stream'),'size':[t.blueprint_get_size_x(),t.blueprint_get_size_y()]})
            if isinstance(n,unreal.MaterialExpressionCustom):code.append(n.get_editor_property('code'))
        scalars={str(n.get_editor_property('parameter_name')):n.get_editor_property('default_value') for n in nodes if isinstance(n,unreal.MaterialExpressionScalarParameter)}
        vectors={str(n.get_editor_property('parameter_name')):str(n.get_editor_property('default_value')) for n in nodes if isinstance(n,unreal.MaterialExpressionVectorParameter)}
        d['materials'].append({'asset':m.get_path_name(),'textures':tex,'code':code,'scalars':scalars,'vectors':vectors,'shading_model':str(m.get_editor_property('shading_model')),'emissive_connected':bool(lib.get_material_property_input_node(m,unreal.MaterialProperty.MP_EMISSIVE_COLOR)),'eye_adaptation_inverse':any(isinstance(n,unreal.MaterialExpressionEyeAdaptationInverse) for n in nodes),'receiver_world_position':any(isinstance(n,unreal.MaterialExpressionWorldPosition) for n in nodes),'lighting':str(m.get_editor_property('translucency_lighting_mode')),'roughness_connected':bool(lib.get_material_property_input_node(m,unreal.MaterialProperty.MP_ROUGHNESS)),'metallic_connected':bool(lib.get_material_property_input_node(m,unreal.MaterialProperty.MP_METALLIC)),'decal_lifetime_opacity':any(isinstance(n,unreal.MaterialExpressionDecalLifetimeOpacity) for n in nodes)})
    assert d['materials'][0]['decal_lifetime_opacity'];assert 'max(T.r,T.b)' in '\n'.join(d['materials'][1]['code'])
    assert not d['materials'][0]['roughness_connected'] and not d['materials'][0]['metallic_connected']
    registry=unreal.AssetRegistryHelpers.get_asset_registry()
    options=unreal.AssetRegistryDependencyOptions(include_soft_package_references=True,include_hard_package_references=True,include_searchable_names=False,include_soft_management_references=True,include_hard_management_references=True)
    for name in ['M_Monster_HitBloodSheet','FT_Monster_HitBloodSheetMask']:
        path='/Game/_Art/Effects/Combat/Blood/'+name
        d['retired_trial_referencers'][path]=[str(p) for p in (registry.get_referencers(path,options) or [])]
    d['status']='passed'
except Exception:d.update(status='failed',error=traceback.format_exc());unreal.log_error(d['error'])
(OUT/'SavedAudit.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
