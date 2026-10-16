"""Place original fire components and missing fire fixtures in the isolated map."""
from pathlib import Path
from collections import Counter
import json
import math
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
META=ROOT/'Content/_Art/Player/Environment/HeinMach/Metadata/TutorialFires_20261006'
EX=MAIN/'Saved/Extracted/HeinMachTutorialFires_20261006'
OUT=MAIN/'Saved/ImportReports/HeinMachTutorialFires_20261006'
DEST='/Game/_Art/Player/Environment/HeinMach/Reconstructed/TutorialFires'
rows=json.loads((EX/'Components.json').read_text(encoding='utf-8'))
fixtures=json.loads((EX/'DynamicFixtures.json').read_text(encoding='utf-8'))
manifest=json.loads((EX/'AssetManifest.json').read_text(encoding='utf-8'))
lookup={r['source_package']:r['destination'] for r in manifest}
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
actors={a.get_actor_label():a for a in sub.get_all_level_actors()}
original_poses=json.loads((OUT/'BaselineScene.json').read_text())['poses']
report={'placements':[],'fixtures':[],'skipped_inactive':[],
        'native_adapter':{'intensity_multiplier':750.,'intensity_units':'Unitless','inverse_squared_falloff':False,
                          'provenance':'Existing HeinMach reconstruct_heinmach_environment.py SOURCE_INTENSITY_TO_LUMENS adapter; source xxPointLight units/defaults unconfirmed. No new light-unit conversion claimed.',
                          'light_shadows_when_not_serialized':False,'flicker_formula':'Source custom light animation is unavailable; shader uses a small native 8% variation with source AnimationSpeed.'}}


def pose(a):
    p=a.get_actor_location();r=a.get_actor_rotation();s=a.get_actor_scale3d();return [p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]


def transform(t):
    p=t['location_cm'];r=t['rotation_degrees'];s=t['scale']
    return unreal.Transform(location=unreal.Vector(p['x'],p['y'],p['z']),rotation=unreal.Rotator(pitch=r['pitch'],yaw=r['yaw'],roll=r['roll']),scale=unreal.Vector(s['x'],s['y'],s['z']))


def source_key(row):
    a=row['actor'];return a['source_level']+'_'+str(a['source_object_index'])+'_'+row['component_name'].removesuffix('_GEN_VARIABLE')


def native_asset(ref):
    pkg=ref['ObjectPath'].split('.')[0];obj=unreal.load_asset(lookup[pkg]);assert obj,pkg;return obj


def root_actor(a):
    label='HM_Prop_'+a['source_level']+'_'+str(a['source_object_index'])+'_'+a['actor_name']
    return actors.get(label)


def world_transform(row):
    t=transform(row['local_transform'])
    for p in row['parent_chain']:t=t*transform(p['local_transform'])
    a=root_actor(row['actor'])
    return t*(a.get_actor_transform() if a else transform(row['actor']['transform']))


def spawn(label,cls,t,kind,key):
    a=actors.get(label)
    if a:
        assert 'KZHeinMachTutorialFire' in [str(v) for v in a.tags],label
    else:a=sub.spawn_actor_from_class(cls,t.translation)
    assert a,label
    a.set_actor_label(label);a.set_actor_transform(t,False,False)
    a.set_folder_path('HeinMach/Reconstructed/TutorialFires/'+kind)
    a.tags=[unreal.Name('KZHeinMachTutorialFire'),unreal.Name('SourceComponent:'+key)]
    actors[label]=a;return a


def dynamic_values(i):
    f=fixtures[i];d=dict(f['cdo_properties'])
    for name,entry in f['effect_parameter_overrides'].items():
        props=entry['properties']
        if 'Value' in props and not props.get('bIsDefaultValue',False):d[name]=props['Value']
    return d


def parameter_values(row):
    values=list(row['properties'].get('InstanceParameters',[]))
    if not row.get('dynamic_fixture'):return values
    d=dynamic_values(row['fixture_index'])
    aliases={'Fire_scale':('Fire_core_size',True),'Fire_mini_spawnrate':('Fire_mini_spawnrate',False),
             'Fire_mini_scale':('Fire_mini_size',True),'Fire_mini_velocity':('Fire_mini_vel',True),'Fire_mini_range':('Fire_mini_range',False),
             'Fire_floor_spawnrate':('Fire_floor_spawnrate',False),'Fire_floor_range':('Fire_floor_range',False),
             'Ember_spawnrate':('Ember_spawnrate',False),'Ember_velocity':('Ember_vel',False),'Ember_range':('Ember_range',False),
             'Smoke_spawnrate':('Smoke_spawnrate',False),'Smoke_scale':('Smoke_size',False),'Smoke_velocity':('smoke_vel',True),'CameraOffset':('CameraOffset',False)}
    byname={p['Name']:p for p in values}
    for src,(dest,vector) in aliases.items():
        if src not in d:continue
        val=d[src]
        p={'Name':dest,'ParamType':'PSPT_Vector' if vector else 'PSPT_Scalar'}
        p['Vector' if vector else 'Scalar']=val if isinstance(val,dict) or not vector else {'X':val,'Y':val,'Z':val}
        byname[dest]=p
    return list(byname.values())


