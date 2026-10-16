"""Import only original Yetuga music; preserve every existing asset and level."""
from pathlib import Path
import hashlib
import json
import os
import traceback
import unreal as u

ROOT = Path(os.environ['KZ_AUDIO_MAIN'])
RUN = Path(os.environ['KZ_AUDIO_OUTPUT'])
TASK = ROOT / 'Metadata/YetugaBGM_20261015'
SOURCE = json.loads((TASK / 'SourceMusic.json').read_text(encoding='utf-8'))
LIB = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
BASE = '/Game/Audio/Original/Music/Yetuga/'
report = {'success': False, 'created': [], 'waves': [], 'errors': []}

def prop(obj, name, value):
    obj.set_editor_property(name, value)

def create(name, cls, factory):
    path = BASE + name
    # This first import never silently overwrites an existing user's asset.
    if LIB.does_asset_exist(path):
        raise RuntimeError('Asset already exists; inspect prior Import.json before resuming: ' + path)
    obj = TOOLS.create_asset(name, BASE.rstrip('/'), cls, factory)
    assert obj, path
    report['created'].append(path)
    return obj

def save(obj):
    assert LIB.save_loaded_asset(obj, only_if_is_dirty=False), obj.get_path_name()

try:
    sound_class = create('SC_YetugaMusic', u.SoundClass, u.SoundClassFactory())
    settings = sound_class.get_editor_property('properties')
    prop(settings, 'volume', 1.)
    prop(settings, 'pitch', 1.)
    prop(settings, 'is_music', True)
    prop(settings, 'always_play', True)
    prop(sound_class, 'properties', settings)
    LIB.set_metadata_tag(sound_class, 'OriginalMusicGain', 'Source -3.5dB baked in WAV; native unity, independent of SFX headroom')
    save(sound_class)
    waves = []
    for row in SOURCE['waves']:
        assert not LIB.does_asset_exist(row['asset']), row['asset']
        task = u.AssetImportTask()
        parent, name = row['asset'].rsplit('/', 1)
        for key, value in [('filename', row['file']), ('destination_path', parent),
                           ('destination_name', name), ('automated', True),
                           ('replace_existing', False), ('save', False), ('factory', u.SoundFactory())]:
            prop(task, key, value)
        TOOLS.import_asset_tasks([task])
        obj = LIB.load_asset(row['asset'])
        assert isinstance(obj, u.SoundWave), row['asset']
        report['created'].append(row['asset'])
        prop(obj, 'volume', 1.)
        prop(obj, 'pitch', 1.)
        prop(obj, 'sound_class_object', sound_class)
        prop(obj, 'sound_asset_compression_type', u.SoundAssetCompressionType.PCM)
        prop(obj, 'compression_quality', 100)
        prop(obj, 'loading_behavior', u.SoundWaveLoadingBehavior.LOAD_ON_DEMAND)
        LIB.set_metadata_tag(obj, 'OriginalAudioSource', SOURCE['source_media'])
        LIB.set_metadata_tag(obj, 'OriginalAudioDebugName', SOURCE['source_debug_name'])
        LIB.set_metadata_tag(obj, 'OriginalDecodedSHA256', row['sha256'])
        LIB.set_metadata_tag(obj, 'OriginalSampleRange', str(row['start_sample']) + ':' + str(row['end_sample']))
        LIB.set_metadata_tag(obj, 'AudioConversion', 'Source Wwise clip/trim/layer/gain rendered once; PCM16 stereo48kHz, no normalization')
        save(obj)
        waves.append(obj)
        report['waves'].append(dict(asset=row['asset'], duration=obj.get_editor_property('duration'),
                                    source_frames=row['frames'], source_seconds=row['seconds']))
    cue = create('SC_YetugaBattle', u.SoundCue, u.SoundCueFactoryNew())
    players = []
    for obj, row in zip(waves, SOURCE['waves']):
        node = u.new_object(u.SoundNodeWavePlayer, outer=cue)
        prop(node, 'sound_wave', obj)
        prop(node, 'looping', row['kind'] == 'Loop')
        players.append(node)
    first = u.new_object(u.SoundNodeConcatenator, outer=cue)
    prop(first, 'child_nodes', players)
    prop(first, 'input_volume', [1., 1.])
    prop(cue, 'first_node', first)
    prop(cue, 'volume_multiplier', 1.)
    prop(cue, 'pitch_multiplier', 1.)
    prop(cue, 'sound_class_object', sound_class)
    prop(cue, 'attenuation_settings', None)
    prop(cue, 'override_attenuation', False)
    prop(cue, 'concurrency_set', [])
    prop(cue, 'virtualization_mode', u.VirtualizationMode.PLAY_WHEN_SILENT)
    LIB.set_metadata_tag(cue, 'OriginalEventPackage', SOURCE['event_start'])
    LIB.set_metadata_tag(cue, 'OriginalEventID', str(SOURCE['event_id']))
    LIB.set_metadata_tag(cue, 'OriginalMusicSource', SOURCE['source_debug_name'])
    LIB.set_metadata_tag(cue, 'NativeAudioAdaptation', SOURCE['fidelity_scope'])
    LIB.set_metadata_tag(cue, 'PlaybackPolicy', 'World 2D; successful Yetuga portal arrival starts once; no death/victory/arena-exit stop')
    finalize = RUN / 'Finalize.json'
    finalize.write_text(json.dumps({'cue_paths': [BASE + 'SC_YetugaBattle']}), encoding='utf-8')
    # Existing native authoring command also persists SoundWaveAssetPtr and editor graph.
    u.SystemLibrary.execute_console_command(None, 'KZ.Audio.FinalizeCues ' + finalize.as_posix())
    save(cue)
    report['cue'] = cue.get_path_name()
    report['sound_class'] = sound_class.get_path_name()
    report['graph'] = 'Concatenator -> Intro WavePlayer, Loop WavePlayer(looping=true)'
    report['asset_sha256'] = {}
    for path in report['created']:
        file = ROOT / 'Content' / (path.removeprefix('/Game/') + '.uasset')
        report['asset_sha256'][path] = hashlib.sha256(file.read_bytes()).hexdigest()
    report['map_saved'] = False
    report['success'] = True
except Exception:
    report['errors'].append(traceback.format_exc())
    u.log_error(report['errors'][-1])
finally:
    (RUN / 'Import.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
if not report['success']:
    raise RuntimeError('Yetuga BGM import failed; inspect Import.json')
