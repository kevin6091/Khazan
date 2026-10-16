"""Read-only current animation/import inventory, using a fresh hidden editor."""
from pathlib import Path
import json
import os
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
assert ROOT == Path(os.environ['KZ_AUDIO_MAIN']).resolve()
OUT = Path(os.environ['KZ_AUDIO_OUTPUT'])
registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
rows = []
try:
    for folder in ('/Game/_Art/Player/Animation/InGame', '/Game/Monsters'):
        for info in registry.get_assets_by_path(folder, recursive=True):
            typ = str(info.asset_class_path.asset_name)
            if typ not in ('AnimSequence', 'AnimMontage'):
                continue
            obj = info.get_asset()
            row = {'asset': obj.get_path_name(), 'type': typ,
                   'notifies': [{'text': n.export_text()} for n in unreal.AnimationLibrary.get_animation_notify_events(obj)],
                   'metadata': {str(k): str(v) for k, v in unreal.EditorAssetLibrary.get_metadata_tag_values(obj).items()}}
            if typ == 'AnimSequence':
                row['seconds'] = obj.get_play_length()
                row['rate_scale'] = obj.get_editor_property('rate_scale')
                model=obj.controller.get_model_interface()
                row['model_frames']=model.get_number_of_frames()
                frame_rate=model.get_frame_rate()
                row['model_fps']=[frame_rate.numerator,frame_rate.denominator]
                data = obj.get_editor_property('asset_import_data')
                row['import_source'] = data.get_first_filename() if data else None
            else:
                row['slots'] = [s.export_text() for s in obj.get_editor_property('slot_anim_tracks')]
            rows.append(row)
    result = {'success': True, 'assets': rows, 'count': len(rows), 'saves': 0}
except Exception:
    result = {'success': False, 'error': traceback.format_exc(), 'assets': rows, 'saves': 0}
(OUT / 'CurrentAssets.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
assert result['success'], result.get('error')
