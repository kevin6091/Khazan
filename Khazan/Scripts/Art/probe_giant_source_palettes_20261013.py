import unreal as u
from pathlib import Path
import json,os
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');out=Path(os.environ['KZ_COMBAT_FINISH_OUT']);lib=u.MaterialEditingLibrary
author=json.loads((main/'Metadata/GiantVFX_20261013/AssetAuthor02/Author.json').read_text(encoding='utf-8'));rows=[]
for p in author['materials']:
    name=p.rsplit('/',1)[-1]
    if not any(x in name for x in ['FMI_World_SubUV_color_A_','FMI_World_Fluid_A_','FMI_World_fluid_B_']):continue
    m=u.load_asset(p);rows.append({'material':p,'vectors':{str(n):str(lib.get_material_instance_vector_parameter_value(m,n)) for n in lib.get_vector_parameter_names(m)}})
(out/'Palettes.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print(json.dumps(rows,indent=2))
