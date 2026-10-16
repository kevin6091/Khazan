"""Repair only existing mask input links; preserve source radius/color adapter."""
from pathlib import Path
import os,json,hashlib,shutil
import unreal
ROOT=Path(unreal.Paths.project_dir()).resolve()
assert ROOT==Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT=Path(os.environ['KZ_COMBAT_UI_OUTPUT'])
path='/Game/UI/Combat/Materials/M_UI_BrutalRing'
file=ROOT/'Content/UI/Combat/Materials/M_UI_BrutalRing.uasset'
before=hashlib.sha256(file.read_bytes()).hexdigest()
shutil.copy2(file,OUT/'Before_M_UI_BrutalRing.uasset')
mat=unreal.load_asset(path);assert mat
lib=unreal.MaterialEditingLibrary
nodes=lib.get_material_expressions(mat)
custom=next(n for n in nodes if isinstance(n,unreal.MaterialExpressionCustom))
masks=[n for n in nodes if isinstance(n,unreal.MaterialExpressionComponentMask)]
assert len(masks)==2
mat.modify()
for mask in masks:assert lib.connect_material_expressions(custom,'',mask,'')
errors=list(lib.recompile_material(mat));assert not errors,errors
stats=lib.get_statistics(mat)
assert unreal.EditorAssetLibrary.save_loaded_asset(mat,only_if_is_dirty=False)
report={'status':'saved','asset':path,'before_sha256':before,'after_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'change':'Existing custom RGBA -> mask default input pins. Radius/color/formula unchanged. Fresh RHI validation required.','compile_errors':errors,'pixel_instructions':stats.num_pixel_shader_instructions}
(OUT/'RingRepair.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('COMBAT_UI_RING_LINK_REPAIR_SAVED')
