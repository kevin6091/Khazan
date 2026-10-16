"""Resolve alpha-graph texture parameters from current material inheritance."""
from pathlib import Path
import hashlib, json, os, shutil, traceback
import unreal as u
MAIN = Path(os.environ['KZ_ALPHA_MAIN']); OUT = Path(os.environ['KZ_ALPHA_OUT'])
triage = json.loads((MAIN / 'Metadata/ParticleAlpha_20261013/MaterialTriage.json').read_text(encoding='utf-8'))
OUT.joinpath('Textures').mkdir(exist_ok=True)
R = {'status': 'running', 'rows': [], 'textures': {}, 'errors': [], 'assets_saved': False}
for row in triage['rows']:
    leaf = u.load_asset(row['path']); textures = []
    for node in row['alpha_nodes']:
        if not node.get('texture'): continue
        parameter = node.get('parameter_name')
        asset = u.MaterialEditingLibrary.get_material_instance_texture_parameter_value(leaf, parameter) if isinstance(leaf, u.MaterialInstanceConstant) and parameter else u.load_asset(node['texture'])
        if asset is None: asset = u.load_asset(node['texture'])
        if not isinstance(asset, u.Texture2D): continue
        path = asset.get_path_name(); textures.append({'node': node['name'], 'parameter': parameter, 'texture': path})
        if path in R['textures']: continue
        target = OUT / 'Textures' / (hashlib.sha256(path.encode()).hexdigest()[:12] + '_' + asset.get_name() + '.png')
        try:
            task = u.AssetExportTask(); task.object = asset; task.filename = str(target); task.automated = True
            task.prompt = False; task.replace_identical = True
            # Let FindExporter enforce SupportsObject/SupportsTexture. Forcing a
            # PNG exporter on an HDR source asserts in UE5.8 EditorFactories.cpp.
            old = MAIN / 'Metadata/ParticleAlpha_20261013/Textures01/Textures' / target.name
            if old.is_file(): shutil.copy2(old, target)
            else:
                R['pending_texture'] = path
                (OUT / 'Textures.json').write_text(json.dumps(R, indent=2), encoding='utf-8')
                if not u.Exporter.run_asset_export_task(task):
                    R['textures'][path] = {'exportable_png': False, 'compression': str(asset.get_editor_property('compression_settings')), 'reason': 'Native exporter rejected PNG for this source format; no forced export.'}
                    continue
            R['textures'][path] = {'file': str(target.relative_to(OUT)), 'srgb': asset.get_editor_property('srgb'),
                                   'compression': str(asset.get_editor_property('compression_settings'))}
        except Exception: R['errors'].append({'texture': path, 'error': traceback.format_exc()})
    R['rows'].append({'material': row['path'], 'master': row['master'], 'textures': textures, 'systems': row['systems']})
    (OUT / 'Textures.json').write_text(json.dumps(R, indent=2), encoding='utf-8')
R['status'] = 'passed' if not R['errors'] else 'partial'
(OUT / 'Textures.json').write_text(json.dumps(R, indent=2), encoding='utf-8')
print('ALPHA_TEXTURES', len(R['textures']), 'errors', len(R['errors']), flush=True)
