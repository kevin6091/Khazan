"""Read-only T3D exports of the 49 current particle systems used by these giants."""
from pathlib import Path
import os, json, hashlib
import unreal as u

main = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
out = Path(os.environ['KZ_COMBAT_FINISH_OUT'])
probe = json.loads((main/'Metadata/GiantVFX_20261013/Probe02/Probe.json').read_text(encoding='utf-8'))
(out/'Exports').mkdir()
report = {'systems': {}, 'materials': {}, 'saved': 0}
for path in probe['systems']:
    system = u.load_asset(path)
    filename = out/'Exports'/(system.get_name()+'.t3d')
    task = u.AssetExportTask();task.object=system;task.filename=str(filename)
    task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.ObjectExporterT3D()
    assert u.Exporter.run_asset_export_task(task)
    report['systems'][path] = {'export': str(filename), 'sha256': hashlib.sha256(filename.read_bytes()).hexdigest()}
    try:
        emitters = list(system.get_editor_property('emitters'))
        report['systems'][path]['emitters'] = len(emitters)
    except Exception as error:
        report['systems'][path]['python_emitters_error'] = str(error)
(out/'Export.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
u.log('GIANT_PARTICLE_EXPORT_DONE: '+str(len(report['systems'])))
