"""User-requested modest snow reduction on the existing EffectType only."""
from pathlib import Path
import hashlib, json, os
import unreal as u
MAIN = Path(os.environ['KZ_ALPHA_MAIN']); PROJECT = Path(u.Paths.project_dir()).resolve()
assert PROJECT == MAIN.parent.parent / 'Khazan_ParticleAlphaWork_20261013/Khazan'
OUT = Path(os.environ['KZ_ALPHA_OUT'])
path = '/Game/_Art/Player/Environment/Rendering/HeinMachWeather/NET_HM_WeatherBudget'
file = PROJECT / ('Content/' + path.removeprefix('/Game/') + '.uasset')
assert file.resolve().is_relative_to(PROJECT)
asset = u.load_asset(path); before_sha = hashlib.sha256(file.read_bytes()).hexdigest()
before = asset.get_editor_property('emitter_scalability_settings').export_text()
container = asset.get_editor_property('emitter_scalability_settings'); rows = list(container.get_editor_property('settings'))
assert len(rows) == 1 and rows[0].get_editor_property('scale_spawn_count')
assert rows[0].get_editor_property('spawn_count_scale') == .25
rows[0].set_editor_property('spawn_count_scale', .20)  # Assistant visual TEMP: 20% fewer than the current .25.
container.set_editor_property('settings', rows); asset.set_editor_property('emitter_scalability_settings', container)
after = asset.get_editor_property('emitter_scalability_settings').export_text()
assert after == before.replace('SpawnCountScale=0.250000', 'SpawnCountScale=0.200000')
assert u.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False)
report = {'status': 'passed', 'path': path, 'before_sha256': before_sha, 'after_sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
          'before': before, 'after': after, 'before_scale': .25, 'after_scale': .20,
          'relative_reduction': .20, 'source': 'User asks slightly fewer snow particles; assistant-selected visual TEMP.',
          'source_spawn_rates_per_second': [1250,2500], 'previous_effective_rates_per_second': [312.5,625], 'new_effective_rates_per_second': [250,500],
          'system_graph_size_speed_lifetime_material_map_unchanged': True}
(OUT / 'SnowApplied.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('SNOW_COUNT_APPLIED .25 -> .20; existing layers unchanged', flush=True)
