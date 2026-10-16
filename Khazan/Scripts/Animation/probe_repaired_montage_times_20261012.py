from pathlib import Path
import os,json,unreal as u
P=Path(os.environ['KZ_TIMING_MAIN']);O=Path(os.environ['KZ_PARRY_OUT']);plan=json.loads((P/'Metadata/AnimationTimingKnockback_20261012/Plan.json').read_text(encoding='utf-8'));out=[]
by={s['asset']:s for s in plan['sequences']}
for row in plan['montages']:
 m=u.load_asset(row['asset']);tracks=m.get_editor_property('slot_anim_tracks');ss=[]
 for tr in tracks:
  for s in tr.anim_track.anim_segments:
   a=s.anim_reference;ss.append({'asset':a.get_path_name().split('.')[0],'start':s.start_pos,'anim_start':s.anim_start_time,'anim_end':s.anim_end_time,'anim_rate':s.anim_play_rate,'loops':s.looping_count,'sequence_seconds':a.get_play_length(),'sequence_rate':a.get_editor_property('rate_scale')})
 r={'asset':row['asset'],'before_seconds':row['seconds'],'after_seconds':m.get_play_length(),'before_segments':row['segments'],'after_segments':ss,'model_fps':m.controller.get_model_interface().get_frame_rate().export_text()};out.append(r)
(O/'MontageTimes.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print('MONTAGE_TIMES',len(out))
