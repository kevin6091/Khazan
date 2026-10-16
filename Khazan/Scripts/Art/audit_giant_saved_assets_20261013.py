"""Read-only raw animation, notify, object and owned dependency verification."""
from pathlib import Path
import unreal as u
import os,json,hashlib,re
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');work=main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
project=Path(u.Paths.project_dir()).resolve();assert project in [main,work]
out=Path(os.environ['KZ_COMBAT_FINISH_OUT']);author=json.loads((main/'Metadata/GiantVFX_20261013/AssetAuthor02/Author.json').read_text(encoding='utf-8'))
fx=u.FXConverterUtilitiesLibrary
reverse={v:k for k,v in author['particles'].items()}
decal_receipt=main/'Metadata/GiantVFX_20261013/SnowDecalRepair02/SnowDecalRepair.json'
if decal_receipt.exists():
    decal=json.loads(decal_receipt.read_text(encoding='utf-8'))
    # One explicitly reviewed presentation-only material substitution.
    # All other original notify fields, clocks and animation data remain strict.
    reverse[decal['material']]=decal['source_material']
report={'project':str(project),'sequences':{},'objects':{},'owned_dependencies':[],'renderers':[],'null_render_bindings':[],'saves':0}
def export(obj):
    target=out/'Scratch.t3d';t=u.AssetExportTask();t.object=obj;t.filename=str(target);t.automated=True;t.prompt=False;t.replace_identical=True;t.exporter=u.ObjectExporterT3D()
    assert u.Exporter.run_asset_export_task(t);return target.read_bytes()
def normalized(text):
    for replacement,source in reverse.items():text=text.replace(replacement,source)
    return re.sub(r'^\s*bUseWorldParticleUnits=True\s*\r?\n','',text,flags=re.M)
for path in author['changed_sequences']:
    seq=u.load_asset(path);assert seq
    model=seq.controller.get_model_interface();rate=model.get_frame_rate()
    record={'raw_model_sha256':hashlib.sha256(export(model)).hexdigest(),'frames':model.get_number_of_frames(),'keys':model.get_number_of_keys(),'fps':[rate.numerator,rate.denominator],
            'seconds':seq.get_play_length(),'settings':{n:str(seq.get_editor_property(n)) for n in ['enable_root_motion','force_root_lock','root_motion_root_lock','rate_scale','interpolation','additive_anim_type','ref_pose_type']},'events':[]}
    for event in u.AnimationLibrary.get_animation_notify_events(seq):
        state=event.get_editor_property('notify_state_class');notify=event.get_editor_property('notify')
        entry={'event':event.export_text()}
        obj=state or notify
        if obj:
            entry['notify_sha256']=hashlib.sha256(normalized(export(obj).decode('utf-8-sig')).encode()).hexdigest()
        record['events'].append(entry)
    report['sequences'][path]=record
for family in ['ApesStoneHandElite','Yetuga']:
    da=u.load_asset('/Game/Monsters/'+family+'/Data/DA_OriginalPatterns_'+family)
    report['objects'][family]=[o.export_text() for o in da.get_editor_property('pattern_objects')]
if project==work or u.EditorAssetLibrary.does_asset_exist('/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish/Materials/M_KZGiant_SoftSnowMist'):
    reg=u.AssetRegistryHelpers.get_asset_registry();options=u.AssetRegistryDependencyOptions(include_hard_package_references=True,include_soft_package_references=True,include_searchable_names=False,include_hard_management_references=False,include_soft_management_references=False)
    prefix='/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish/'
    queue=[p.split('.',1)[0] for p in author['particles'].values()]+[prefix+'OriginalObjects/'+n for n in ['FP_Boss_Yetuga_IceBreath_explosion_01','FP_Boss_Yetuga_IceBreath_Smash_04']]
    if decal_receipt.exists() and u.EditorAssetLibrary.does_asset_exist(decal['material'].split('.',1)[0]):
        queue.append(decal['material'].split('.',1)[0])
    for family in ['ApesStoneHandElite','Yetuga']:
        da=u.load_asset('/Game/Monsters/'+family+'/Data/DA_OriginalPatterns_'+family)
        for obj in da.get_editor_property('pattern_objects'):
            for field in ['SpawnEffect','FlightEffect','ImpactEffect']:
                ps=obj.get_editor_property(field)
                if ps:queue.append(ps.get_path_name().split('.',1)[0])
    seen=set()
    while queue:
        package=queue.pop()
        if package in seen:continue
        seen.add(package);assert u.EditorAssetLibrary.does_asset_exist(package),package
        for dep in reg.get_dependencies(package,options):
            if str(dep).startswith(prefix):queue.append(str(dep))
    report['owned_dependencies']=sorted(seen)
    for path in [p for p in seen if isinstance(u.load_asset(p),u.ParticleSystem)]:
        p=u.load_asset(path)
        for emitter in fx.get_cascade_system_emitters(p):
            for li in range(len(p.get_editor_property('lod_distances'))):
                lod=fx.get_cascade_emitter_lod_level(emitter,li)
                if not fx.get_lod_level_is_enabled(lod):continue
                req=fx.get_lod_level_required_module(lod);typ=fx.get_lod_level_type_data_module(lod);mat=req.get_editor_property('Material')
                r={'system':path,'emitter':emitter.get_name(),'lod':li,'material':mat.get_path_name() if mat else None}
                if isinstance(typ,u.ParticleModuleTypeDataMesh):
                    mesh=typ.get_editor_property('Mesh');r['mesh']=mesh.get_path_name() if mesh else None
                    if not mesh:report['null_render_bindings'].append(r)
                    # An explicit Required Material overrides the mesh slots; otherwise
                    # valid mesh slot bindings are an intentional native renderer path.
                    if not mat and mesh and not all(x.material_interface for x in mesh.get_editor_property('static_materials')):report['null_render_bindings'].append(r)
                elif not mat:report['null_render_bindings'].append(r)
                report['renderers'].append(r)
(out/'SavedAudit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('GIANT_SAVED_AUDIT: sequences='+str(len(report['sequences']))+' nullRenderBindings='+str(len(report['null_render_bindings'])))
