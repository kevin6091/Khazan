"""Check real DX12 shaders for the reference-fit existing material graphs."""
from pathlib import Path
import json
import time
import traceback
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
OUT=ROOT/'Saved/ImportReports/HeinMachReference_20261006'
START=time.monotonic()
HANDLE=None


def tick(delta):
    if time.monotonic()-START<10:return
    unreal.unregister_slate_post_tick_callback(HANDLE)
    report={'materials':[]}
    try:
        for path in ['/Game/_Art/Player/Environment/Rendering/HeinMachWeather/'+name for name in
                     ('M_HM_RegionalLook','M_HM_SourceSnow','M_HM_SourceDust')]+['/Game/__HeinMachQA/'+name for name in
                     ('M_Regional_Legacy','M_HM_SourceSnow_Legacy','M_HM_SourceDust_Legacy')]:
            mat=unreal.load_asset(path)
            errors=list(unreal.MaterialEditingLibrary.recompile_material(mat))
            instructions=unreal.MaterialEditingLibrary.get_statistics(mat).num_pixel_shader_instructions
            report['materials'].append({'asset':path,'errors':errors,'instructions':instructions})
            assert not errors and instructions>0,report['materials'][-1]
            assert unreal.EditorAssetLibrary.save_loaded_asset(mat,only_if_is_dirty=False)
        print('KZ_HEINMACH_REFERENCE_COMPILE_PASSED')
    except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
    (OUT/'ShaderVerification.json').write_text(json.dumps(report,indent=2)+'\n')
    unreal.SystemLibrary.quit_editor()


HANDLE=unreal.register_slate_post_tick_callback(tick)
