"""Upgrade owned snow materials to the native toroidal field, without recloning terrain."""
from pathlib import Path
import importlib.util
import unreal
assert Path(unreal.Paths.project_dir()).resolve()==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
path=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Scripts/Art/heinmach_snow_author.py')
spec=importlib.util.spec_from_file_location('snow_author',path)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
for group in ('Landscape1','Landscape2'):mod.build_material(group,{})
print('SNOW_FIELD_MATERIALS_UPGRADED')
