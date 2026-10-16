"""Append verified Art extraction results without replacing prior records."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / 'Content/_Art/Effects/Metadata/Extraction_20261006'
delivery = json.loads((META / 'DeliveryVerification.json').read_text(encoding='utf-8'))
assert delivery['status'] == 'passed'
sections = {
    'Docs/Art/DUAL_AXE_SWORD_EFFECTS_EXTRACTION_2026-10-06.md': '''
## 2026-10-06 — 최종 저장본·재생 검사와 미복원 범위

**요청 범위의 원본 추출·보존 및 지원하는 native 에셋 작성/검증을 마쳤다. 원작 효과 전부의 동일한 재생 복원은 미완료다.** `DeliveryVerification.json` passed가 이 작업의 마지막 디스크 검증이다. 과거 진행 체크포인트의 2,175개 의존성/13개 float texture 및 material stage 대기 상태는 현재 2,313개/15개 및 아래 결과로 대체한다.

- native `.uasset` **2,028개**, 예상 목록 외 파일 0. Cascade 751개, emitter 4,518개, LOD 5,608개. 모든 에셋을 새 process에서 로드하고 class·출처·원본 emitter/LOD/module 수·required material·FName·mesh material/slot 참조를 대조했다. Material 109개 기본 scalar/vector/texture와 MI 522개 parent 및 scalar/vector/texture override 배열을 원본과 대조했다. 마지막 2,028개 파일 SHA256이 audit와 동일하다.
- raw 시각 패키지 **2,313개/5,070파일**, raw binding **733개/1,466파일**, 교환 payload **600개/601파일** 모두 존재·비어 있지 않음·export 실패 0. 지속 source JSON 2,313개와 source manifest의 SHA256 일치. 원본 cooked 파일은 계속 Content 밖에 있다.
- native raw distribution table **80,874개**의 활성 entry count/stride/value 배열 범위와 source shape를 검사했다. source shape 차이 0. `EntryCount=0`인 비활성 table은 엔진 `Empty()`가 남긴 value allocation과 구분한다. `PP_Dmg_Water_Blood`의 GPU `EmitterInfo` 5필드는 Python protected getter로 읽을 수 없었으며 이 내부 compiled field까지 검증했다고 주장하지 않는다. 일반 원본 module distribution 검사와 실제 GPU 대표 재생을 구분한다.
- 색상 커브 9개의 원본 key **117개**를 native `get_unadjusted_linear_color_value()`로 평가해 해당 채널의 source 값을 비교했다. editor key/tangent는 source T3D로 이관했지만 모든 중간 시간의 곡선/원작 화면까지 전수 검증한 것은 아니다.
- `ShaderVerification.json`: 실제 RHI에서 master material **109개 모두 compile errors 0**, pixel/vertex instruction 양수. 셰이더 컴파일 통과는 제거된 원작 표현식 그래프의 복원 증명이 아니다.
- `RepresentativeEffectRendering.json`: 별도 hidden process의 unsaved blank PIE에서 **9개 대표 효과를 재생·캡처**, process exit 0/marker passed. Guard, JustGuard, Parry, `FP_BloodBleed_001`, DAS FatalbloodEX slash, PC DeepSnow normal footstep/dash/Smash, Monster L DeepSnow dash다. **45 PNG**는 `Saved/ImportReports/CombatEffects_20261006/Preview`에 있다. 마지막 Guard/JustGuard 근접 frame 2의 황금 섬광/밝은 궤적과 Parry·blood·DAS slash·눈 입자 이미지를 실제 열어 확인했다. 751개 모두의 전체 수명·충돌·소켓·원작 동일성 검사를 한 것은 아니다.

검수 카메라 거리(guard 계열 150cm, 나머지 fit 300–800cm), 1280×720, 노출 1, 30FPS cap, 캡처 frame 1/2/4/8/16은 **검수용 기술 설정**이다. 원작 gameplay 카메라·속도·전이·효과 수치로 사용하지 않는다. 최초 먼 카메라의 검은 Guard 캡처를 원작 효과가 없다는 근거로 사용하지 않는다. 해당 camera만 가까이 옮긴 마지막 이미지에서 가시성을 확인했고 에셋 크기나 원본 수치를 키우지 않았다. 이미지는 독립 SceneCapture 검수이며 실제 플레이어 전투 화면/원작 비교 사진이 아니다.

### 후속 수정의 실제 내용

가드 runtime에서 `93 into an array of size 93` assertion이 발생했다. 새 process의 native readback에서 `ColorScaleOverLife` table이 source 32×3=96개인데 93개였고, `AlphaScaleOverLife`도 source 128개 대신 127개였음을 확인했다. 소스 마지막 작은 값의 `e-05` 표기 다음 원소들이 잘렸다. 로컬 UE5.8 `CoreUObject/Private/UObject/PropertyNumeric.cpp`의 `FNumericProperty::ImportText_Internal`은 float 문자열 포인터를 숫자/부호/소수점/f까지만 전진시키며 exponent를 전진시키지 않는다. `PropertyArray.cpp`는 잘린 import에서 배열을 부분 변경한 채 반환할 수 있다.

`text()`를 유한 float의 **일반 소수 표기**로 바꾸었다. 숫자를 튜닝/반올림해서 바꾼 것이 아니라 같은 source JSON 값을 전달하는 형식의 수정이다. source 기준 337 ParticleSystem의 **750필드**, source table에서 유도한 editor distribution의 **640필드**를 다시 가져왔다. 고정 배열 색상 커브 9개와 atlas 참조도 재검사했다. `GuardDistributionReadback.json` 마지막 invalid 0 및 전체 table audit/대표 PIE 통과가 수정 결과다. Rider native dump는 throw 지점과 assertion을 확인하는 데 사용했으나 엔진 PDB가 없어 원인 frame의 명명된 변수/소스 라인을 debugger로 직접 확인하지 못했다. task-owned dump session은 종료했고 사용자 breakpoint/editor는 조작하지 않았다.

`Import_numeric.json`의 failed는 curve duplicate가 기존 경로를 unattended로 덮지 못한 **중간 단계 상태**다. 그 이전 particle/MI/mesh 저장 결과는 유지됐고, `Import_numericdata.json` completed에서 task-owned curve만 byte backup·참조 소유권 확인 후 재작성했다. scratch subobject에 강한 Python 참조를 유지해 GC에 사라지지 않게 했다. native 삭제 API가 원래 파일을 남긴 경우에도 backup과 byte가 같은 정확한 task 경로만 제거했다. 현재 모든 curve/atlas를 포함한 fresh audit가 통과했으므로 이 과거 실패를 현재 누락으로 해석하지 않는다.

초기 이름 충돌 정리 때 남아 있던 `External/BASE_Black`, `BASE_Disolve`, `BASE_SAPE` 3 texture 경로는 source별 최종 hash-suffix 목적지로 MI를 재연결한 뒤 정리했다. 기존 referencer가 있었을 때는 정리를 중단했고, 마지막에는 referencer 0·metadata 소유권·replacement·byte backup SHA256을 확인했다. `ObsoleteTextureCleanup.json` passed/3개 파일 부재, 현재 2,028개 예상 native만 존재한다. backup은 `Saved/ArtBackups/CombatEffects_20261006/BeforeDecimalRepair` 및 `ObsoleteTextureNames`. `GuardEffectiveMaterialParameters.json`에는 Guard 관련 MI 4개의 실제 effective parameter readback도 있다.

### 확정된 한계와 정확한 재개

**Niagara 21개와 MaterialFunction 264개는 원본 raw/JSON 추출 완료, native 편집/재생 복원 미완료**다. BloodSplit/Dmg_Blood_Base와 DAS dissolve/buff/afterimage가 이 목록에 있다. source-only raw를 UE5 Content에 복사하거나 이름만 같은 빈 에셋을 만들지 않았다. shader는 계속 source texture/parameter를 사용하는 recovery graph이며 distortion/refraction/dissolve/VAT와 원작 전용 renderer·3개 custom class의 runtime 특수 동작을 완전히 이식한 것이 아니다. 원작 runtime buffer writer, owner/socket parameter와 gameplay/surface routing 실행도 추가하지 않았다.

다음 작업은 Router → Art 최신 상태 → 이 마지막 절 → `DeliveryVerification`, `AssetManifest`, `SourceOnlyAssets`, 해당 binding catalog 순서로 시작한다. 완료한 전체 추출/임포트나 `numericdata`를 반복하지 않는다. native 목적지는 manifest에서 찾는다. 원작 Niagara/editor shader source를 확보할 수 있으면 21개/264개 중 실제 사용할 대상만 이어서 복원한다. 확보가 불가능하면 원작 metadata와 해당 효과의 원작 화면/동작을 근거로 좁은 범위의 native 재제작 및 차이 검증을 별도 진행한다. gameplay 연결은 현재 Source/BP/소켓/시간축·취소 수명 계약을 확인하는 별도 요청이다.

후속 수정 전 현재 대상 파일의 사용자 변경/새 SHA를 확인하고 새로운 backup을 만든다. 예전 byte backup이나 source metadata tag가 있다는 이유만으로 이후 사용자 편집을 덮지 않는다. 검사 runner는 `audit`, `compile --render`, `preview --render`; 결과 marker/report를 함께 읽는다. 이 작업의 Unreal 검사 process와 Rider dump session은 종료됐다. live reload/`DEBUG RESETLOADERS`/Save All/사용자 PIE 제어를 하지 않았다.
''',
    'Docs/Art/ART_PROJECT_STATE.md': '''
## 2026-10-06 — DualAxeSword 전투·혈흔·눈/먼지 효과 저장 결과

- 사용자 직접 요청의 Art 추출/임포트 결과는 [DUAL_AXE_SWORD_EFFECTS_EXTRACTION_2026-10-06.md](DUAL_AXE_SWORD_EFFECTS_EXTRACTION_2026-10-06.md) 마지막 절이 정본이다. 목적지 `/Game/_Art/Effects`: DAS Core/Flow/Yaksha/Enchant, Combat GuardParry/AttackContact/Blood/HitReaction/Shared, Movement 표면별 Player/Monsters, Shared dependencies, Metadata로 정리했다.
- 원본 시각 2,313 package 및 binding 733 package raw/JSON, 600 package 교환 payload 모두 실패 0. 원본 effect notify 4,146/routing entry 3,426/physical surface 계약 16개를 보존했다. native 2,028 `.uasset`(ParticleSystem 751 포함) 생성·fresh load/reference/MI override 검사·파일 SHA 검증 완료. distribution table 80,874/색상 curve key 117 검사, real RHI 109 master shader errors 0, 대표 9 효과 PIE/45 PNG 통과.
- 원본 추출/지원 native 작성은 완료했으나 **요청 전체의 원작 동일 재생 복원은 미완료**다. Niagara 21/MaterialFunction 264는 stripped editor graph 때문에 source-only. 복원용 material의 원작 distortion/dissolve/VAT/전용 renderer 동일성, runtime socket/owner/buffer writer와 전투/표면 이벤트 연결은 미구현·미검증이다. 게임 C++/BP/Notify/기존 맵이나 사용자 live editor를 이 작업에서 바꾸지 않았다.
- source manifest/catalog와 `Content/_Art/Effects/Metadata/Extraction_20261006/DeliveryVerification.json`부터 재사용한다. 전체 재추출/재임포트를 반복하지 않으며 다른 동시 작업 변경은 이 작업 결과로 합산하지 않는다.
''',
    'Docs/Art/ART_KNOWLEDGE_INDEX.md': '''
## 2026-10-06 — DAS 전투·접촉·혈흔·표면 입자 조회

- [DUAL_AXE_SWORD_EFFECTS_EXTRACTION_2026-10-06.md](DUAL_AXE_SWORD_EFFECTS_EXTRACTION_2026-10-06.md): 폴더/원본 실행 조건/복원 방법/최종 검사/21 Niagara 및 shader 미복원/재개 절차.
- 첫 metadata는 `Content/_Art/Effects/Metadata/Extraction_20261006`의 AssetManifest/DependencyEdges/AnimationEffectNotifies/EffectRoutingContracts/PhysicalSurfaceContracts/SourceOnlyAssets/Recovery/Cascade다. manifest에 source package/type/JSON SHA/native 목적지가 있다. raw는 `Saved/Extracted/CombatEffects_20261006/OriginalRaw`와 OriginalBindingRaw; 원본 cooked 파일을 UE5 asset로 읽지 않는다.
- source `PP_Damage_Spray.ItemList`의 NewDefense/NewJustGuard/EnhancedJustGuard와 `PA_Attack_Slash.NewExtraData`의 NewParrying을 구분한다. SurfaceType13 DeepSnow/10 Snow/7 Dirt 등은 source PhysicalMaterial의 field를 근거로 읽고 현재 프로젝트 surface에 자동 대응됐다고 해석하지 않는다. notify socket/scale/time/killOnEnd/attack-success/dilation은 binding raw entry를 먼저 확인한다.
- 최신 검사는 DeliveryVerification/FreshSavedAssetAudit/ShaderVerification/RepresentativeEffectRendering. source table을 통한 유도 editor curve는 80,841개이며 원작 editor key 직접 복원이 아니다. 80,874개 table shape/117 native curve key/MI 522개 source override 검사와 실제 원작 shader/전체 수명 동일성을 구분한다. protected GPU EmitterInfo 5필드는 직접 readback 미검증이다.
- Guard readback의 배열 잘림은 SETNOPEC 숫자의 exponent 처리 문제였으며 소수 문자열 변환으로 해결했다. `Import_numeric` 중간 failed는 `Import_numericdata` completed 및 마지막 전체 audit가 후속 해결한다. 이미 끝난 numericdata를 후속 사용자 수정 위에 반복하지 않는다.
''',
    'Docs/Art/ART_PIPELINE_RULES.md': '''
## 2026-10-06 — cooked VFX 이관과 텍스트 속성 검증

- 원본 cooked UE4 VFX raw/JSON은 Content 밖 archive 및 Art metadata에 보존하고 native factory/import 결과와 구분한다. editor graph가 제거된 Niagara/MaterialFunction을 빈 native system/function으로 대체해 완료로 보고하지 않는다. source CachedExpressionData는 Properties 밖에도 있으므로 root export까지 표적 확인한다.
- UE5.8 `FNumericProperty::ImportText_Internal` 기반 SET/SETNOPEC 경로에는 exponent 숫자를 전달하지 않는다. finite float를 같은 값의 일반 소수 문자열로 전달하며 값을 임의 튜닝/반올림하지 않는다. 직접 FName과 nested delimited FName의 인용 규칙도 구분한다. 객체의 exact full path·길이·작업 소유권을 검증하고 class/CDO 전역 SET을 하지 않는다.
- native distribution은 `EntryCount>0`일 때 Values 길이=EntryCount×EntryStride인지 새 process에서 읽는다. `EntryCount=0`인 비활성 table의 남은 allocation을 활성 table 오류로 오판하지 않는다. 원본 cooked table에서 editor curve를 유도한 경우 inverse time grid·단위/lock/random 조건·원작 pre-cook keys 미확보 경계를 기록한다.
- guarded fixed-array CurveLinearColor는 unsaved scratch T3D subobject를 사용한다. GC 전 모든 scratch curve에 strong Python 참조를 유지한다. 같은 작업이 만든 curve의 재작성도 byte backup/source tag/현재 referencer 소유권과 원본 atlas 재연결을 확인한다. 성공한 delete API 뒤 남은 byte 파일은 exact path/backup SHA가 확인된 task 파일만 처리한다.
- asset load/reference audit, 실제 RHI shader errors/instruction 수, 대표 standalone 재생·이미지 검수를 따로 기록한다. process exit 0만으로 caught-exception report를 통과시키지 않는다. native 생성/원본 추출/원작 그래프 및 runtime 완전 복원/사용자 gameplay 적용을 각각 구분한다. [DAS 효과 정본](DUAL_AXE_SWORD_EFFECTS_EXTRACTION_2026-10-06.md) 참조.
''',
    'Docs/Art/ART_WORK_CONTINUITY.md': '''
## 2026-10-06 — DualAxeSword 효과 최종 상태와 재개 계약

- 이전 이 작업의 진행 체크포인트를 대체하는 최신 결과는 [DUAL_AXE_SWORD_EFFECTS_EXTRACTION_2026-10-06.md](DUAL_AXE_SWORD_EFFECTS_EXTRACTION_2026-10-06.md) 마지막 절이다. 원본 시각 2,313/binding 733 raw·JSON/payload 600 추출 실패 0. native 2,028(Cascade 751) 저장·검사 완료, 기타 예상 외 native 0. 분류 루트 `/Game/_Art/Effects`, 원본은 `Saved/Extracted/CombatEffects_20261006`, 지속 metadata는 `Content/_Art/Effects/Metadata/Extraction_20261006`.
- 마지막 검증: DeliveryVerification passed/2,028 native·2,313 source SHA, FreshSavedAssetAudit passed/emitter 4,518/LOD 5,608/MI 522 source override/table 80,874/curve key 117, ShaderVerification passed/109 master errors 0, RepresentativeEffectRendering passed/9 effect/45 PNG. 실제 이미지에서 근접 Guard/JustGuard/Parry와 혈흔·DAS 궤적·눈 입자를 확인했다. 모든 751 전체 수명/게임 전투/원작 동일 검증은 아니다. GPU EmitterInfo 5 protected 필드는 getter readback 미검증.
- 실패/수정: original null Distribution의 native GPU compile crash는 source table 기반 editor distribution으로 해결. text exponent 때문에 Guard 배열 96→93/128→127로 잘린 runtime assertion은 같은 값을 일반 소수 문자열로 재전달해 해결했다. Import_numeric의 curve overwrite 실패는 Import_numericdata completed로 해결했고 source curve/atlas fresh 검사 통과. task-owned byte backup은 BeforeDecimalRepair/기존 49 particle backup에 보존했다. 초기 texture stale MI 참조 3경로는 source 목적지로 재연결 후 referencer0/backup 검증하고 삭제했다.
- **남은 목표**: source-only Niagara 21와 함수 264의 실제 editor shader/graph 복원, 원작 전용 renderer/custom module/VAT/distortion/dissolve, owner/socket parameter/runtime buffer writer, 실제 전투/표면 routing 및 원작 controlled frame 일치. 원본 source가 stripped라 이번 지원 native 이관 단계의 직접 blocker다. 추출 자체를 미완료로 되돌리거나 native 재생 전부 완료로 기록하지 않는다.
- 정확한 재개: Router → Art 최신 상태/이 정본 마지막 절 → Delivery/AssetManifest/SourceOnlyAssets/해당 binding catalog → 사용할 effect 원본만 표적 확인. 완료한 full extractor/importer/numericdata를 재실행하지 않는다. native 사용은 manifest destination, notify/guard/surface 의미는 source entry로 찾는다. 21 source-only의 원본 editor graph/HLSL 확보 또는 metadata·원작 화면 기반의 좁은 재제작/검증이 다음 복원 절차다. gameplay 연결 요청은 실제 current Source/BP·소켓·시간축/취소 계약의 별도 작업이다.
- 후속 수정 전 현재 user 변화/파일 SHA와 새 byte backup을 확인한다. 검수 runner는 UE python + `Scripts/Art/run_combat_effects_background.py audit`, `compile --render`, `preview --render`; marker/report가 통과해야 한다. 이번 task-owned Unreal process 및 native dump session은 종료했고 사용자 editor/PIE/미저장 작업은 조작하지 않았다. live reload/DEBUG RESETLOADERS/Save All을 사용하지 않는다.
'''
}
written = []
for name, section in sections.items():
    path = ROOT / name
    before = path.read_bytes()
    heading = section.strip().splitlines()[0]
    if heading in before.decode('utf-8-sig'):
        continue
    with path.open('a', encoding='utf-8', newline='\n') as stream:
        stream.write('\n' + section.strip() + '\n')
    written.append({'file': name, 'heading': heading,
                    'before_sha256': hashlib.sha256(before).hexdigest(),
                    'after_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
(META / 'DocumentationAppend.json').write_text(json.dumps({'status': 'completed', 'files': written}, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print('KZFX_ART_DOCUMENTATION_APPENDED', len(written), flush=True)