def flame(row,t):
    key=source_key(row);a=spawn('HM_FireFX_'+key,unreal.Emitter,t,'Particles',key)
    c=a.get_component_by_class(unreal.ParticleSystemComponent);assert c
    c.set_template(native_asset(row['properties']['Template']))
    params=parameter_values(row)
    for p in params:
        name=p['Name'];kind=p['ParamType']
        if kind=='PSPT_Scalar':c.set_float_parameter(name,p['Scalar'])
        elif kind=='PSPT_Vector':
            v=p['Vector'];c.set_vector_parameter(name,unreal.Vector(v['X'],v['Y'],v['Z']))
        elif kind=='PSPT_Color':
            v=p['Color'];c.set_color_parameter(name,unreal.LinearColor(v['R']/255.,v['G']/255.,v['B']/255.,v.get('A',255)/255.))
    prop=row['properties']
    distance=prop.get('LDMaxDrawDistance',prop.get('CachedMaxDrawDistance',0.))
    c.set_cull_distance(distance)
    c.set_editor_property('cast_shadow',False);c.set_editor_property('auto_activate',True);c.activate(True)
    return {'label':a.get_actor_label(),'source_key':key,'type':'ParticleSystemComponent','pose':pose(a),'asset':c.template.get_path_name(),
            'instance_parameters':params,'max_draw_distance_cm':distance,'source':row['actor']['source_package'],'source_component_index':row['component_index']}


