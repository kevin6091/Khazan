"""Read-only project animation rates and composite dependency audit."""
from pathlib import Path
from fractions import Fraction
from collections import Counter
import json,os,traceback,unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=Path(os.environ['KZ_PARRY_OUT'])
report={'success':False,'project':str(ROOT),'asset_saves':0,'sequences':[],'composites':[]}
def pkg(o):return o.get_path_name().split('.')[0] if o else None
def prop(o,n):
    try:return o.get_editor_property(n)
    except Exception:return None
try:
    reg=u.AssetRegistryHelpers.get_asset_registry();reg.search_all_assets(True)
    rows=reg.get_assets_by_path('/Game',recursive=True,include_only_on_disk_assets=True)
    selected=sorted([(str(x.package_name),str(x.asset_class_path.asset_name)) for x in rows if str(x.asset_class_path.asset_name) in ['AnimSequence','AnimMontage','AnimComposite']])
    rates={}
    for path,kind in selected:
        if kind!='AnimSequence':continue
        a=u.load_asset(path);assert a,path
        model=a.controller.get_model_interface();r=model.get_frame_rate();fps=[r.numerator,r.denominator]
        sampling=a.get_editor_property('platform_target_frame_rate').get_editor_property('default')
        sampling_fps=[sampling.numerator,sampling.denominator]
        rates[path]=Fraction(*sampling_fps)
        item={'asset':path,'fps':fps,'sampling_fps':sampling_fps,'frames':int(model.get_number_of_frames()),'seconds':a.get_play_length(),
              'rate_scale':a.get_editor_property('rate_scale'),'skeleton':pkg(a.get_editor_property('skeleton')),
              'tracks':len(model.get_bone_track_names()),'float_curves':model.get_number_of_float_curves(),
              'transform_curves':model.get_number_of_transform_curves(),
              'notifies':len(u.AnimationLibrary.get_animation_notify_events(a)),
              'metadata':{str(k):str(v) for k,v in u.EditorAssetLibrary.get_metadata_tag_values(a).items()}}
        report['sequences'].append(item)
        if len(report['sequences'])%100==0:print('FPS_AUDIT_SEQUENCE_COUNT',len(report['sequences']),flush=True)
    comp=[]
    for path,kind in selected:
        if kind=='AnimSequence':continue
        a=u.load_asset(path);assert a,path
        if kind=='AnimMontage':tracks=[x.anim_track for x in a.get_editor_property('slot_anim_tracks')]
        else:tracks=[a.get_editor_property('animation_track')]
        segs=[]
        for track in tracks:
            for s in track.anim_segments:
                segs.append({'asset':pkg(s.anim_reference),'start':s.start_pos,'anim_start':s.anim_start_time,
                             'anim_end':s.anim_end_time,'anim_rate':s.anim_play_rate,'loops':s.looping_count})
        comp.append({'asset':path,'class':kind,'seconds':a.get_play_length(),'rate_scale':a.get_editor_property('rate_scale'),
                     'segments':segs,'model_fps':a.controller.get_model_interface().get_frame_rate().export_text()})
    def common(path,seen=None):
        if path in rates:return rates[path]
        seen=seen or set()
        if path in seen:return Fraction(100000,1)
        seen.add(path);c=next((c for c in comp if c['asset']==path),None)
        if not c:return Fraction(100000,1)
        rs=[common(s['asset'],set(seen)) for s in c['segments'] if s['asset']]
        target=rs[0] if rs else Fraction(30,1)
        for r in rs[1:]:
            if (target/r).denominator==1:target=r
            elif target!=r and (r/target).denominator!=1:return Fraction(100000,1)
        rates[path]=target;return target
    for c in comp:
        r=common(c['asset']);c['engine_sampling_fps']=[r.numerator,r.denominator]
        c['display_frames']=round(c['seconds']*float(r));report['composites'].append(c)
    report['summary']={'sequences':len(report['sequences']),'composites':len(comp),
      'fractional_sequences':sum(Fraction(*s['fps']).denominator!=1 for s in report['sequences']),
      'fallback_composites':sum(c['engine_sampling_fps']==[100000,1] for c in comp),
      'fps_distribution':dict(Counter(str(s['fps']) for s in report['sequences']))}
    report['success']=True
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'Inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('FPS_AUDIT',report.get('summary',{}),report.get('error',''),flush=True)
if not report['success']:raise RuntimeError('FPS audit failed')
