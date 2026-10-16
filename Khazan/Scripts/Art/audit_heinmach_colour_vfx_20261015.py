"""Read current gameplay/map VFX reachability, material colour paths and hit bindings."""
from pathlib import Path
from collections import deque
import hashlib,json,os,traceback
import unreal as u

root=Path(u.Paths.project_dir()).resolve()
out=Path(os.environ['KZ_HM_COLOUR_OUT'])
registry=u.AssetRegistryHelpers.get_asset_registry()
registry.wait_for_completion()
lib=u.MaterialEditingLibrary
report={'status':'running','asset_saves':0,'maps':[],'definitions':[],'monster_defaults':[],
        'brutal_effects':[],'systems':[],'materials':[],'roots':[]}

def package_path(obj):return obj.get_path_name().split('.')[0]
def sha(package):
    if not package.startswith('/Game/'):return None
    rel='Content/'+package.removeprefix('/Game/')
    p=root/(rel+('.umap' if package in maps else '.uasset'))
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
def serial(value):
    if isinstance(value,u.Object):return value.get_path_name()
    if value is None or isinstance(value,(float,int,str,bool)):return value
    return value.export_text() if hasattr(value,'export_text') else str(value)
def props(obj,names):
    row={}
    for name in names:
        try:row[name]=serial(obj.get_editor_property(name))
        except Exception:pass
    return row
def cls(package):
    data=registry.get_assets_by_package_name(package)
    return str(data[0].asset_class_path.asset_name) if data else ''
def deps(package):return [str(x) for x in registry.get_dependencies(package,u.AssetRegistryDependencyOptions())]

