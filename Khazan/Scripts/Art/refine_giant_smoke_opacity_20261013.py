"""Stop the unrecovered Opa_Str=10000 adapter from making solid smoke cards."""
from pathlib import Path
import unreal as u
import os,json

main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');work=Path(u.Paths.project_dir()).resolve()
assert work==main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
out=Path(os.environ['KZ_COMBAT_FINISH_OUT']);lib=u.MaterialEditingLibrary
author=json.loads((main/'Metadata/GiantVFX_20261013/AssetAuthor02/Author.json').read_text(encoding='utf-8'))
rows=[]
for original,dest in author['materials'].items():
    if 'FMI_World_SubUV_color_A_yetuga_' not in original:continue
    mi=u.load_asset(dest);before=lib.get_material_instance_scalar_parameter_value(mi,'Opa_Str')
    if before<=1:continue
    # TEMP in the interpreted project shader, not a change to the original
    # parameter or a claim of recovered native opacity math. HDR RGB unchanged.
    lib.set_material_instance_scalar_parameter_value(mi,'Opa_Str',1)
    lib.update_material_instance(mi);assert u.EditorAssetLibrary.save_loaded_asset(mi,only_if_is_dirty=False)
    rows.append({'original':original,'owned':dest,'old_interpreted_gain':before,'temporary_gain':1,'reason':'Raw source gain cannot be applied as linear alpha in reconstructed shader; caused visible full cards.'})
(out/'SmokeOpacity.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
u.log('GIANT_SMOKE_OPACITY_REFINED '+str(len(rows)))
