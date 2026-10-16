import json,pathlib,os,unreal
out=pathlib.Path(r'C:/Users/user/Desktop/GitProject/Khazan/Khazan/Metadata/CombatReaction_20261008')
plan=json.loads((out/'AnimationClassification.json').read_text(encoding='utf8'))
report={'pid':os.getpid(),'project':unreal.Paths.project_dir(),'rows':[]}
assert pathlib.Path(unreal.Paths.project_dir()).resolve()==pathlib.Path(r'C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan').resolve()
for r in plan['player']['reaction_source_clips']:
 clip=unreal.load_asset(r['current_path']);assert clip
 row={'path':r['current_path'],'class':clip.get_class().get_name()}
 for f in ['rate_scale','enable_root_motion','force_root_lock','root_motion_root_lock','use_normalized_root_motion_scale']:
  row[f]=str(clip.get_editor_property(f))
 row['root_samples']=[]
 duration=r['embedded_timing_contract']['duration']
 for at in [0,duration*.25,duration*.5,duration*.75,duration]:
  transform=unreal.AnimationLibrary.extract_root_track_transform(clip,at)
  row['root_samples'].append({'time':at,'translation':str(transform.translation),'scale':str(transform.scale3d)})
 report['rows'].append(row)
report['available_root_APIs']={k:[n for n in dir(getattr(unreal,k,None)) if 'root' in n.lower()] for k in ['AnimationLibrary','AnimationBlueprintLibrary','AnimPoseExtensions','AnimSequence']}
unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
report['dirty_packages']=[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
(out/'PlayerSourceRootReadback.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('PLAYER_REACTION_PROBE_COMPLETE',len(report['rows']))
