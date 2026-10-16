"""New particle package avoids replacing a file held by the user's live editor."""
from pathlib import Path
import os,json,unreal,traceback
ROOT=Path(unreal.Paths.project_dir()).resolve();assert 'Khazan_GiantFallWork_20261011' in str(ROOT)
OUT=Path(os.environ['KZ_BLOOD_REFERENCE_OUT']);d={'status':'running'}
try:
    source=unreal.load_asset('/Game/_Art/Effects/Combat/Blood/FP_Monster_HitBlood');assert source
    dest='/Game/_Art/Effects/Combat/Blood/FP_Monster_HitBloodReference'
    assert not unreal.load_asset(dest)
    a=unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset('FP_Monster_HitBloodReference','/Game/_Art/Effects/Combat/Blood',source);assert a
    assert unreal.EditorAssetLibrary.save_loaded_asset(a,only_if_is_dirty=False)
    d.update(status='passed',asset=a.get_path_name(),source=source.get_path_name(),original_main_replaced=False)
except Exception:d.update(status='failed',error=traceback.format_exc());unreal.log_error(d['error'])
(OUT/'ParticleClone.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
