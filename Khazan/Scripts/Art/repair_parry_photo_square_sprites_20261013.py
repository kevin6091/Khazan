from pathlib import Path
import json,os,re,unreal as u
ROOT=Path(__file__).resolve().parents[2];OUT=Path(os.environ['KZ_PARRY_PHOTO_OUT'])
BASE='/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Reference';DEST=BASE+'/PP_Player_Parry_Reference'
H={};s=(ROOT/'Scripts/Art/author_monster_hit_flash_20261012.py').read_text(encoding='utf-8').split('\ntry:\n    flash = particle()')[0]
s=s.replace("'bEnabled':'FBoolProperty'", "'bEnabled':'FBoolProperty','ScreenAlignment':'FByteProperty'")
exec(compile(s,'cascade_helpers','exec'),H);H.update(OUT=OUT,DEST=DEST)
ps=u.load_asset(DEST);t=H['export'](ps,'Before.t3d');rows=[]
for match in re.finditer(r'^      Begin Object Name="([^\"]+)" .*?^      End Object',t,re.M|re.S):
    if not match.group(1).startswith('ParticleLODLevel'):continue
    path=re.search(r"ExportPath=\"[^']+'([^']+)'",match.group(0)).group(1)
    if not any(x in path for x in ['ParticleSpriteEmitter_0.','ParticleSpriteEmitter_2.','ParticleSpriteEmitter_13.']):continue
    ref=re.search(r'RequiredModule="[^\x27]+\x27([^\x27]+)\x27"',match.group(0)).group(1)
    req=u.load_object(None,ref if ref.startswith('/') else ps.get_path_name()+':'+ref.split(':')[-1]);assert req
    H['set_owned'](req,'ScreenAlignment','PSA_Square')
    rows.append(path)
H['rebuild'](ps);assert u.EditorAssetLibrary.save_loaded_asset(ps,only_if_is_dirty=False)
(OUT/'Square.json').write_text(json.dumps({'status':'passed','rows':rows,'reason':'Source circle StartSize is (250,0,0); explicit square alignment gives X-based square extent rather than zero-height rectangle.'},indent=2),encoding='utf-8')
