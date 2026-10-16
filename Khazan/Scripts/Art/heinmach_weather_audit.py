"""Fresh saved-scene contract audit; never changes the map or material graph."""
from pathlib import Path
import hashlib
import json
import re
import runpy
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
META=ROOT/'Content/_Art/Player/Environment/Rendering/Metadata/HeinMachWeather_20261006'
BASE='/Game/_Art/Player/Environment/Rendering/HeinMachWeather'
BEFORE=json.loads((META/'Before.json').read_text(encoding='utf-8'))
REFINE_META=ROOT/'Content/_Art/Player/Environment/Rendering/Metadata/HeinMachLookRefinement_20261006'
REFINED=json.loads((REFINE_META/'Applied.json').read_text(encoding='utf-8')) if (REFINE_META/'Applied.json').exists() else None
CONF=runpy.run_path(str(ROOT/'Scripts/Art/heinmach_weather_look.py')) if REFINED else None
REPORT={'background':True,'saved_assets_modified':False,'checks':{}}
world=unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
by={a.get_actor_label():a for a in actors}
assert len(by)==len(actors),'Duplicate level actor labels'


def pose(a):
    p,r,s=a.get_actor_location(),a.get_actor_rotation(),a.get_actor_scale3d()
    return [p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]


old=({label:{'pose':value['location']+value['rotation']+value['scale']} for label,value in json.loads(Path(REFINED['before_actor_snapshot']).read_text(encoding='utf-8'))['actors'].items()}
     if REFINED else {r['label']:r for r in BEFORE['actors']})
assert set(by)-set(old)==(set() if REFINED else {'HM_Environment_SourceSnow'})
assert not set(old)-set(by)
allowed=set() if REFINED else {'HM_Environment_SourceSkyMesh'}|{'HM_Environment_PP_HeinMach_Light_'+str(n) for n in range(209,216)}
differences=[label for label,row in old.items() if pose(by[label])!=row['pose']]
assert not set(differences)-allowed,differences
REPORT['checks']['actors']={'before':len(old),'after':len(by),'added':[] if REFINED else ['HM_Environment_SourceSnow'],'removed':[],
                             'changed_poses':differences,'all_other_poses_preserved':True,
                             'PlayerStarts':[{'label':a.get_actor_label(),'pose':pose(a)} for a in actors if isinstance(a,unreal.PlayerStart)]}
sky=by['HM_Environment_SourceSkyMesh'].get_component_by_class(unreal.StaticMeshComponent)
assert sky.get_editor_property('custom_depth_stencil_value')==252
assert sky.get_material(0).get_path_name().startswith(BASE+'/MI_HM_SourceSky_OP.')
REPORT['checks']['sky']={'stencil':252,'mesh':sky.get_editor_property('static_mesh').get_path_name(),
                         'material':sky.get_material(0).get_path_name(),'pose':pose(by['HM_Environment_SourceSkyMesh'])}
pp=[]
for a in actors:
    if not isinstance(a,unreal.PostProcessVolume):continue
    s=a.get_editor_property('settings')
    if REFINED:
        for field,expected in CONF['REALISM_GRADE'].items():
            value=s.get_editor_property(field)
            assert s.get_editor_property('override_'+field),(a.get_actor_label(),field,'override missing')
            actual=[getattr(value,c) for c in ('r','g','b','a') if hasattr(value,c)] if field=='scene_color_tint' else ([getattr(value,c) for c in ('x','y','z','w')] if isinstance(expected,tuple) else value)
            assert all(abs(x-y)<0.00001 for x,y in zip(actual,expected)) if isinstance(expected,tuple) else abs(actual-expected)<0.00001,(a.get_actor_label(),field,actual,expected)
    if not a.get_editor_property('unbound'):
        p,b=a.get_actor_bounds(False)
        assert min(b.x,b.y,b.z)>0,a.get_actor_label()
    pp.append({'label':a.get_actor_label(),'enabled':a.get_editor_property('enabled'),
               'unbound':a.get_editor_property('unbound'),'priority':a.get_editor_property('priority'),
               'radius_cm':a.get_editor_property('blend_radius'),'user_flags':s.get_editor_property('user_flags'),
               'EV100':[s.get_editor_property('auto_exposure_min_brightness'),s.get_editor_property('auto_exposure_max_brightness')]})
