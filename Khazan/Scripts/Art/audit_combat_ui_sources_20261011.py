"""Audit only the requested combat HUD widgets extracted by the existing FModel provider."""
from pathlib import Path
import hashlib
import json
import re

MAIN = Path(__file__).resolve().parents[2]
OUT = MAIN / 'Metadata/CombatUI_20261011'
SOURCE = OUT / 'SourceWidgets01/BBQ/Content/_Kazan_/UserInterface/UIWidget/GameHud'
REQUESTED = ['W_Hud_LockOn', 'W_Hp_PC', 'W_Hp_Monster', 'W_Stamina',
             'W_GaugePackage_PC', 'W_GaugePackage_Monster', 'W_Boss', 'W_OverheadGauge']


def walk(value, path=''):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, path + '/' + key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, path + '/' + str(index))
    else:
        yield path, value


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    report = {'scope': 'Requested combat HUD; source metadata, not original native UI code',
              'source_files': [], 'widgets': [], 'resource_packages': [], 'native_timing_fields': []}
    resources = set()
    for file in sorted(SOURCE.rglob('*.json')):
        objects = json.loads(file.read_text(encoding='utf-8-sig'))
        report['source_files'].append({'path': str(file), 'sha256': sha(file), 'exports': len(objects)})
        chosen = file.stem in REQUESTED
        for index, obj in enumerate(objects):
            props = obj.get('Properties', {})
            kind, name = obj.get('Type', ''), obj.get('Name', '')
            if chosen or file.stem == 'WBP_BattleHUD' and kind == 'CanvasPanelSlot':
                if kind != 'Function' and kind != 'MovieSceneCompiledData':
                    report['widgets'].append({'file': str(file), 'export_index': index,
                                              'type': kind, 'name': name, 'properties': props})
            if chosen:
                for field, value in walk(props):
                    if field.endswith('/ObjectPath') and isinstance(value, str) and 'UserInterface/UITexture/' in value:
                        resources.add(re.sub(r'\.\d+$', '', value))
                    if isinstance(value, (float, int)) and re.search(r'(?i)(interpolation|smooth|duration|speed)', field):
                        report['native_timing_fields'].append({'file': str(file), 'export_index': index,
                                                              'name': name, 'field': 'Properties' + field, 'raw': value,
                                                              'status': 'Direct serialized value; native interpretation requires separate evidence'})
    report['resource_packages'] = sorted(resources)
    (OUT / 'SourceWidgetAudit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (OUT / 'SourceResourcePackages01.json').write_text(json.dumps(sorted(resources), indent=2) + '\n', encoding='utf-8')
    concise = []
    for obj in report['widgets']:
        kind, name, props = obj['type'], obj['name'], obj['properties']
        if Path(obj['file']).stem == 'W_Hud_LockOn' and kind in ['xxImage', 'xxSizeBox', 'xxAnimatedSwitcher']:
            brush = props.get('Brush', {})
            concise.append({'name': name, 'kind': kind, 'resource': brush.get('ResourceObject'),
                            'size': brush.get('ImageSize'), 'color': brush.get('TintColor'),
                            'width': props.get('WidthOverride'), 'height': props.get('HeightOverride'),
                            'transition': props.get('TransitionDuration')})
    print(json.dumps({'source_files': len(report['source_files']), 'resources': len(resources),
                      'timing': report['native_timing_fields'], 'lockon': concise}, ensure_ascii=True))


if __name__ == '__main__':
    main()
