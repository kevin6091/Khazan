"""Source-backed camera-centered GPU snow; no new runtime C++ owner."""
from pathlib import Path
import json
import math
import runpy
import sys
import time
import traceback
import unreal

sys.dont_write_bytecode = True
ROOT = Path(unreal.Paths.project_dir()).resolve()
META = ROOT / 'Content/_Art/Player/Environment/Rendering/Metadata/HeinMachWeather_20261006'
EXTRACT = ROOT / 'Saved/Extracted/HeinMachWeather_20261006'
ASSETS = '/Game/_Art/Player/Environment/Rendering/HeinMachWeather'
LIB = unreal.MaterialEditingLibrary
OLD = runpy.run_path(str(ROOT / 'Scripts/Art/restore_level_look.py'))
FX = unreal.FXConverterUtilitiesLibrary
T = unreal.NiagaraScriptInputType
CAT = unreal.ScriptExecutionCategory
def F(value):
    return FX.create_script_input_float(value)
V = lambda v: FX.create_script_input_vector(unreal.Vector(*v))
SOURCE_PACKAGE = 'BBQ/Content/_Kazan_/Art/VFX/VFX_Particle/Level/BBQ_Level/Enviroment/FP_World_IceBlizzard'
NATIVE = {'RadianceScale': 2**json.loads((META/'LookApplied.json').read_text())['native_controls']['OutdoorEV100'], 'SourceOPSpawn': 500.0,
          'SpaceAdaptation': 'World-space particles spawned around the camera, instead of attaching existing flakes to camera movement.'}
CONTEXTS = []


def write(name, data):
    (META / (name+'.json')).write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')


def save(asset):
    assert unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False)


def asset(name, cls, factory):
    obj = unreal.load_asset(ASSETS+'/'+name)
    if not obj:
        unreal.EditorAssetLibrary.make_directory(ASSETS)
        obj = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, ASSETS, cls, factory)
    assert obj, name
    return obj


def imported(name, path, factory):
    obj = unreal.load_asset(ASSETS+'/'+name)
    if not obj:
        task = unreal.AssetImportTask()
        for k, v in [('filename', str(path)), ('destination_path', ASSETS), ('destination_name', name),
                     ('automated', True), ('replace_existing', False), ('save', True), ('factory', factory)]:
            task.set_editor_property(k, v)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        obj = unreal.load_asset(ASSETS+'/'+name)
    assert obj, name
    return obj


