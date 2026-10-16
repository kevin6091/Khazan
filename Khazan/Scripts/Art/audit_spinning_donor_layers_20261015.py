"""Read the four reused systems and per-emitter bindings only; save nothing."""
from pathlib import Path
import json,os,re,unreal as u
out=Path(os.environ['KZ_LOOKSPIN_OUT']);FX=u.FXConverterUtilitiesLibrary
base='/Game/_Art/Effects/DualAxeSword/Core/'
names=['FP_Kazan_SpinningBeast_Axe_Slash_01','FP_Kazan_DualaxeSword_Overfury_slash_01',
       'FP_PlaneSlash_Flow_Strong','FP_Kazan_Dualaxesword_flow_burst_01']
def path(obj):return obj.get_path_name() if obj else None
def export(obj):
    target=out/(obj.get_name()+'.t3d');task=u.AssetExportTask();task.object=obj
    task.filename=str(target);task.exporter=u.ObjectExporterT3D();task.automated=True;task.prompt=False
    assert u.Exporter.run_asset_export_task(task)
    return target
rows=[]
for name in names:
    system=u.load_asset(base+name);assert system
    file=export(system);record=dict(asset=path(system),emitters=[])
    for index,emitter in enumerate(FX.get_cascade_system_emitters(system)):
        for level in range(max(1,len(system.get_editor_property('lod_distances')))):
            lod=FX.get_cascade_emitter_lod_level(emitter,level);required=FX.get_lod_level_required_module(lod)
            material=required.get_editor_property('Material');type_data=FX.get_lod_level_type_data_module(lod)
            row=dict(index=index,lod=level,emitter=path(emitter),enabled=FX.get_lod_level_is_enabled(lod),
                     material=path(material),type_data=path(type_data),modules=[path(x) for x in FX.get_lod_level_modules(lod)])
            if material:
                export(material)
                parent=material.get_editor_property('parent') if isinstance(material,u.MaterialInstanceConstant) else None
                if parent:export(parent)
            record['emitters'].append(row)
    rows.append(record)
(out/'Layers.json').write_text(json.dumps(dict(status='passed',asset_saves=0,rows=rows),indent=2),encoding='utf-8')
print('SPIN_DONOR_LAYERS_AUDITED',sum(len(x['emitters']) for x in rows))
