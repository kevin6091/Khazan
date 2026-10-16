"""Saved parameter/graph checks plus real RHI compile of the currently used masters."""
from pathlib import Path
import hashlib,json,os,traceback
import unreal as u
MAIN=Path(os.environ['KZ_ALPHA_MAIN']);OUT=Path(os.environ['KZ_ALPHA_OUT']);PROJECT=Path(u.Paths.project_dir()).resolve()
plan=json.loads((MAIN/'Metadata/ParticleAlpha_20261013/RepairPlan.json').read_text())
audit=json.loads((MAIN/'Metadata/ParticleAlpha_20261013/Audit02/Audit.json').read_text(encoding='utf-8'))
R={'status':'running','project':str(PROJECT),'asset_saves':0,'instances':[],'masters':[],'files':[],'errors':[]}
try:
    import re
    for row in plan['rows']:
        mi=u.load_asset(row['material']);param='KZAlphaFromRed_'+re.sub(r'\W','_',row['parameter'] or row['texture'].rsplit('/',1)[-1].split('.')[0])
        assert u.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi,param)==1
        assert u.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi,'KZAlphaCardRepair')==1
        R['instances'].append({'path':row['material'],'red_density':1,'repair':1})
    for path in sorted({r['path'] for r in audit['materials'] if r['class']=='Material'}):
        mat=u.load_asset(path);errors=[str(e) for e in u.MaterialEditingLibrary.recompile_material(mat)]
        stats=u.MaterialEditingLibrary.get_statistics(mat)
        R['masters'].append({'path':path,'compile_errors':errors,'pixel_instructions':stats.num_pixel_shader_instructions})
        if errors:R['errors'].append(R['masters'][-1])
        (OUT/'Verification.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
    for path in plan['targets']:
        f=PROJECT/('Content/'+path.removeprefix('/Game/')+'.uasset')
        R['files'].append({'path':path,'relative':str(f.relative_to(PROJECT)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
    for path in {r['master'] for r in plan['rows']}|{plan['default_particle']}:
        mat=u.load_asset(path);assert u.EditorAssetLibrary.get_metadata_tag(mat,'KZAlphaRepair20261013'),path
    budget=u.load_asset('/Game/_Art/Player/Environment/Rendering/HeinMachWeather/NET_HM_WeatherBudget')
    R['snow']=budget.get_editor_property('emitter_scalability_settings').export_text()
    assert 'SpawnCountScale=0.200000' in R['snow']
    R['status']='passed' if not R['errors'] else 'failed'
except Exception:R['status']='failed';R['error']=traceback.format_exc()
(OUT/'Verification.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print('ALPHA_RHI_VERIFICATION',R['status'],'masters',len(R['masters']),'errors',len(R['errors']),flush=True)
u.SystemLibrary.quit_editor()
