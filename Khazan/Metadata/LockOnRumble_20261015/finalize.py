from pathlib import Path
import datetime
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
ui = load(OUT / 'PIE01/Driver.json')
giant = load(OUT / 'PIE02_Giant/Driver.json')
shipping = load(ROOT / 'Metadata/Release_20261015/Package06_LockOnRumble/Exit.json')
package = load(OUT / 'PackageReadback.json')
smoke = load(OUT / 'Smoke01/Result.json')
changes = load(OUT / 'ChangedFiles.json')
assert ui['tests'][0]['passed'] and giant['status'] == 'passed'
assert shipping['exit_code'] == 0 and smoke['status'] == 'StartupObserved'
for entry in changes:
    assert sha(ROOT / entry['path']) == entry['current_sha256'], entry['path']
assert sha(ROOT / 'Content/Maps/L_HeinMach_Environment.umap') == '7b072b9bfd8c051701fa8190fb794422e33c4c1bd16c62a2370ce1831471c728'
receipt = dict(status='Complete', utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    runtime_files_changed=5, new_runtime_files=0, changed_files=changes,
    release_folder='C:/Users/user/Desktop/Khazan_Release_20261015/Windows',
    launch_executable='C:/Users/user/Desktop/Khazan_Release_20261015/Windows/Khazan.exe',
    editor_builds=['EditorBuild01.log', 'EditorBuild02.log', 'EditorBuild03.log'],
    combat_ui_test=ui['tests'][0], combat_ui_module_sha256=ui['module_sha256'],
    giant_test=giant['tests'][0], giant_module_sha256=giant['module_sha256'],
    module_difference='Only DEV giant-test death-source assertion changed after the UI pass; runtime/config unchanged.',
    package_run='Metadata/Release_20261015/Package06_LockOnRumble', package_exit=shipping,
    shipping_build_seconds=51.47, cook_seconds=91.98, cook_packages=8590, cook_errors=0, cook_warnings=6,
    package_readback=package, smoke=smoke,
    semantics=['ForceFeedbackScale=2 via existing engine config; motor outputs saturate at 1.',
               'HP zero synchronously clears target, delegate and movement constraint; dead targets rejected.',
               'Confirmed Yetuga capture unlocks the local victim; cleanup re-locks the living captor for the same controller/pawn.',
               'Capture failure does not schedule a re-lock; dead/destroyed/changed-owner participants cannot re-lock.'],
    preserved_map_sha256=sha(ROOT / 'Content/Maps/L_HeinMach_Environment.umap'),
    failed_attempts=['PIE01 GiantFall: broad root-motion assertion included the new death montage; corrected DEV assertion passed in PIE02_Giant.',
                     'IoStoreList_FirstAttempt.log: verification CLI required the IoStore subcommand; corrected readback passed.'],
    limitations=['Physical gamepad sensation/output was not measured.',
                 'Shipping startup was observed offscreen with sound disabled; full packaged combat/FPS/audio was not exercised.',
                 'Existing cook warnings: Lumen atlas priority, empty decorative SM_PortalPlane convex geometry, default GameplayCue search path.'],
    required_remaining=[])
(OUT / 'FinalVerification.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')

marker = '<!-- LockOnRumble_20261015_complete -->'
common = '''

## 2026-10-15 — 진동 2배·HP0/Yetuga 잡기 LockOn·HeinMach 재패키징 완료

사용자 직접 요청을 기존 runtime5/Config1/DEV2의 작은 변경으로 완료했다. 신규 runtime 파일/class0, BP/애니메이션/맵 저장0이다. 진동은 기존 엔진 config `/Script/Engine.PlayerController.ForceFeedbackScale=2.0`을 사용하며 생성자 변경은 남기지 않았다. 배율2는 사용자 지정, 최종0..1 상한은 엔진 장치 출력 범위다. 기존 pulse duration/몬스터 거리 감쇠는 그대로다.

LockOn은 대상 ASC HP<=0 callback에서 즉시 해제하고 살아 있는 대상만 선택/유지한다. Yetuga의 승인된 잡기 성공 시 피해 Player의 잠금을 풀고, 기존 잡기 cleanup 후 양쪽 생존·동일 Controller/Pawn이면 동일 Yetuga에 자동 재잠금한다. 잡기 중 신규 잠금, 죽은 target 및 소멸/소유권 변경 후 재잠금은 거절한다. ASC/Ability 상태와 이동 제약의 기존 작성자를 유지하며 delegate/constraint/controller receipt는 각 소유자가 정리한다.

EditorBuild01~03 Succeeded, 실제 RHI CombatUI.PIE 및 GiantFall.PIE(14패턴/기존 낙하 포함) Success. UI 검증 후 변경은 DEV death assertion뿐이며 제품 runtime/config는 동일하다. 초기 lethal fixture가 사망 montage까지 포함한 HasRootMotionSources 검사에서 실패한 기록은 보존하고 자기 OriginalPatternMoveTo 제거 검사로 보정해 재통과했다. 정확한 각 DLL/Source hash와 범위는 `Metadata/LockOnRumble_20261015/FinalVerification.json` 및 Changes.patch/ChangedFiles.json/PIE01/PIE02_Giant를 따른다.

Package06_LockOnRumble의 새 Shipping compile51.47초, cook8590/91.98초/0error·6warning, UATexit0(276.15초)으로 완료했다. 최종 container의 게임 map은 HeinMach 하나, 설정은 진동2/Epic11그룹3/해상도100%, packaged Shipping exe는 현재 build SHA와 동일하다. 배포 폴더 `C:/Users/user/Desktop/Khazan_Release_20261015/Windows`, 실행 `Khazan.exe`, 전체41파일/2,410,106,779bytes다. VC x64 prerequisite와 실행안내 포함, 배포는 Windows 폴더 전체 단위다. 기존 map SHA7b072b9bfd8c051701fa8190fb794422e33c4c1bd16c62a2370ce1831471c728 보존.

소유 Shipping 프로세스의 별도 UserDir/offscreen/nosound 90초 생존과 새 crash0을 확인한 뒤 해당 프로세스만 종료했다. 자연 종료/전체 패키지 전투·FPS·오디오·실물 패드 체감은 검증한 것으로 확대하지 않는다. 기존6 cook 경고는 이전 release와 같은 Lumen priority/장식 PortalPlane convex/GameplayCue 검색 경로다. 필수 잔여0이며 이후 재개는 위 FinalVerification → 새 요청 범위의 현재 Source/Config부터 한다. 이전 배포 완료본을 현재 바이너리로 오인하거나 과거 package/asset/DLL 전체를 복원하지 않는다.

''' + marker + '\n'
for name in ['ENGINEERING_PROJECT_STATE.md', 'ENGINEERING_WORK_CONTINUITY.md']:
    path = ROOT / 'Docs/Engineering' / name
    if marker not in path.read_text(encoding='utf-8-sig'):
        with path.open('a', encoding='utf-8') as stream:
            stream.write(common)

