"""Target the proven retained snow projector and its original shader inputs."""
from pathlib import Path
import json, os, unreal as u
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
out=Path(os.environ['KZ_COMBAT_FINISH_OUT'])
probe=json.loads((main/'Metadata/GiantVFX_20261013/Probe02/Probe.json').read_text(encoding='utf-8'))
rows=[];materials={}
for path in probe['sequences']:
    if 'Yetuga' not in path and 'ApesStoneHandElite' not in path:continue
    a=u.load_asset(path)
    for event in u.AnimationLibrary.get_animation_notify_events(a):
        n=event.get_editor_property('notify_state_class')
        if isinstance(n,u.KZAnimNotifyState_MonsterVisual):
            effect=n.get_editor_property('effect')
            if not effect:continue
            mat=effect.get_editor_property('decal_material')
            if mat and 'FMI_Decal_Deferred_D_02' in mat.get_name():
                rows.append(dict(asset=path,notify=n.get_path_name(),effect=effect.get_path_name(),event=event.export_text(),effect_export=effect.export_text() if hasattr(effect,'export_text') else '',material=mat.get_path_name()))
                materials[mat.get_path_name()]=mat
assert rows
shader=[]
for path,mi in materials.items():
    parent=mi.get_editor_property('parent')
    shader.append(dict(material=path,parent=parent.get_path_name(),textures=[p.export_text() for p in mi.get_editor_property('texture_parameter_values')],scalars=[p.export_text() for p in mi.get_editor_property('scalar_parameter_values')],overrides=mi.get_editor_property('base_property_overrides').export_text()))
    for obj in [mi,parent]:
        t=u.AssetExportTask();t.object=obj;t.filename=str(out/(obj.get_name()+'.t3d'));t.automated=True;t.prompt=False;t.replace_identical=True;t.exporter=u.ObjectExporterT3D();assert u.Exporter.run_asset_export_task(t)
(out/'SnowDecalProbe.json').write_text(json.dumps(dict(rows=rows,materials=shader,asset_saves=0),indent=2),encoding='utf-8')