maps=['/Game/Maps/DevMap','/Game/Maps/L_HeinMach_Environment']
roots=set(maps)
for data in registry.get_assets_by_path('/Game/Data',recursive=True):roots.add(str(data.package_name))
try:
    # Existing gameplay references are the boundary. This is not an inventory of
    # every extracted PS, texture, or unused animation in Content.
    systems=set();visited=set();todo=deque(sorted(roots))
    skip={'StaticMesh','SkeletalMesh','Skeleton','PhysicsAsset','Texture2D','TextureCube','Material',
          'MaterialInstanceConstant','MaterialFunction','SoundWave','SoundCue','CurveFloat','CurveVector','CurveLinearColor'}
    while todo:
        package=todo.popleft()
        if package in visited or not package.startswith('/Game/'):continue
        visited.add(package);kind=cls(package)
        if kind in ('ParticleSystem','NiagaraSystem'):
            systems.add(package);continue
        if kind in skip:continue
        todo.extend(deps(package))
        assert len(visited)<25000,'Unexpected gameplay dependency expansion'
    for path in maps:
        world=u.EditorLoadingAndSavingUtils.load_map(path);assert world,path
        actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
        row={'map':path,'sha256':sha(path),'actor_count':len(actors),'postprocess':[],'lights':[]}
        for actor in actors:
            if isinstance(actor,u.PostProcessVolume):
                row['postprocess'].append({'actor':actor.get_actor_label(),**props(actor,['enabled','priority','unbound','blend_weight']),
                    'settings':actor.get_editor_property('settings').export_text()})
            for component in actor.get_components_by_class(u.LightComponentBase):
                if isinstance(component,(u.DirectionalLightComponent,u.SkyLightComponent)):
                    row['lights'].append({'actor':actor.get_actor_label(),'class':component.get_class().get_name(),
                        **props(component,['intensity','light_color','light_source_angle','specular_scale','real_time_capture'])})
            for component in actor.get_components_by_class(u.ParticleSystemComponent):
                template=component.get_editor_property('template')
                if template:systems.add(package_path(template))
            for component in actor.get_components_by_class(u.NiagaraComponent):
                template=component.get_asset()
                if template:systems.add(package_path(template))
            if isinstance(actor,u.KZMonster):
                default=u.get_default_object(actor.get_class())
                item={'class':actor.get_class().get_path_name(),**props(default,['HitBloodEffect','HitBloodDecalMaterial'])}
                if item not in report['monster_defaults']:report['monster_defaults'].append(item)
                particle=default.get_editor_property('HitBloodEffect')
                if particle:systems.add(package_path(particle))
        report['maps'].append(row)
    for package in sorted(visited):
        if cls(package)!='KZCharacterDefinitionData':continue
        obj=u.load_asset(package);settings=obj.get_editor_property('HitReactions')
        report['definitions'].append({'asset':package,'sha256':sha(package),
            'HitReactions':settings.export_text(),**props(settings,['ImpactEffect'])})
        particle=settings.get_editor_property('ImpactEffect')
        if particle:systems.add(package_path(particle))
    for name in ('AM_DAS_BrutalFront','AM_DAS_BrutalBack'):
        path='/Game/_Art/Player/Animation/InGame/DAS/BrutalAttack/'+name
        montage=u.load_asset(path);assert montage,path
        for event in u.AnimationLibrary.get_animation_notify_events(montage):
            parent=event.get_editor_property('Notify')
            if not isinstance(parent,u.KZAnimNotify_CombatEffect):continue
            for effect in [parent]+list(parent.get_editor_property('BatchedEffects')):
                if effect.get_editor_property('bEndEvent'):continue
                report['brutal_effects'].append({'montage':path,**props(effect,['EventId','ParticleTemplate','NiagaraTemplate',
                    'bOnAttackSuccessed','WindowStartTime','WindowEndTime','RelativeLocation','RelativeRotation','Scale3D'])})
    for path in ['/Game/_Art/Effects/Combat/Blood/PP_Dmg_Blood_Trail_Sub',
                 '/Game/_Art/Effects/Combat/Blood/FP_Monster_HitBloodReference',
                 '/Game/_Art/Effects/Combat/Blood/M_Monster_HitBloodGround']:
        obj=u.load_asset(path);assert obj,path
        task=u.AssetExportTask();task.object=obj;task.filename=str(out/(path.split('/')[-1]+'.t3d'))
        task.exporter=u.ObjectExporterT3D();task.automated=True;task.prompt=False
        assert u.Exporter.run_asset_export_task(task),path
    material_paths=set()
    for system in sorted(systems):
        seen=set();todo=deque([system]);used=set()
        while todo:
            package=todo.popleft()
            if package in seen:continue
            seen.add(package);kind=cls(package)
            if kind in ('Material','MaterialInstanceConstant'):
                used.add(package);material_paths.add(package);continue
            if kind.startswith('Texture') or kind.startswith('Sound'):continue
            if not package.startswith(('/Game/','/Niagara/')):continue
            todo.extend(deps(package))
            assert len(seen)<8000,(system,'VFX dependency expansion')
        report['systems'].append({'asset':system,'class':cls(system),'sha256':sha(system),'materials':sorted(used)})
    masters={}
    for path in sorted(material_paths):
        obj=u.load_asset(path)
        if not isinstance(obj,u.MaterialInterface):continue
        item={'material':path,'sha256':sha(path)}
        parent=obj
        if isinstance(obj,u.MaterialInstanceConstant):
            item.update(props(obj,['parent','base_property_overrides']))
        while isinstance(parent,u.MaterialInstance):parent=parent.get_editor_property('parent')
        if not isinstance(parent,u.Material):continue
        item['root']=package_path(parent);masters[item['root']]=parent
        report['materials'].append(item)
    for path,obj in sorted(masters.items()):
        nodes=list(lib.get_material_expressions(obj))
        emission=lib.get_material_property_input_node(obj,u.MaterialProperty.MP_EMISSIVE_COLOR)
        report['roots'].append({'material':path,'sha256':sha(path),
            **props(obj,['material_domain','blend_mode','shading_model','translucency_pass','disable_depth_test','disable_pre_exposure_scale','bUseTranslucencyVertexFog']),
            'emissive_node':emission.get_class().get_name() if emission else None,
            'eye_adaptation_inverse_count':sum(isinstance(node,u.MaterialExpressionEyeAdaptationInverse) for node in nodes),
            'parameters':[{'class':node.get_class().get_name(),**props(node,['parameter_name','default_value'])}
                          for node in nodes if isinstance(node,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter))]})
    report['gameplay_packages_visited']=len(visited)
    report['status']='passed'
except Exception:
    report['status']='failed';report['error']=traceback.format_exc();u.log_error(report['error'])
finally:
    (out/'Usage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert report['status']=='passed',report.get('error')
print('HEIN_COLOUR_AUDIT',len(report['systems']),len(report['materials']),len(report['roots']))