def flicker(speed):
    path=DEST+'/Materials/MI_HM_FireFlicker_'+str(speed).replace('.','_')
    old=unreal.load_asset(path)
    if old:return old
    base_path=DEST+'/Materials/M_HM_FireFlicker'
    m=unreal.load_asset(base_path)
    if not m:
        m=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_HM_FireFlicker',DEST+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
        m.set_editor_property('material_domain',unreal.MaterialDomain.MD_LIGHT_FUNCTION)
        lib=unreal.MaterialEditingLibrary
        time=lib.create_material_expression(m,unreal.MaterialExpressionTime)
        rate=lib.create_material_expression(m,unreal.MaterialExpressionScalarParameter);rate.set_editor_property('parameter_name','SourceAnimationSpeed');rate.set_editor_property('default_value',speed)
        depth=lib.create_material_expression(m,unreal.MaterialExpressionScalarParameter);depth.set_editor_property('parameter_name','NativeFlickerAmplitude');depth.set_editor_property('default_value',.08)
        n=lib.create_material_expression(m,unreal.MaterialExpressionCustom)
        inputs=[]
        for name in ('Time','Speed','Amplitude'):
            inp=unreal.CustomInput();inp.set_editor_property('input_name',name);inputs.append(inp)
        n.set_editor_property('inputs',inputs);n.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT1)
        n.set_editor_property('code','return 1-Amplitude+Amplitude*(0.65*sin(Time*Speed)+0.35*sin(Time*Speed*1.73));')
        for obj,pin in ((time,'Time'),(rate,'Speed'),(depth,'Amplitude')):assert lib.connect_material_expressions(obj,'',n,pin)
        assert lib.connect_material_property(n,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        assert not list(lib.recompile_material(m));assert unreal.EditorAssetLibrary.save_loaded_asset(m,False)
    mat=unreal.AssetToolsHelpers.get_asset_tools().create_asset(path.rsplit('/',1)[1],DEST+'/Materials',unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
    unreal.MaterialEditingLibrary.set_material_instance_parent(mat,m)
    unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mat,'SourceAnimationSpeed',speed)
    unreal.MaterialEditingLibrary.update_material_instance(mat);assert unreal.EditorAssetLibrary.save_loaded_asset(mat,False)
    return mat


def light(row,t):
    p=dict(row['properties']);key=source_key(row)
    if row.get('dynamic_fixture'):
        d=dynamic_values(row['fixture_index']);second='Second' in row['component_name']
        for src,dest in [('SecondLightIntensity' if second else 'LightIntensity','Intensity'),('SecondLightRadius' if second else 'LightRadius','AttenuationRadius')]:
            if src in d:p[dest]=d[src]
    if p.get('bAffectsWorld') is False or p.get('Intensity',0.)<=0:
        report['skipped_inactive'].append({'source_key':key,'reason':'Source bAffectsWorld=false or intensity zero','properties':p});return None
    a=spawn('HM_FireLight_'+key,unreal.PointLight,t,'Lights',key);c=a.get_component_by_class(unreal.PointLightComponent)
    c.set_editor_property('mobility',unreal.ComponentMobility.MOVABLE)
    c.set_editor_property('intensity_units',unreal.LightUnits.UNITLESS)
    c.set_editor_property('use_inverse_squared_falloff',False)
    c.set_editor_property('intensity',p['Intensity']*750.)
    c.set_editor_property('attenuation_radius',p['AttenuationRadius'])
    color=p.get('LightColor')
    if color:c.set_editor_property('light_color',unreal.Color(r=color['R'],g=color['G'],b=color['B'],a=color.get('A',255)))
    c.set_editor_property('cast_shadows',p.get('CastShadows',False))
    for src,dest in [('LightFalloffExponent','light_falloff_exponent'),('SpecularScale','specular_scale'),('MaxDrawDistance','max_draw_distance'),('MaxDistanceFadeRange','max_distance_fade_range'),('VolumetricScatteringIntensity','volumetric_scattering_intensity'),('IndirectLightingIntensity','indirect_lighting_intensity'),('SourceRadius','source_radius'),('SourceLength','source_length'),('IESBrightnessScale','ies_brightness_scale')]:
        if src in p:c.set_editor_property(dest,p[src])
    if p.get('IESTexture'):c.set_editor_property('ies_texture',native_asset(p['IESTexture']))
    if p.get('bUseIESBrightness') is not None:c.set_editor_property('use_ies_brightness',p['bUseIESBrightness'])
    if p.get('bUseLightAnimation') and p.get('AnimationSpeed'):c.set_editor_property('light_function_material',flicker(p['AnimationSpeed']))
    return {'label':a.get_actor_label(),'source_key':key,'type':'PointLightComponent','pose':pose(a),'source_intensity':p['Intensity'],
            'native_intensity':c.get_editor_property('intensity'),'radius_cm':p['AttenuationRadius'],'source_properties':p,
            'ies':c.get_editor_property('ies_texture').get_path_name() if c.get_editor_property('ies_texture') else None}


def decal(row,t):
    p=row['properties'];key=source_key(row)
    if not p.get('DecalMaterial'):return None
    a=spawn('HM_FireDecal_'+key,unreal.DecalActor,t,'GroundBurn',key)
    c=a.get_component_by_class(unreal.DecalComponent);assert c
    c.set_decal_material(native_asset(p['DecalMaterial']))
    size=p['DecalSize'];c.set_editor_property('decal_size',unreal.Vector(size['X'],size['Y'],size['Z']))
    for src,dest in [('FadeScreenSize','fade_screen_size'),('SortOrder','sort_order')]:
        if src in p:c.set_editor_property(dest,p[src])
    return {'label':a.get_actor_label(),'source_key':key,'type':'DecalComponent','pose':pose(a),
            'asset':c.get_editor_property('decal_material').get_path_name(),'size_cm':size,'source':row['actor']['source_package'],'source_component_index':row['component_index']}


for f in fixtures:
    a=f['actor'];key=a['source_level']+'_'+str(a['source_object_index'])+'_'+a['actor_name']
    target=spawn('HM_FireFixture_'+key,unreal.StaticMeshActor,transform(a['transform']),'Fixtures',key)
    c=target.get_component_by_class(unreal.StaticMeshComponent);c.set_static_mesh(native_asset(f['static_mesh']))
    # Art appearance only. Existing scene collision remains authoritative.
    c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    report['fixtures'].append({'label':target.get_actor_label(),'source_key':key,'pose':pose(target),'mesh':c.static_mesh.get_path_name(),
                               'boundary':'Original unbroken StaticMeshArray presentation; original Chaos destruction/gameplay not implemented.'})

for row in rows:
    t=world_transform(row)
    if 'ParticleSystemComponent' in row['component_type']:result=flame(row,t)
    elif 'PointLightComponent' in row['component_type']:result=light(row,t)
    elif row['component_type']=='DecalComponent':result=decal(row,t)
    else:continue
    if result:report['placements'].append(result)

after={a.get_actor_label():pose(a) for a in sub.get_all_level_actors()}
changed=[n for n,v in original_poses.items() if n not in after or max(abs(x-y) for x,y in zip(v,after[n]))>1e-6]
assert not changed,changed
report['preserved_actor_count']=len(original_poses);report['existing_pose_changes']=changed
report['counts']=dict(Counter(r['type'] for r in report['placements']));report['new_fixture_count']=len(report['fixtures']);report['total_actors']=len(after)
assert unreal.EditorLoadingAndSavingUtils.save_map(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(),'/Game/Maps/L_HeinMach_Environment')
(META/'Placement.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
(OUT/'Placement.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print('KZ_HM_FIRES_PLACE_PASSED',report['counts'],'newFixtures',len(report['fixtures']),'preserved',len(original_poses))
