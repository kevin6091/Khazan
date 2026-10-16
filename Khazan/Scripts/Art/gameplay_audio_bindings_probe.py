"""Read only current combo windows, map fire anchors and native authoring APIs."""
from pathlib import Path
import json
import os
import traceback
import unreal as u
OUT=Path(os.environ['KZ_AUDIO_OUTPUT']);report={'success':False,'combos':[],'fire':[],'api':{}}
try:
    registry=u.AssetRegistryHelpers.get_asset_registry();registry.search_all_assets(True)
    assets=registry.get_assets_by_class(u.TopLevelAssetPath('/Script/Khazan','KZComboDefinitionData'),True)
    for ad in assets:
        obj=ad.get_asset();nodes=obj.get_editor_property('nodes');objects=obj.get_editor_property('pattern_objects')
        report['combos'].append({'asset':str(ad.package_name),'nodes':[{'id':str(n.get_editor_property('node_id')),
            'montage':n.get_editor_property('montage').get_path_name() if n.get_editor_property('montage') else None,
            'windows':len(n.get_editor_property('attack_windows'))} for n in nodes],
            'objects':[o.export_text() for o in objects]})
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem);assert editor.load_level('/Game/Maps/L_HeinMach_Environment')
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors();report['actor_count']=len(actors)
    for a in actors:
        label=a.get_actor_label();tags=[str(t) for t in a.get_editor_property('tags')]
        if any(s in (label+' '+' '.join(tags)).lower() for s in ('torch','brazier','campfire','fire_','bonfire','bongfire')):
            report['fire'].append({'path':a.get_path_name(),'label':label,'tags':tags,'location':a.get_actor_location().to_tuple(),'class':a.get_class().get_name()})
    for cls in ('AudioVolume','ReverbEffect','RuntimeFloatCurve','SoundCue','AmbientSound'):
        typ=getattr(u,cls,None);report['api'][cls]=[n for n in dir(typ) if any(s in n for s in ('reverb','priority','settings','attenuation','curve','first','audio_component','volume'))] if typ else []
    vol=u.get_editor_subsystem(u.EditorActorSubsystem).spawn_actor_from_class(u.AudioVolume,u.Vector())
    report['volume_defaults']={k:str(vol.get_editor_property(k)) for k in ('settings','priority','enabled')}
    u.get_editor_subsystem(u.EditorActorSubsystem).destroy_actor(vol)
    rev=u.new_object(u.ReverbEffect)
    report['reverb_properties']=[s for s in dir(rev) if not s.startswith('_')]
    report['success']=True
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'Bindings.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if not report['success']:raise RuntimeError('Audio current binding probe failed')
