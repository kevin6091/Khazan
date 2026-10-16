"""Read-only target mesh units/materials for the captured grab artifact."""
from pathlib import Path
import unreal as u
import json,os
out=Path(os.environ['KZ_COMBAT_FINISH_OUT']);lib=u.MaterialEditingLibrary;r={'meshes':[],'materials':[],'saves':0}
for name in ['T_SM_Blood03','T_SM_Blood05','FS_bill']:
    path='/Game/_Art/Effects/Shared/Meshes/BBQ_Mesh/'+('Physics/' if name.startswith('T_SM') else '')+name
    m=u.load_asset(path);b=m.get_bounding_box();r['meshes'].append({'path':path,'min':str(b.min),'max':str(b.max),'extent':str((b.max-b.min)*.5)})
for name in ['T_M_Blood03_inst','T_M_Blood05_inst2']:
    path='/Game/_Art/Effects/Shared/Meshes/BBQ_Mesh/Physics/'+name;m=u.load_asset(path)
    if not m:continue
    row={'path':m.get_path_name(),'parent':str(m.get_editor_property('parent')),'parameters':[]}
    for field in ['scalar_parameter_values','vector_parameter_values','texture_parameter_values','base_property_overrides']:
        row[field]=str(m.get_editor_property(field))
    for t in lib.get_material_instance_texture_parameter_names(m):row['parameters'].append({'name':str(t),'value':str(lib.get_material_instance_texture_parameter_value(m,t))})
    r['materials'].append(row)
(out/'GrabBloodProbe.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
