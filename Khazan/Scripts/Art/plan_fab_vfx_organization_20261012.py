"""Flatten seven packs into one visible VFX root; only collision names change."""
from pathlib import Path
from collections import Counter
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / 'Metadata/FabVFX_20261012/Completion'


def category(row):
    cls = row['class']
    if cls == 'NiagaraSystem':
        return ''
    if cls in ('Material', 'MaterialInstanceConstant', 'MaterialFunction', 'MaterialLayer', 'MaterialLayerBlend'):
        return 'Materials'
    if cls.startswith('Texture') or cls in ('VectorFieldStatic', 'VectorFieldAnimated'):
        return 'Textures'
    if cls in ('StaticMesh', 'SkeletalMesh', 'Skeleton', 'PhysicsAsset', 'SkeletalMeshLODSettings'):
        return 'Meshes'
    if cls in ('NiagaraEmitter', 'NiagaraScript'):
        return 'Modules'
    if cls.startswith('Curve'):
        return 'Curves'
    if cls in ('UserDefinedEnum', 'UserDefinedStruct'):
        return 'Blueprints'
    if cls == 'Blueprint':
        return 'Blueprints'
    return 'Demo'


def main():
    registry = json.loads((META / 'InputRegistry.json').read_text())
    folders = json.loads((META / 'FolderMap.json').read_text())
    rows = []
    for item in registry['assets']:
        if item['package'].startswith(('/Game/__ExternalActors__/', '/Game/__ExternalObjects__/')):
            continue
        source_root = item['package'].split('/')[2]
        assert source_root in folders, ('Unclassified dependency root', source_root)
        target_folder = '/Game/VFX/' + folders[source_root]
        cat = category(item)
        if cat:
            target_folder += '/' + cat
        rows.append(dict(item, target_folder=target_folder, new_name=item['name'], new_package=target_folder + '/' + item['name']))
    counts = Counter(r['new_package'].lower() for r in rows)
    for row in rows:
        if counts[row['new_package'].lower()] > 1:
            # Keep the vendor basename; a brief source-family suffix disambiguates
            # identically named assets without creating more folder levels.
            parts = row['package'].split('/')[3:-1]
            ignored = {'vfx','niagara','niagarasystems','system','systems','materials','material','textures','texture','mi','demo','demomap','mesh','meshes','map','maps','blueprint','blueprints','allshadesofvfxbundle'}
            family = next((p for p in parts if p.lower() not in ignored), 'Variant')
            family = ''.join(c for c in family if c.isalnum() or c == '_')[:32]
            row['new_name'] = row['name'] + '_' + family
            row['new_package'] = row['target_folder'] + '/' + row['new_name']
    counts = Counter(r['new_package'].lower() for r in rows)
    for row in rows:
        if counts[row['new_package'].lower()] > 1:
            row['new_name'] += '_' + hashlib.sha256(row['package'].encode()).hexdigest()[:6]
            row['new_package'] = row['target_folder'] + '/' + row['new_name']
        row['new_object_path'] = row['new_package'] + '.' + row['new_name']
        assert len(row['new_package'].split('/')) <= 6, row
        assert not any((ROOT / 'Content' / (row['new_package'].removeprefix('/Game/') + ext)).exists() for ext in ('.uasset', '.umap')), row
    assert len({r['new_package'].lower() for r in rows}) == len(rows)
    (META / 'RenamePlan.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    (META / 'LayoutSummary.json').write_text(json.dumps({'root': '/Game/VFX', 'pack_folders': folders, 'public_assets': len(rows), 'niagara_systems': registry['classes']['NiagaraSystem'], 'max_visible_folder_depth_below_Content': 3, 'renamed_for_collisions': sum(r['new_name'] != r['name'] for r in rows), 'categories': dict(Counter(category(r) or 'Effect at pack root' for r in rows))}, indent=2), encoding='utf-8')
    print(json.dumps({'public_assets': len(rows), 'niagara_systems': registry['classes']['NiagaraSystem'], 'renamed_for_collisions': sum(r['new_name'] != r['name'] for r in rows), 'pack_folders': folders}), flush=True)


if __name__ == '__main__':
    main()
