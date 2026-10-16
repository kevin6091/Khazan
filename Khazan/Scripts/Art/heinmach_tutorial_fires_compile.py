"""Real RHI shader verification of saved task materials; no live-editor access."""
from pathlib import Path
import json
import time
import traceback
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
META=ROOT/'Content/_Art/Player/Environment/HeinMach/Metadata/TutorialFires_20261006'
OUT=MAIN/'Saved/ImportReports/HeinMachTutorialFires_20261006'
DEST='/Game/_Art/Player/Environment/HeinMach/Reconstructed/TutorialFires'
START=time.monotonic();HANDLE=None


def tick(delta):
    if time.monotonic()-START<10:return
    unreal.unregister_slate_post_tick_callback(HANDLE)
    report={'materials':[],'passed':False}
    try:
        for path in unreal.EditorAssetLibrary.list_assets(DEST,recursive=True,include_folder=False):
            data=unreal.EditorAssetLibrary.find_asset_data(path)
            if str(data.asset_class_path.asset_name)!='Material':continue
            mat=unreal.load_asset(path)
            errors=list(unreal.MaterialEditingLibrary.recompile_material(mat))
            stat=unreal.MaterialEditingLibrary.get_statistics(mat)
            result={'asset':path,'errors':errors,'pixel_instructions':stat.num_pixel_shader_instructions,'vertex_instructions':stat.num_vertex_shader_instructions}
            report['materials'].append(result)
            assert not errors and stat.num_pixel_shader_instructions>0,result
            assert unreal.EditorAssetLibrary.save_loaded_asset(mat,False)
        report['passed']=True;print('KZ_HM_FIRES_COMPILE_PASSED')
    except Exception:
        report['error']=traceback.format_exc();unreal.log_error(report['error'])
    (OUT/'ShaderVerification.json').write_text(json.dumps(report,indent=2)+'\n')
    (META/'ShaderVerification.json').write_text(json.dumps(report,indent=2)+'\n')
    unreal.SystemLibrary.quit_editor()


HANDLE=unreal.register_slate_post_tick_callback(tick)