assert len(pp)==8
profiles_by_label={r['label']:r['profile'] for r in json.loads((META/'LookApplied.json').read_text())['volumes']}
assert all(r['user_flags']==(1 if profiles_by_label[r['label']]=='Cave1' else 0) for r in pp)
REPORT['checks']['volumes']=pp
comp=by['HM_Environment_SourceSnow'].get_component_by_class(unreal.NiagaraComponent)
system=comp.get_asset()
assert system.get_path_name().startswith(BASE+'/NS_HM_SourceSnow_TwoLayers.')
assert comp.get_editor_property('auto_activate') and not comp.get_editor_property('cast_shadow')
assert system.get_editor_property('bFixedBounds')
REPORT['checks']['snow']={'system':system.get_path_name(),'auto_activate':True,'cast_shadow':False,
                          'bounds':str(system.get_editor_property('FixedBounds')),'pose':pose(by['HM_Environment_SourceSnow'])}
lib=unreal.MaterialEditingLibrary
materials=[]
for name in ('M_HM_SourceSky','M_HM_RegionalLook','M_HM_SourceSnow','M_HM_SourceDust'):
    m=unreal.load_asset(BASE+'/'+name)
    assert lib.get_material_property_input_node(m,unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    row={'name':name,'emissive_connected':True}
    if name=='M_HM_RegionalLook':
        assert m.get_editor_property('disable_pre_exposure_scale')
        row['disable_pre_exposure_scale']=True
    if name in ('M_HM_SourceSnow','M_HM_SourceDust'):
        root=lib.get_material_property_input_node(m,unreal.MaterialProperty.MP_OPACITY)
        assert isinstance(root,unreal.MaterialExpressionComponentMask)
        assert [root.get_editor_property(c) for c in ('r','g','b','a')]==[False,False,False,True]
        assert m.get_editor_property('translucency_pass')==unreal.MaterialTranslucencyPass.MTP_BEFORE_DOF
        row.update(alpha_only=True,pass_before_DOF=True)
    materials.append(row)
REPORT['checks']['materials']=materials
profiles=[]
for key in ('OP','Blizzard1','Blizzard2','Boss','Cave1','Escape'):
    mi=unreal.load_asset(BASE+'/MI_HM_RegionalLook_'+key)
    scale=lib.get_material_instance_scalar_parameter_value(mi,'HM_NativeShadowFillScale')
    radiance=lib.get_material_instance_scalar_parameter_value(mi,'HM_NativeShadowRadiance')
    expected_scale=REFINED['native_controls']['HM_NativeShadowFillScale'] if REFINED else 8
    assert abs(scale-expected_scale)<0.00001 and radiance==(16 if key=='Cave1' else 256),(key,scale,radiance)
    if REFINED:
        for name in ('WorldOutlineOpacity','WorldToonWeight','CharacterOutlineOpacity','CharacterToonWeight','ShadeSmoothness'):
            actual=lib.get_material_instance_scalar_parameter_value(mi,name)
            assert abs(actual-REFINED['native_controls'][name])<0.00001,(key,name,actual)
    profiles.append({'profile':key,'native_shadow_scale':scale,'native_shadow_radiance':radiance})
REPORT['checks']['regional_native_parameters']=profiles
if REFINED:
    sun=by['HM_PreviewSun'].get_component_by_class(unreal.DirectionalLightComponent)
    specular=sun.get_editor_property('specular_scale')
    assert abs(specular-REFINED['sun_specular_scale']['native'])<0.00001,specular
    REPORT['checks']['native_realism_grade']={'checked_volumes':len(pp),'checked_parameters':CONF['REALISM_GRADE'],'sun_specular_scale':specular}
t3d=(ROOT/'Saved/Extracted/HeinMachWeather_20261006/NativeSnowTwoLayers.t3d').read_text(encoding='utf-8')
handles=re.findall(r'^\s+EmitterHandles\((\d+)\)=',t3d,re.MULTILINE)
assert handles==['0','1'],handles
assert 'Source_Flakes_Fast_Large' in t3d and 'Source_Dust' in t3d
REPORT['checks']['compiled_system']={'export':str(ROOT/'Saved/Extracted/HeinMachWeather_20261006/NativeSnowTwoLayers.t3d'),
                                    'emitter_handles':handles,'names':['Source_Flakes_Fast_Large','Source_Dust']}
REPORT['map_sha256']=hashlib.sha256((ROOT/'Content/Maps/L_HeinMach_Environment.umap').read_bytes()).hexdigest()
REPORT['passed']=True
((REFINE_META if REFINED else META)/'FreshSavedSceneAudit.json').write_text(json.dumps(REPORT,indent=2)+'\n',encoding='utf-8')
print('KZ_HEINMACH_FRESH_AUDIT_PASSED')
