from pathlib import Path
import json,os,shutil,unreal as u
ROOT=Path(__file__).resolve().parents[2];OUT=Path(os.environ['KZ_PARRY_PHOTO_OUT'])
DEST='/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Reference/PP_Player_Parry_Reference'
H={};s=(ROOT/'Scripts/Art/author_monster_hit_flash_20261012.py').read_text(encoding='utf-8').split('\ntry:\n    flash = particle()')[0]
exec(compile(s,'cascade_helpers','exec'),H);H.update(OUT=OUT,DEST=DEST)
ps=u.load_asset(DEST);size=u.load_object(None,ps.get_path_name()+':KZPhotoHaloSize');assert size
shutil.copy2(ROOT/('Content/'+DEST.removeprefix('/Game/')+'.uasset'),OUT/'Before.uasset')
# Restore source X=250cm and mirror it to the CPU square axes. Remove the
# provisional half-extent tuning, while retaining explicit CPU geometry.
H['dist'](size,'StartSize','DistributionVectorConstant',{'Constant':'(X=250,Y=250,Z=250)'})
H['rebuild'](ps);assert u.EditorAssetLibrary.save_loaded_asset(ps,only_if_is_dirty=False)
(OUT/'Extent.json').write_text(json.dumps({'status':'saved','source_x_cm':250,'cpu_axes_cm':[250,250,250],'classification':'Source X retained; Y/Z technical CPU square adapter; not original GPU renderer parity'},indent=2),encoding='utf-8')