notes = {
    'CHARACTER_GAMEPLAY_ARCHITECTURE.md': '''

## 2026-10-15 — ARCH-09/14/89/99 LockOn/진동 계약 실제 완료

앞선 착수 계약을 runtime5/Config1/DEV2로 적용했다. 진동은 config property의 Engine 기본1을 프로젝트 DefaultGame ForceFeedbackScale2로 override하며 PlayerController.cpp는 원래 SHA를 보존한다. 기존 Engine clamp와 finite pulse 수명을 재사용한다. LockOn은 직접 HP delegate/자기 constraint를, PatternAbility는 성공한 capture의 controller receipt와 기존 cleanup을 소유한다. CharacterDefinitionAssetName getter는 기존 ID의 읽기 전용 노출이다. 새 공개 gameplay 상태/manager/tag/runtime class는 없다.

Editor build·두 native RHI suite·HeinMach 단일 Epic Shipping build/cook·최종 container와 config·90초 offscreen 시작을 실제 완료했다. 초기 DEV 사망 assertion 보정/각 DLL과 실물 패드·Shipping 전체 combat 미확인 범위는 Metadata/LockOnRumble_20261015/FinalVerification.json을 따른다. 앞선 계획/진행 중 기록은 이 범위에서 완료로 대체한다.
''',
    'SOURCE_BP_CONFIG_ARCHITECTURE.md': '''

## 2026-10-15 — 컨트롤러 진동 엔진 배율 2 / HeinMach 패키징

Config/DefaultGame.ini의 [/Script/Engine.PlayerController] ForceFeedbackScale=2.0이 기존 Engine/Config/BaseGame.ini의1.0을 덮는다. 사용자 지정 무차원 배율이며 새 wrapper/설정 field/진동 시간은 없다. 설치 UE5.8 PlayerController.cpp:4778 이후 기존 엔진이 혼합된 각 모터값에 배율을 곱하고0..1로 clamp한다. 실제 PlayerController PIE 값2와 최종 pak DefaultGame 값2를 모두 확인했다. 기존 MapsToCook=HeinMach, Epic11그룹3/ResolutionQuality100과 기타 config는 보존한다.

새 runtime class/BP/맵 저장0, 최신 재배포 Windows 전체 폴더와 검증 근거는 Metadata/LockOnRumble_20261015/FinalVerification.json이다. 패드 실물 체감은 미측정이며 포화된 강한 출력이 물리적으로2배가 된다고 표현하지 않는다.
''',
    'COMBAT_UI_RUNTIME_20261011.md': '''

### 2026-10-15 — LockOn 후속 HeinMach Shipping 완료

앞선 실제 PIE 완료에 이어 Package06_LockOnRumble Shipping compile/cook8590/0error/UATexit0, 최종 container의 HeinMach 단일 map·ForceFeedbackScale2·Epic 설정과90초 offscreen 시작을 확인했다. 배포는 C:/Users/user/Desktop/Khazan_Release_20261015/Windows 전체 폴더다. 정확 source/module/package hash와 각 검증 한계는 Metadata/LockOnRumble_20261015/FinalVerification.json. 필수 잔여0이다.
'''
}
for name, note in notes.items():
    path = ROOT / 'Docs/Engineering' / name
    if marker not in path.read_text(encoding='utf-8-sig'):
        with path.open('a', encoding='utf-8') as stream:
            stream.write(note + '\n' + marker + '\n')
print('Final verification and domain records completed')
