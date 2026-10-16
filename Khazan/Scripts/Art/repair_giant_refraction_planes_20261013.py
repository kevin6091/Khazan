"""Bound the unrecovered shock-wave mesh shader instead of drawing a white quad."""
from pathlib import Path
import unreal as u
import json,os
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');assert Path(u.Paths.project_dir()).resolve()==main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
out=Path(os.environ['KZ_COMBAT_FINISH_OUT']);root='/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish/Materials';lib=u.MaterialEditingLibrary;parent=u.load_asset(root+'/M_KZGiant_SoftPowder');assert parent;rows=[]
for path in u.EditorAssetLibrary.list_assets(root,recursive=True):
    m=u.load_asset(path)
    if isinstance(m,u.MaterialInstanceConstant) and m.get_name().startswith('KZ_FMI_MashRefractionShock_01_DepthFade_'):
        lib.set_material_instance_parent(m,parent);lib.update_material_instance(m);assert u.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
        rows.append({'material':m.get_path_name(),'reason':'TEMP source refraction shader topology unrecovered; RHI shows FS_bill as opaque white quad. Existing organic source mask and native sphere/depth support render a soft frost pulse.'})
assert rows;(out/'RefractionPlaneRepair.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
cases=[];probe=json.loads((main/'Metadata/GiantVFX_20261013/Probe02/Probe.json').read_text(encoding='utf-8'))
for path in probe['sequences']:
    if 'Yetuga' in path and any(t in path for t in ['Attack_Armageddon_Jump_Start.','Attack_Armageddon_Jump_End.','Attack_Armageddon_Jump_End_Close.']):cases.append([path.split('.')[-1],'Yetuga','animation',path])
(main/'Metadata/GiantVFX_20261013/RefractionAffectedCases.tsv').write_text('\n'.join('\t'.join(c) for c in cases),encoding='utf-8')
