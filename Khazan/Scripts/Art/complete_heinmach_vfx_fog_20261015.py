"""Finish current referenced VFX roots, including heal and tutorial fire."""
from pathlib import Path
import hashlib,json,os,shutil
import unreal as u
main=Path(os.environ['KZ_HM_COLOUR_MAIN']);root=Path(u.Paths.project_dir()).resolve()
assert root==main.parent.parent/'Khazan_HeinColourVFXWork_20261015'/'Khazan'
out=Path(os.environ['KZ_HM_COLOUR_OUT']);lib=u.MaterialEditingLibrary
usage=json.loads((main/'Metadata/HeinMachColourVFX_20261015/CandidateAudit03/Usage.json').read_text(encoding='utf-8'))
prep=json.loads((main/'Metadata/HeinMachColourVFX_20261015/Preparation.json').read_text(encoding='utf-8'))
rows=[];additional={}
for row in usage['roots']:
    path=row['material']
    if not path.startswith('/Game/') or 'MD_SURFACE' not in row.get('material_domain',''):continue
    material=u.load_asset(path);assert material
    rel='Content/'+path.removeprefix('/Game/')+'.uasset';file=root/rel
    before=hashlib.sha256(file.read_bytes()).hexdigest()
    if rel not in prep['targets']:
        original=main/rel;expected=hashlib.sha256(original.read_bytes()).hexdigest()
        assert before==expected,(rel,'QA integration target changed before baseline')
        backup=out/'AdditionalBefore'/rel;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original,backup)
        additional[rel]=expected
    fog=bool(material.get_editor_property('bUseTranslucencyVertexFog'))
    depth=bool(material.get_editor_property('disable_depth_test'))
    if fog:
        material.set_editor_property('bUseTranslucencyVertexFog',False)
        errors=list(lib.recompile_material(material));assert not errors,(path,errors)
        assert u.EditorAssetLibrary.save_loaded_asset(material,only_if_is_dirty=False)
    assert material.get_editor_property('disable_depth_test')==depth,path
    rows.append({'asset':path,'changed':fog,'before_sha256':before,
                 'after_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'depth_test_disabled':depth})
for name in ('FP_LVL_WBP_LightObj_001_FIRE_medium','FP_LVL_WBP_LightObj_001_fire_small'):
    path='/Game/_Art/Player/Environment/HeinMach/Reconstructed/TutorialFires/Particles/'+name
    obj=u.load_asset(path);assert obj
    task=u.AssetExportTask();task.object=obj;task.filename=str(out/(name+'.t3d'))
    task.exporter=u.ObjectExporterT3D();task.automated=True;task.prompt=False
    assert u.Exporter.run_asset_export_task(task)
(out/'FogCompletion.json').write_text(json.dumps({'status':'passed','rows':rows,'additional_targets':additional,
    'basis':'Only current VFX material references; native fog flag changed, alpha/graph/depth behavior retained'},indent=2),encoding='utf-8')
print('VFX_FOG_COMPLETE',len(rows),sum(row['changed'] for row in rows))
