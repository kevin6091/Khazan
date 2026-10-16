"""Import two missing original ice models and repair only owned render bindings."""
from pathlib import Path
import unreal as u
import os,json,struct,hashlib
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
work=Path(u.Paths.project_dir()).resolve()
assert work==main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
out=Path(os.environ['KZ_COMBAT_FINISH_OUT']);fx=u.FXConverterUtilitiesLibrary
folder='/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish'
ice=u.load_asset(folder+'/Materials/M_KZGiant_IceDebris');mist=u.load_asset(folder+'/Materials/M_KZGiant_SoftSnowMist');assert ice and mist
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
report={'imported_meshes':[],'render_bindings':[],'hidden_helpers':[]}
meshes={}
for row in json.loads((main/'Metadata/GiantVFX_20261013/ObjectOriginal/MeshExport/ExportReport.json').read_text(encoding='utf-8')):
    assert row['Success'];source=Path(row['DiskFilePaths'][0]);name=source.stem
    raw=bytearray(source.read_bytes());offset=0
    while offset<len(raw):
        chunk,flags,size,count=struct.unpack_from('<20siii',raw,offset);offset+=32
        if chunk.rstrip(b'\0')==b'MATT0000':
            for i in range(count):raw[offset+i*size:offset+i*size+64]=('KZGiant_Ice_'+str(i)).encode().ljust(64,b'\0')
        offset+=size*count
    staged=out/(name+'.pskx');staged.write_bytes(raw)
    task=u.AssetImportTask();task.set_editor_property('filename',str(staged));task.set_editor_property('destination_path',folder+'/OriginalObjects/Meshes')
    task.set_editor_property('destination_name',name);task.set_editor_property('automated',True);task.set_editor_property('save',False)
    task.set_editor_property('factory',u.PSKXFactory());task.set_editor_property('replace_existing',False)
    assert not u.EditorAssetLibrary.does_asset_exist(folder+'/OriginalObjects/Meshes/'+name)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(folder+'/OriginalObjects/Meshes/'+name);assert isinstance(mesh,u.StaticMesh)
    for i in range(len(mesh.get_editor_property('static_materials'))):mesh.set_material(i,ice)
    u.EditorAssetLibrary.set_metadata_tag(mesh,'KZGiantOriginalPayload',row['ObjectPath'])
    u.EditorAssetLibrary.set_metadata_tag(mesh,'KZGiantPayloadSHA256',hashlib.sha256(source.read_bytes()).hexdigest())
    assert u.EditorAssetLibrary.save_loaded_asset(mesh,only_if_is_dirty=False);meshes[name]=mesh
    report['imported_meshes'].append({'source':row['ObjectPath'],'payload_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'asset':mesh.get_path_name()})
for name in ['FP_Boss_Yetuga_IceBreath_explosion_01','FP_Boss_Yetuga_IceBreath_Smash_04']:
    p=u.load_asset(folder+'/OriginalObjects/'+name)
    source=main/'Metadata/GiantVFX_20261013/ObjectOriginal/Extracted/BBQ/Content/_Kazan_/Art/VFX/VFX_Particle/Monster/Boss_Yetuga'/(name+'.json')
    original=json.loads(source.read_text(encoding='utf-8-sig'))
    mesh_names={o['Name']:o['Properties']['Mesh']['ObjectName'].split("'")[1] for o in original if o['Type']=='ParticleModuleTypeDataMesh'}
    for emitter in fx.get_cascade_system_emitters(p):
        lod=fx.get_cascade_emitter_lod_level(emitter,0);req=fx.get_lod_level_required_module(lod);typ=fx.get_lod_level_type_data_module(lod)
        if isinstance(typ,u.ParticleModuleTypeDataMesh):
            wanted=mesh_names[typ.get_name()]
            if wanted in meshes:typ.set_editor_property('Mesh',meshes[wanted])
            # Source WM_SKL_Ice_Ground_002 / FMI_meshoffset_A_170 are absent from
            # the imported dependency closure. Preserve the original 3D mesh and
            # motion, with an explicitly recovered lit ice material.
            if not req.get_editor_property('Material'):
                req.set_editor_property('Material',ice);typ.set_editor_property('bOverrideMaterial',True)
                report['render_bindings'].append({'module':req.get_path_name(),'material':ice.get_path_name(),'source_material_status':'missing source shader; TEMP lit recovery'})
        elif fx.get_lod_level_is_enabled(lod) and not typ:
            req.set_editor_property('Material',mist)
            report['render_bindings'].append({'module':req.get_path_name(),'material':mist.get_path_name(),'source_material_status':'TEMP bounded snow density recovery'})
    assert u.EditorAssetLibrary.save_loaded_asset(p,only_if_is_dirty=False)
author=json.loads((main/'Metadata/GiantVFX_20261013/AssetAuthor02/Author.json').read_text(encoding='utf-8'))
for entry in author.get('helper_mesh_review',[]):
    p=u.load_asset(entry['system'])
    for emitter in fx.get_cascade_system_emitters(p):
        lod=fx.get_cascade_emitter_lod_level(emitter,0);typ=fx.get_lod_level_type_data_module(lod)
        if isinstance(typ,u.ParticleModuleTypeDataMesh) and typ.get_editor_property('Mesh') and typ.get_editor_property('Mesh').get_name()=='FS_axis':
            before=fx.get_lod_level_is_enabled(lod);assert len(lod.get_path_name())<256
            u.SystemLibrary.execute_console_command(world,'SETNOPEC "'+lod.get_path_name()+'" bEnabled False')
            assert not fx.get_lod_level_is_enabled(lod)
            report['hidden_helpers'].append({'lod':lod.get_path_name(),'before':before,'after':False,'mesh':'FS_axis'})
    assert u.EditorAssetLibrary.save_loaded_asset(p,only_if_is_dirty=False)
(out/'FieldDependencies.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('GIANT_FIELD_DEPENDENCIES_COMPLETE')
