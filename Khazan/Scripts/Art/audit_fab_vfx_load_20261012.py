"""Load all migrated public assets in UE; preserve vendor package bytes."""
from pathlib import Path
from collections import Counter
import json
import time
import traceback
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
META = MAIN / 'Metadata/FabVFX_20261012'
PROJECT = Path(unreal.Paths.project_dir()).resolve()
LABEL = 'Main' if PROJECT == MAIN else 'Stage'
OUT = META / (LABEL + 'Load.json')
ROWS = json.loads((META / 'StageDependencies.json').read_text(encoding='utf-8'))['assets']
report = {'status': 'running', 'project': str(PROJECT), 'engine_version': unreal.SystemLibrary.get_engine_version(), 'assets': [], 'errors': [], 'asset_saves': 0, 'scope': 'Native asset load and hard reference validation; no claim of gameplay integration or final visual quality.'}
start = time.monotonic()
try:
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.search_all_assets(synchronous_search=True)
    classes = Counter()
    held = []
    for index, row in enumerate(ROWS):
        item = {'package': row['package'], 'class': row['class']}
        # WP actor/object packages are loaded by their owning demo world. Their
        # registry entries and bytes are verified separately from public assets.
        if row['package'].startswith(('/Game/__ExternalActors__/', '/Game/__ExternalObjects__/')):
            item['status'] = 'external_package_registered'
            report['assets'].append(item)
            continue
        try:
            asset = unreal.load_asset(row['object_path'])
            if asset is None:
                raise RuntimeError('Native load returned None')
            item['status'] = 'loaded'
            item['actual_class'] = asset.get_class().get_name()
            if item['actual_class'] != row['class']:
                raise RuntimeError('Unexpected asset class: ' + item['actual_class'])
            classes[item['actual_class']] += 1
            if item['actual_class'] == 'NiagaraSystem':
                held.append(asset)
        except Exception:
            item['status'] = 'failed'
            item['error'] = traceback.format_exc()
            report['errors'].append(item)
        report['assets'].append(item)
        if index % 100 == 0:
            report.update(processed=index + 1, classes=dict(classes), elapsed_seconds=round(time.monotonic()-start, 2))
            OUT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
            print('FAB_VFX_LOAD ' + json.dumps({'processed': index+1, 'total': len(ROWS), 'errors': len(report['errors'])}), flush=True)
    report.update(status='failed' if report['errors'] else 'passed', processed=len(ROWS), classes=dict(classes), elapsed_seconds=round(time.monotonic()-start, 2))
except Exception:
    report['status'] = 'failed'
    report['errors'].append({'error': traceback.format_exc()})
OUT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('FAB_VFX_LOAD_FINAL ' + json.dumps({k: v for k, v in report.items() if k != 'assets'}), flush=True)
