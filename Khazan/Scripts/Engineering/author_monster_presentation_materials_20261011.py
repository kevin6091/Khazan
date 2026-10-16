"""Private public-API author: chest sockets, corpse shaders, source UI gradient, blood decal suppression."""
from pathlib import Path
import json, os, traceback, unreal
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');WORK=Path(unreal.Paths.project_dir()).resolve()
assert WORK==Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan')
OUT=Path(os.environ['KZ_MONSTER_REPAIR_OUT']);lib=unreal.MaterialEditingLibrary
d={'status':'running','saved':[],'sockets':[],'corpse_masters':[],'suppressed_blood_decals':[]}
def save(a):
    assert unreal.EditorAssetLibrary.save_loaded_asset(a,only_if_is_dirty=False),a.get_path_name()
    if a.get_path_name() not in d['saved']:d['saved'].append(a.get_path_name())
def node(m,c,**props):
    n=lib.create_material_expression(m,c)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def connect(a,b,pin,out=''):assert lib.connect_material_expressions(a,out,b,pin)
def custom(m,code,inputs):
    fields=[]
    for i in inputs:
        field=unreal.CustomInput();field.set_editor_property('input_name',i);fields.append(field)
    n=node(m,unreal.MaterialExpressionCustom,code=code,output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT1,inputs=fields);return n