def material(texture, dust=False):
    m = asset('M_HM_SourceDust' if dust else 'M_HM_SourceSnow', unreal.Material, unreal.MaterialFactoryNew())
    m.modify()
    LIB.delete_all_material_expressions(m)
    for k, v in [('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT), ('two_sided', True),
                 ('shading_model', unreal.MaterialShadingModel.MSM_UNLIT), ('enable_responsive_aa', True),
                 ('output_translucent_velocity', True), ('use_translucency_vertex_fog', False),
                 # Source bEnableSeparateTranslucency=false: participate in
                 # the main translucency before DOF/motion blur.
                 ('translucency_pass',unreal.MaterialTranslucencyPass.MTP_BEFORE_DOF)]:
        m.set_editor_property(k, v)
    LIB.set_material_usage(m, unreal.MaterialUsage.MATUSAGE_NIAGARA_SPRITES)
    tex = OLD['expression'](m, unreal.MaterialExpressionTextureSample, -600, 0)
    tex.set_editor_property('texture', texture)
    tex.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
    pc = OLD['expression'](m, unreal.MaterialExpressionParticleColor, -600, 200)
    world = OLD['expression'](m, unreal.MaterialExpressionWorldPosition, -600, 400)
    camera = OLD['expression'](m, unreal.MaterialExpressionCameraPositionWS, -600, 600)
    age = OLD['expression'](m, unreal.MaterialExpressionParticleRelativeTime, -600, 700)
    node = OLD['expression'](m, unreal.MaterialExpressionCustom, 0, 0)
    node.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    node.set_editor_property('inputs', [OLD['custom_input'](k) for k in ('Mask', 'Particle', 'World', 'Camera', 'Age', 'CameraFade', 'Radiance')])
    objects = json.loads(next((EXTRACT/'Source').rglob('FP_World_IceBlizzard.json')).read_text(encoding='utf-8-sig'))
    data = next(o['Properties']['ResourceData'] for o in objects if o['Name'] == ('ParticleModuleTypeDataGpu_1' if dust else 'ParticleModuleTypeDataGpu_0'))
    alphas = [s['A']/255*data['ColorScale']['W']+data['ColorBias']['W'] for s in data['QuantizedColorSamples']]
    count=len(alphas)
    code = 'float sourceAlpha['+str(count)+']={'+','.join(str(v) for v in alphas)+'};\n'
    code += '''
// Engine per-view PostProcessVolume flag bit 0 is reserved for covered cave views.
if (PostVolumeUserFlagTest(0.0)>0.5) return float4(0,0,0,0);
float alphaIndex=saturate(Age)*15.0;
int first=min((int)alphaIndex,14);
float sourceLifetimeAlpha=lerp(sourceAlpha[first],sourceAlpha[first+1],alphaIndex-first);
float distanceToCamera=length(World.xyz-Camera.xyz);
float nearFade=saturate(distanceToCamera/max(CameraFade,0.001));
return float4(Particle.rgb*Radiance,Mask.r*Particle.a*nearFade*sourceLifetimeAlpha);
'''
    code=code.replace('Age)*15.0','Age)*'+str(count-1)+'.0').replace('(int)alphaIndex,14','(int)alphaIndex,'+str(count-2))
    node.set_editor_property('code', code)
    for src, out, pin in [(tex, 'R', 'Mask'), (pc, 'RGBA', 'Particle'), (world, '', 'World'), (camera, '', 'Camera'), (age, '', 'Age'),
                          (OLD['scalar'](m, 'CameraFade_SourceCm', 50.0, -600, 800), '', 'CameraFade'),
                          (OLD['scalar'](m, 'Radiance_Native', NATIVE['RadianceScale'], -600, 1000), '', 'Radiance')]:
        OLD['connect'](src, out, node, pin)
    rgb = OLD['expression'](m, unreal.MaterialExpressionComponentMask, 300, 0)
    for k in ('r', 'g', 'b'):
        rgb.set_editor_property(k, True)
    alpha = OLD['expression'](m, unreal.MaterialExpressionComponentMask, 300, 200)
    # ComponentMask defaults to R+G. Setting A alone would feed emissive R
    # into Opacity and turn every sub-UV flake into an opaque rectangle.
    for k in ('r', 'g', 'b', 'a'):
        alpha.set_editor_property(k, k == 'a')
    OLD['connect'](node, '', rgb, '')
    OLD['connect'](node, '', alpha, '')
    assert LIB.connect_material_property(rgb, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    # UE5 rejects SceneDepth/DepthFade when translucent Output Velocity writes
    # depth. Keep source motion-vector output and camera fade. Source material
    # exposes DepthFade=10, but its cooked node body/active use was stripped.
    assert LIB.connect_material_property(alpha, '', unreal.MaterialProperty.MP_OPACITY)
    # Restore Cascade's exact SizeBySpeed vertex equation. The sprite's Y
    # axis is velocity-aligned; moving vertices avoids a second GPU update
    # module and leaves the original short flake size intact at low speed.
    stretch=OLD['expression'](m,unreal.MaterialExpressionCustom,0,700)
    stretch.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    stretch.set_editor_property('inputs',[OLD['custom_input'](k) for k in ('World','Center','Direction','Speed')])
    stretch.set_editor_property('code','float scale=min(max(Speed,1.0),'+('4.0' if dust else '2.0')+'); return Direction.xyz*dot(World.xyz-Center.xyz,Direction.xyz)*(scale-1.0);')
    for cls,pin in [(unreal.MaterialExpressionParticlePositionWS,'Center'),(unreal.MaterialExpressionParticleDirection,'Direction'),(unreal.MaterialExpressionParticleSpeed,'Speed')]:
        OLD['connect'](OLD['expression'](m,cls,-600,1200),'',stretch,pin)
    OLD['connect'](world,'',stretch,'World')
    assert LIB.connect_material_property(stretch,'',unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    errors=LIB.recompile_material(m)
    assert not errors,str(errors)
    stats = LIB.get_statistics(m)
    assert stats.num_pixel_shader_instructions > 0, 'Snow material did not compile: '+m.get_name()
    save(m)
    return m


def context(path):
    return FX.create_script_context(unreal.CreateScriptContextArgs(FX.create_asset_data(path)))


def setp(ctx, name, value):
    assert ctx.set_parameter(name, value), 'Niagara input mismatch: '+name


def dynamic(path, inputs, kind):
    ctx = context(path)
    for k, v in inputs.items():
        setp(ctx, k, v)
    return FX.create_script_input_dynamic(ctx, kind)


def random(lo, hi, kind=T.FLOAT):
    n = 'Float' if kind == T.FLOAT else 'Vector'
    return dynamic('/Niagara/DynamicInputs/UniformRange/V2/RandomRange'+n,
                   {'Minimum': F(lo) if kind == T.FLOAT else V(lo), 'Maximum': F(hi) if kind == T.FLOAT else V(hi)}, kind)


def main():
    # Explicit legacy factories avoid the editor Interchange async import path.
    texture = imported('T_HM_SnowTickle_03', next((EXTRACT/'Textures').rglob('FT_SnowTickle_03.png')), unreal.TextureFactory())
    if texture.get_editor_property('srgb') or texture.get_editor_property('compression_settings') != unreal.TextureCompressionSettings.TC_GRAYSCALE:
        texture.set_editor_property('srgb', False)
        texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_GRAYSCALE)
        save(texture)
    field = imported('VF_HM_Perlin_Source16', EXTRACT/'FP_Perlin_HighFreq_16x16x16.fga', unreal.VectorFieldStaticFactory())
    snowmat = material(texture)
    dustmat = material(texture, True)
    name = 'NS_HM_SourceSnow_TwoLayers'
    partial = unreal.load_asset(ASSETS+'/'+name)
    if partial and unreal.EditorAssetLibrary.get_metadata_tag(partial, 'HM_WeatherBuilt'):
        write('SnowMaterialUpdate', {'native_controls': NATIVE, 'source_alpha_samples': {'flakes': 16, 'dust': 8},
                                   'opacity_contract': 'Only custom float4 A drives Opacity; RGB drives Emissive. ComponentMask R/G defaults explicitly disabled.',
                                   'material_stats': {m.get_name(): LIB.get_statistics(m).num_pixel_shader_instructions for m in (snowmat, dustmat)},
                                   'Cave_visibility': 'Engine PostProcessVolume UserFlags bit 0, material PostVolumeUserFlagTest. No runtime controller.'})
        print('KZ_HEINMACH_SNOW_MATERIAL_UPDATED')
        return
    if partial and not unreal.EditorAssetLibrary.get_metadata_tag(partial, 'HM_WeatherBuilt'):
        # Only replace this session's incomplete generated system. It has not
        # yet been bound to the saved level; other systems are never deleted.
        for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
            if a.get_actor_label() == 'HM_Environment_SourceSnow':
                assert a.get_component_by_class(unreal.NiagaraComponent).get_asset() != partial
        assert unreal.EditorAssetLibrary.delete_asset(ASSETS+'/'+name)
    # Rebuild only this task's dedicated system, preserving all user VFX assets.
    system = asset(name, unreal.NiagaraSystem, unreal.NiagaraSystemFactoryNew())
    ctx = FX.create_system_conversion_context(system)
    CONTEXTS.append(ctx)
    assert not unreal.EditorAssetLibrary.get_metadata_tag(system, 'HM_WeatherBuilt'), 'System already built; use targeted editing rather than append duplicate emitters'
    e = ctx.add_empty_emitter('Source_Flakes_Fast_Large')
    e.set_sim_target(unreal.NiagaraSimTarget.GPU_COMPUTE_SIM)
    e.set_local_space(False)
    def module(label, path, cat):
        return e.find_or_add_module_script(label, unreal.CreateScriptContextArgs(FX.create_asset_data(path)), cat)
    state = module('EmitterState', '/Niagara/Modules/Emitter/EmitterState', CAT.EMITTER_UPDATE)
    setp(state, 'Life Cycle Mode', FX.create_script_input_enum('/Niagara/Enums/ENiagaraEmitterLifeCycleMode', 'Self'))
    setp(state, 'Loop Behavior', FX.create_script_input_enum('/Niagara/Enums/ENiagara_EmitterStateOptions', 'Infinite'))
    spawn = module('SourceSpawn', '/Niagara/Modules/Emitter/SpawnRate', CAT.EMITTER_UPDATE)
    # Original OP Spawn=500 multiplied by original GPU RateScale [2.5,5].
    setp(spawn, 'SpawnRate', random(500*2.5, 500*5))
    init = module('InitializeParticle', '/Niagara/Modules/Spawn/Initialization/InitializeParticle', CAT.PARTICLE_SPAWN)
    setp(init, 'Lifetime', random(5, 6))
    assert init.set_parameter('Sprite Size', dynamic('/Niagara/DynamicInputs/TypeConversions/Vector2DFromFloat', {'Value': random(0.5, 0.75)}, T.VEC2), True, True)
    setp(init, 'Color', FX.create_script_input_linear_color(unreal.LinearColor(0.30980393, 0.427451, 0.48627454, 1)))
    camera = dynamic('/Niagara/DynamicInputs/Vectors/Position/ReturnCameraPosition',
                     {'Camera Query': FX.create_script_input_di(unreal.new_object(unreal.load_class(None, '/Script/Niagara.NiagaraDataInterfaceCamera')))}, T.POSITION)
    # Query the owning player's camera once in the CPU emitter update and
    # upload that position for GPU spawn. A GPU-only Camera DI reads the
    # renderer's PrimaryView, which can remain stale in offscreen captures.
    e.set_parameter_directly('Emitter.SourceCameraPosition', camera, CAT.EMITTER_UPDATE)
    localbox = random((-1500, -250, 0), (0, 250, 500), T.VEC3)
    rotation = FX.create_script_input_linked_parameter('Engine.Owner.Rotation', T.QUATERNION)
    worldbox = dynamic('/Niagara/DynamicInputs/Vectors/RotateVectorByQuaternion',
                       {'Vector To Rotate': localbox, 'Quaternion': rotation}, T.VEC3)
    pos = dynamic('/Niagara/DynamicInputs/Vectors/Position/AddVectorToPosition', {'Position': FX.create_script_input_linked_parameter('Emitter.SourceCameraPosition',T.POSITION), 'Vector': worldbox}, T.POSITION)
    # InitializeParticle gates these inputs behind WritePosition/WriteSpriteSize.
    # Setting values alone leaves both switches off. Enable their edit condition.
    assert init.set_parameter('Position', pos, True, True)
    velocity = dynamic('/Niagara/DynamicInputs/Vectors/RotateVectorByQuaternion',
                       {'Vector To Rotate': random((750, -50, -500), (1250, 50, -250), T.VEC3), 'Quaternion': rotation}, T.VEC3)
    e.set_parameter_directly('Particles.Velocity', velocity, CAT.PARTICLE_SPAWN)
    e.set_parameter_directly('Particles.SubImageIndex', random(0, 16), CAT.PARTICLE_SPAWN)
    module('ParticleState', '/Niagara/Modules/Update/Lifetime/ParticleState', CAT.PARTICLE_UPDATE)
    vf = unreal.new_object(unreal.load_class(None, '/Script/Niagara.NiagaraDataInterfaceVectorField'))
    vf.set_editor_property('field', field)
    for axis in 'xyz':
        vf.set_editor_property('bTile'+axis.upper(), True)
    # SampleVectorField is a module writing an Output variable, not a
    # dynamic input. Treating its parameter-map output as Vec3 selects the
    # wrong graph output and can broadcast DeltaTime into all force axes.
    sample = module('SourceSampleVectorField','/Niagara/VectorFields/SampleVectorField',CAT.PARTICLE_UPDATE)
    setp(sample,'VectorField',FX.create_script_input_di(vf))
    setp(sample,'FieldScale',V((50,50,50)))
    apply = module('SourceVectorField', '/Niagara/VectorFields/ApplyVectorField', CAT.PARTICLE_UPDATE)
    setp(apply, 'Vector Field Vector', FX.create_script_input_linked_parameter('Output.SampleVectorField.SampledVector',T.VEC3))
    setp(apply, 'Vector Field Intensity as Force', F(10000))
    # Niagara's native module adds the field velocity before blending. Scale
    # that input by source tightness to reproduce Cascade's target blend.
    setp(apply, 'Vector Field Intensity as Velocity', F(10000*0.025))
    setp(apply, 'Vector Field Velocity Tightness', F(0.025))
    module('SolveForcesAndVelocity', '/Niagara/Modules/Solvers/SolveForcesAndVelocity', CAT.PARTICLE_UPDATE)
    renderer = unreal.NiagaraSpriteRendererProperties()
    for k, v in [('material', snowmat), ('sub_image_size', unreal.Vector2D(4, 4)),
                 ('alignment', unreal.NiagaraSpriteAlignment.VELOCITY_ALIGNED),
                 ('sort_mode', unreal.NiagaraSortMode.NONE), ('cast_shadows', False)]:
        renderer.set_editor_property(k, v)
    e.add_renderer('SourceSnowSprites', renderer)
    # Original second GPU emitter: short-lived, camera-near drifting dust.
    dustfield=imported('VF_HM_Perlin_Source8',EXTRACT/'FP_Perlin_HighFreq_8x8x8.fga',unreal.VectorFieldStaticFactory())
    de=ctx.add_empty_emitter('Source_Dust')
    de.set_sim_target(unreal.NiagaraSimTarget.GPU_COMPUTE_SIM)
    de.set_local_space(False)
    def dm(label,path,cat):return de.find_or_add_module_script(label,unreal.CreateScriptContextArgs(FX.create_asset_data(path)),cat)
    ds=dm('EmitterState','/Niagara/Modules/Emitter/EmitterState',CAT.EMITTER_UPDATE)
    setp(ds,'Life Cycle Mode',FX.create_script_input_enum('/Niagara/Enums/ENiagaraEmitterLifeCycleMode','Self'))
    setp(ds,'Loop Behavior',FX.create_script_input_enum('/Niagara/Enums/ENiagara_EmitterStateOptions','Infinite'))
    setp(dm('SourceDustSpawn','/Niagara/Modules/Emitter/SpawnRate',CAT.EMITTER_UPDATE),'SpawnRate',random(500*2.5,500*5))
    de.set_parameter_directly('Emitter.SourceCameraPosition',camera,CAT.EMITTER_UPDATE)
    di=dm('InitializeParticle','/Niagara/Modules/Spawn/Initialization/InitializeParticle',CAT.PARTICLE_SPAWN)
    setp(di,'Lifetime',random(1,2))
    # GPU ResourceData.MiscBias XY=.3 and no MiscScale XY, so the compiled
    # original GPU size is .3 square; the stale editable StartSize table differs.
    assert di.set_parameter('Sprite Size',FX.create_script_input_vec2(unreal.Vector2D(.3,.3)),True,True)
    setp(di,'Color',FX.create_script_input_linear_color(unreal.LinearColor(1,1.5,2,1)))
    sphere=dm('SourceSphere','/Niagara/Modules/Spawn/Location/V2/ShapeLocation',CAT.PARTICLE_SPAWN)
    setp(sphere,'Shape Primitive',FX.create_script_input_enum('/Niagara/Enums/Location/ENiagara_LocationShapes','Sphere'))
    setp(sphere,'Sphere Radius',F(50))
    setp(sphere,'Offset Mode',FX.create_script_input_enum('/Niagara/Enums/Transforms/ENiagara_OffsetMode','Default'))
    assert sphere.set_parameter('Offset',FX.create_script_input_linked_parameter('Emitter.SourceCameraPosition',T.VEC3),True,True)
    de.set_parameter_directly('Particles.Velocity',dynamic('/Niagara/DynamicInputs/Vectors/RotateVectorByQuaternion',{'Vector To Rotate':random((0,-2,1),(5,2,5),T.VEC3),'Quaternion':rotation},T.VEC3),CAT.PARTICLE_SPAWN)
    de.set_parameter_directly('Particles.SubImageIndex',random(0,16),CAT.PARTICLE_SPAWN)
    dm('ParticleState','/Niagara/Modules/Update/Lifetime/ParticleState',CAT.PARTICLE_UPDATE)
    setp(dm('SourceDustDrag','/Niagara/Modules/Update/Forces/Drag',CAT.PARTICLE_UPDATE),'Drag',random(0,1))
    setp(dm('SourceDustAcceleration','/Niagara/Modules/Update/Forces/AccelerationForce',CAT.PARTICLE_UPDATE),'Acceleration',V((1,0,1)))
    dvf=unreal.new_object(unreal.load_class(None,'/Script/Niagara.NiagaraDataInterfaceVectorField'))
    dvf.set_editor_property('field',dustfield)
    for axis in 'XYZ':dvf.set_editor_property('bTile'+axis,True)
    dsm=dm('SourceSampleVectorField','/Niagara/VectorFields/SampleVectorField',CAT.PARTICLE_UPDATE)
    setp(dsm,'VectorField',FX.create_script_input_di(dvf));setp(dsm,'FieldScale',V((250,250,250)))
    da=dm('SourceVectorField','/Niagara/VectorFields/ApplyVectorField',CAT.PARTICLE_UPDATE)
    setp(da,'Vector Field Vector',FX.create_script_input_linked_parameter('Output.SampleVectorField.SampledVector',T.VEC3))
    setp(da,'Vector Field Intensity as Force',F(5000))
    setp(da,'Vector Field Intensity as Velocity',F(5000*.05))
    setp(da,'Vector Field Velocity Tightness',F(.05))
    dm('SolveForcesAndVelocity','/Niagara/Modules/Solvers/SolveForcesAndVelocity',CAT.PARTICLE_UPDATE)
    dr=unreal.NiagaraSpriteRendererProperties()
    for k,v in [('material',dustmat),('sub_image_size',unreal.Vector2D(4,4)),('alignment',unreal.NiagaraSpriteAlignment.VELOCITY_ALIGNED),('sort_mode',unreal.NiagaraSortMode.NONE),('cast_shadows',False)]:dr.set_editor_property(k,v)
    de.add_renderer('SourceDustSprites',dr)
    ctx.finalize()
    save(system)
    ctx.cleanup()
    CONTEXTS.remove(ctx)
    world = unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
    ac = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    by = {a.get_actor_label(): a for a in ac.get_all_level_actors()}
    snow = by.get('HM_Environment_SourceSnow') or ac.spawn_actor_from_class(unreal.NiagaraActor, unreal.Vector())
    snow.set_actor_label('HM_Environment_SourceSnow')
    snow.set_folder_path('HeinMach/Reconstructed/Environment/Weather')
    snow.set_actor_rotation(unreal.Rotator(pitch=0, yaw=120, roll=0), False)
    comp = snow.get_component_by_class(unreal.NiagaraComponent)
    comp.set_asset(system)
    comp.set_editor_property('cast_shadow', False)
    # World-space camera queries require conservative bounds over the level.
    scene = [a.get_actor_bounds(False) for a in by.values() if a.get_actor_label().startswith(('HM_Prop_', 'HM_Landscape_', 'HM_Terrain_'))]
    lo = [min(getattr(p, c)-getattr(b, c) for p, b in scene)-5000 for c in 'xyz']
    hi = [max(getattr(p, c)+getattr(b, c) for p, b in scene)+5000 for c in 'xyz']
    bounds = unreal.Box(min=unreal.Vector(*lo), max=unreal.Vector(*hi))
    system.set_editor_property('FixedBounds', bounds)
    system.set_editor_property('bFixedBounds', True)
    save(system)
    comp.set_system_fixed_bounds(bounds)
    comp.set_emitter_fixed_bounds('Source_Flakes_Fast_Large', bounds)
    comp.set_emitter_fixed_bounds('Source_Dust',bounds)
    comp.set_auto_activate(True)
    comp.activate(True)
    assert unreal.EditorLoadingAndSavingUtils.save_map(world, '/Game/Maps/L_HeinMach_Environment')
    unreal.EditorAssetLibrary.set_metadata_tag(system, 'HM_WeatherBuilt', '20261006')
    save(system)
    write('SnowApplied', {'asset': system.get_path_name(), 'original_particle': SOURCE_PACKAGE, 'GPU_emitters': 2,
                         'source_spawn_rate_per_second': [1250, 2500], 'source_lifetime_seconds': [5, 6],
                         'source_size_cm': [0.5, 0.75], 'source_OP_yaw_degrees': 120, 'world_bounds_cm': [lo, hi],
                         'source_dust':{'life_seconds':[1,2],'compiled_GPU_size_cm':[.3,.3],'spawn_sphere_radius_cm':50,'original_vector_samples':512},
                         'native_controls': NATIVE, 'boundary': 'Native Niagara adaptation of both source GPU snow/dust emitters. Ground collision/event puffs, rotating dust vector field, MaxBlizzard replacement and full regional wind/rate controller remain separate source contracts.'})
    print('KZ_HEINMACH_SNOW_APPLIED')


started = time.monotonic()
handle = None
def tick(delta):
    if time.monotonic()-started < 10:
        return
    unreal.unregister_slate_post_tick_callback(handle)
    try:
        main()
    except Exception:
        write('SnowFailure', {'error': traceback.format_exc()})
        unreal.log_error(traceback.format_exc())
    finally:
        for ctx in CONTEXTS:
            ctx.cleanup()
    unreal.SystemLibrary.quit_editor()
if '-nullrhi' in unreal.SystemLibrary.get_command_line().lower():
    main()
else:
    handle = unreal.register_slate_post_tick_callback(tick)
