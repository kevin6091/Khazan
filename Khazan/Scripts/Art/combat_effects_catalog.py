"""Build reusable source-field catalogs; no gameplay assets are edited."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'Saved/Extracted/CombatEffects_20261006'
META = ROOT / 'Content/_Art/Effects/Metadata/Extraction_20261006'
ROWS = json.loads((META / 'AssetManifest.json').read_text(encoding='utf-8'))
LOOKUP = {r['source_package']: r for r in ROWS}


def write(name, value):
    (META / (name + '.json')).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def refs(value, field=''):
    if isinstance(value, dict):
        if 'ObjectPath' in value:
            yield field, value
        else:
            for key, item in value.items():
                yield from refs(item, field + '.' + key)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            yield from refs(item, field + '[' + str(i) + ']')


notifications, routing, surfaces, provenance = [], [], [], []
for path in (BASE / 'BindingSource').rglob('*.json'):
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(data, list) or not data or 'Type' not in data[0]:
        continue
    root = next((o for o in data if not o.get('Outer')), data[-1])
    package = root.get('Package', str(path.relative_to(BASE / 'BindingSource')).replace('\\', '/').removesuffix('.json'))
    props = root.get('Properties', {})
    stamp = hashlib.sha256(path.read_bytes()).hexdigest()
    provenance.append({'source_package': package, 'type': root['Type'], 'sha256': stamp})
    if root['Type'] == 'PhysicalMaterial':
        surfaces.append({'source_package': package, 'property': 'SurfaceType', 'raw_value': props.get('SurfaceType', 'not_serialized'), 'properties': props})
    if '/PhysicsData/' in package:
        for field in ('ItemList', 'NewExtraData', 'EffectList'):
            for i, entry in enumerate(props.get(field, [])):
                pointers = []
                for ref_field, pointer in refs(entry):
                    target = pointer['ObjectPath'].split('.')[0]
                    row = LOOKUP.get(target)
                    pointers.append({'field': ref_field, 'source_reference': pointer,
                                     'native_destination': row['destination'] if row else None})
                routing.append({'source_package': package, 'source_sha256': stamp,
                                'field': field + '[' + str(i) + ']', 'raw_entry': entry, 'references': pointers})
    if root['Type'] in ('AnimComposite', 'AnimMontage', 'AnimSequence') and '/DualAxeSword/' in package:
        for i, event in enumerate(props.get('Notifies', [])):
            pointer = event.get('NotifyStateClass') or event.get('Notify')
            if not pointer or pointer['ObjectPath'].split('.')[0] != package:
                continue
            notify = data[int(pointer['ObjectPath'].rsplit('.', 1)[1])]
            if not any(t in notify['Type'].lower() for t in ('particle', 'effect', 'trail', 'decal')):
                continue
            notifications.append({'source_package': package, 'source_sha256': stamp,
                'field': 'Properties.Notifies[' + str(i) + ']', 'event': event,
                'notify_object': notify['Name'], 'notify_type': notify['Type'],
                'notify_properties': notify.get('Properties', {}),
                'time_contract': 'Original LinkValue/Duration/EndLink preserved; DilationCurve is in the full source JSON. No timing transplant performed.'})
write('AnimationEffectNotifies', notifications)
write('PhysicalSurfaceContracts', surfaces)
write('EffectRoutingContracts', routing)
write('BindingSourceManifest', provenance)
shutil.copytree(BASE / 'BindingSource', META / 'Bindings/Source', dirs_exist_ok=True)
unavailable = []
for row in ROWS:
    if row['source_type'] not in ('NiagaraSystem', 'MaterialFunction'):
        continue
    data = json.loads((ROOT / row['source_json']).read_text(encoding='utf-8-sig'))
    unavailable.append({**row,
        'status': 'source_json_and_original_raw_preserved; no_empty_native_asset_created',
        'reason': 'UE4 cooked Niagara editor graph/GPU HLSL source unavailable; UE5.8 compiled VM/schema is incompatible.' if row['source_type'] == 'NiagaraSystem' else 'Cooked MaterialFunction expression graph stripped; native recovery masters use independent explicit shader graphs.',
        'export_types': dict(Counter(o['Type'] for o in data)),
        'original_raw_base': str((BASE / 'OriginalRaw' / row['source_package']).relative_to(ROOT)).replace('\\', '/')})
write('SourceOnlyAssets', unavailable)
write('CatalogSummary', {'source_packages': len(ROWS), 'particle_systems': sum(r['source_type'] == 'ParticleSystem' for r in ROWS),
    'niagara_source_only': sum(r['source_type'] == 'NiagaraSystem' for r in ROWS),
    'binding_source_packages': len(provenance), 'animation_effect_events': len(notifications),
    'routing_entries': len(routing), 'physical_materials': len(surfaces),
    'classification_contract': 'Folder labels are authoring categories. Event claims come from exact original fields, not names alone.'})
print('Binding catalog:', len(provenance), 'sources,', len(notifications), 'effect notifies,', len(routing), 'routing entries', flush=True)

# Fix this task's initial checkpoint, whose PowerShell pipe replaced Korean text
# with question marks. Earlier user/other-task records are preserved byte-for-byte.
p = ROOT / 'Docs/Art/ART_WORK_CONTINUITY.md'
content = p.read_text(encoding='utf-8')
marker = '\n\n## 2026-10-06 DualAxeSword ????/??'
if marker in content:
    start = content.index(marker)
    end = content.find('\n## ', start + len(marker))
    if end < 0:
        end = len(content)
    corrected = '''

## 2026-10-06 DualAxeSword 전투·눈/먼지 효과 추출/임포트 — 진행 체크포인트

- 사용자 직접 요청에 따라 FModel 원본에서 휘두름/명중/가드/직전 가드/패링/피격/혈흔과 Player·Monster 달리기/대시/무기 접촉의 눈·먼지를 추출하여 `/Game/_Art/Effects`에 작성 중이다. 작업 범위는 Art assets/scripts/metadata이며 게임 Source/BP/기존 맵과 라이브 editor는 수정하지 않는다. 다른 동시 작업 변경을 보존한다.
- 재개 기준: `Content/_Art/Effects/Metadata/Extraction_20261006/AssetManifest.json`, Source, Bindings/Source, DependencyEdges 및 `Saved/Extracted/CombatEffects_20261006/RootRequests.json`. 현재 Cascade 751/Niagara 21, 별도 decal material/curve 42 roots다. 최종 native 수량/재생 검증은 후속 audit로 확정한다.
- 원본 JSON/payload 추출 실패 0. Vector fields 17개는 source RGB/bounds/dimensions를 검증했다. FloatRGBA textures 13개는 원본 inline bulk의 alpha 포함 half bits를 EXR로 보존하고 RGBA 재조립 SHA256 일치를 확인했다. PrecisionTextureExtraction 참조.
- native textures/vector fields/curves/MPC가 저장됐다. Material v2와 mesh/particle stage를 진행한다. CurveLinearColor fixed arrays는 hidden process의 unsaved T3D scratch actor에서 원본 tangent/key를 가져와 curve만 duplicate했다. scratch map/actor는 저장하지 않았다. native material graph는 원본 그래프의 완전 복원이 아니다.
- 실패/해결: ActorX None material-token crash는 작업용 PSKX token만 바꾸어 회피했다(geometry 동일). destination의 double slash를 정규화했다. HDR 자동 cube 오분류는 process-only TextureImporter INI override 및 exact EXR로 교정했다. 다른 작업 Build.bat lock은 child process의 UE_SKIP_UBT_SDK_SETUP=1로 우회했으며 다른 build/editor를 중지하지 않았다.
- 남은 절차: runner import materials → meshes → particles → fresh saved-asset audit → RHI shader/대표 효과 재생 검수. Niagara 21개는 cooked editor graph/GPU HLSL source가 없으므로 native 재생 복원을 완료로 기록하지 않는다. SourceOnlyAssets의 원본 raw/JSON은 모두 보존한다.
- 정확한 재개: Router → Art 최신 상태/이 절 → importer/manifest/report. Python은 UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe. runner는 hidden subprocess/nullrhi, 검수만 --render. 사용자 editor/PIE를 임의 reload/종료하거나 DEBUG RESETLOADERS를 호출하지 않는다.
'''
    p.write_text(content[:start] + corrected + content[end:], encoding='utf-8')