try:
    registry=unreal.AssetRegistryHelpers.get_asset_registry();roots={};skeletons={}
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for family in ['Swordsman','SwordShield','HeavySwordsman','HalberdElite','ApesStoneHandElite','Yetuga']:
        path='/Game/Bluprints/Monsters/BP_Monster_'+family
        cls=unreal.load_class(None,path+'.BP_Monster_'+family+'_C');assert cls,path
        actor=actors.spawn_actor_from_class(cls,unreal.Vector())
        try:
            mesh=actor.get_editor_property('Mesh');sk=mesh.get_editor_property('skeletal_mesh');skeleton=sk.get_editor_property('skeleton')
            assert mesh.does_socket_exist('Bip001-Spine2')
            skeletons[skeleton.get_path_name()]=skeleton
            for component in actor.get_components_by_class(unreal.MeshComponent):
                for slot in range(component.get_num_materials()):
                    mat=component.get_material(slot)
                    while isinstance(mat,unreal.MaterialInstance):mat=mat.get_editor_property('parent')
                    if isinstance(mat,unreal.Material) and 'InvisiblePoseCarrier' not in mat.get_name():roots[mat.get_path_name()]=mat
        finally:actors.destroy_actor(actor)
    # Skeleton Sockets are Python-protected; the task-private native author uses the public C++ Sockets API.
    noise=unreal.load_asset('/Game/_Art/Effects/Shared/Textures/BBQ_Texture/Noise/FT_Noise_Dissolve');assert noise
    for path,m in roots.items():
        if any(isinstance(n,unreal.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='KZDeathProgress' for n in lib.get_material_expressions(m)):
            d['corpse_masters'].append({'material':path,'already_authored':True});continue
        assert not m.get_editor_property('use_material_attributes'),path+' requires an attributes-preserving adapter'
        base=lib.get_material_property_input_node(m,unreal.MaterialProperty.MP_BASE_COLOR)
        base_output=lib.get_material_property_input_node_output_name(m,unreal.MaterialProperty.MP_BASE_COLOR)
        oldblend=m.get_editor_property('blend_mode');trans=oldblend in [unreal.BlendMode.BLEND_TRANSLUCENT,unreal.BlendMode.BLEND_ADDITIVE]
        prop=unreal.MaterialProperty.MP_OPACITY if trans else unreal.MaterialProperty.MP_OPACITY_MASK
        opacity=lib.get_material_property_input_node(m,prop)
        opacity_output=lib.get_material_property_input_node_output_name(m,prop)
        progress=node(m,unreal.MaterialExpressionScalarParameter,parameter_name='KZDeathProgress',default_value=0.)
        edge=node(m,unreal.MaterialExpressionScalarParameter,parameter_name='KZDeathEdgeWidth',default_value=.08)
        tex=node(m,unreal.MaterialExpressionTextureSampleParameter2D,parameter_name='KZDeathNoise',texture=noise,sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        mask=custom(m,'return P<=0 ? Original : (P>=1 ? 0 : Original*smoothstep(P-Edge,P,N));',['Original','P','Edge','N'])
        if not opacity:opacity=node(m,unreal.MaterialExpressionConstant,r=1.)
        connect(opacity,mask,'Original',opacity_output);connect(progress,mask,'P');connect(edge,mask,'Edge');connect(tex,mask,'N','R')
        assert lib.connect_material_property(mask,'',prop)
        if not trans:m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED)
        if base:
            char=custom(m,'return lerp(Base,float3(.002,.002,.002),saturate(P*3));',['Base','P']);char.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
            connect(base,char,'Base',base_output);connect(progress,char,'P');assert lib.connect_material_property(char,'',unreal.MaterialProperty.MP_BASE_COLOR)
        lib.recompile_material(m);save(m);d['corpse_masters'].append({'material':path,'original_blend':str(oldblend),'base_output':base_output,'opacity_output':opacity_output,'noise':noise.get_path_name(),'baseline_progress':0,'temporary_edge_width':.08})
    path='/Game/UI/Combat/Materials/M_UI_GaugeBackground'
    m=unreal.load_asset(path)
    if not m:
        m=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_UI_GaugeBackground','/Game/UI/Combat/Materials',unreal.Material,unreal.MaterialFactoryNew())
        m.set_editor_property('material_domain',unreal.MaterialDomain.MD_UI);m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
        uv=node(m,unreal.MaterialExpressionTextureCoordinate)
        alpha=custom(m,'float y=1-UV.y;return y<Mid ? lerp(A1,A2,y/Mid) : lerp(A2,A3,(y-Mid)/(1-Mid));',['UV','Mid','A1','A2','A3'])
        connect(uv,alpha,'UV')
        for name,value in [('Mid',.8),('A1',.35),('A2',.2),('A3',.1)]:
            connect(node(m,unreal.MaterialExpressionScalarParameter,parameter_name=name,default_value=value),alpha,name)
        color=node(m,unreal.MaterialExpressionVectorParameter,parameter_name='TrackColor',default_value=unreal.LinearColor(.015,.015,.015,1))
        assert lib.connect_material_property(color,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR);assert lib.connect_material_property(alpha,'',unreal.MaterialProperty.MP_OPACITY)
        lib.recompile_material(m);save(m)
    d['ui_background']=m.get_path_name() # Preserve a valid existing graph; UE deletion asserts on Python-rooted expressions.
    plan=json.loads((MAIN/'Saved/ImportReports/MonsterVFX_20261008/PreparedPlaybackPlan.json').read_text(encoding='utf-8-sig'))
    blood={e['event_id'] for e in plan['events'] if e['notify_type']=='xxAnimNotifyState_Decal' and 'blood' in json.dumps(e['source']['properties']).lower()}
    for asset in sorted({e['asset'] for e in plan['events'] if e['event_id'] in blood}):
        a=unreal.load_asset(asset);changed=False
        for evt in unreal.AnimationLibrary.get_animation_notify_events(a):
            state=evt.get_editor_property('notify_state_class')
            if not isinstance(state,unreal.KZAnimNotifyState_MonsterVisual):continue
            fx=state.get_editor_property('Effect')
            if fx and str(fx.get_editor_property('EventId')) in blood:
                state.set_editor_property('Effect',None);changed=True;d['suppressed_blood_decals'].append({'asset':asset,'event':str(fx.get_editor_property('EventId'))})
        if changed:save(a)
    d['status']='passed'
except Exception:d['status']='failed';d['error']=traceback.format_exc();unreal.log_error(d['error'])
(OUT/'MaterialAuthor.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
