"""Snapshot verified snow delivery and append separate Art/Engineering handover records."""
from pathlib import Path
import datetime
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
STAGE = Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
OUT = ROOT / 'Saved/ImportReports/HeinMachSnow_20261006'
RESUME = OUT / 'Resume20261007'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

delivery = read(OUT / 'Delivery20261007.json')
native = read(OUT / 'MainVerification20261007.json')
update = read(OUT / 'SnowContactModuleUpdate.json')
nav = read(RESUME / 'NavigationFinal.json')
collision = read(RESUME / 'CollisionChannelsPreserved.json')
scene = read(RESUME / 'SceneFinalAudit.json')
floor = read(RESUME / 'FloorCMCBeforeAfter.json')
perf = read(RESUME / 'Profile(20261007_132110)_SnowTick.json')
assert all((delivery['success'], native['success'], update['success'], nav['passed'],
            collision['success'], scene['success'], floor['success']))
assert native['pid'] == 27452 and native['native_pie_passed']
map_path = ROOT / 'Content/Maps/L_HeinMach_Environment.umap'
assert sha(map_path) == update['map_sha256'] == delivery['map_sha256']
module_path = Path(native['module_path'])
assert sha(module_path) == update['module_sha256']
asset_files = [r for r in delivery['files'] if r['path'].endswith('.uasset')]
assert len(asset_files) == 48
for row in asset_files:
    assert sha(ROOT / row['path']) == row['sha256'], row['path']
own_source = {}
for rel in ('Source/Khazan/Environment/KZSnowDeformation.h',
            'Source/Khazan/Environment/KZSnowDeformation.cpp',
            'Source/Khazan/Tests/KZSnowDeformationPIETest.cpp'):
    own_source[rel] = sha(ROOT / rel)
    assert own_source[rel] == sha(STAGE / rel), rel
assert own_source['Source/Khazan/Environment/KZSnowDeformation.cpp'] == update['source_sha256']
normal_path = ROOT / 'Binaries/Win64/UnrealEditor-Khazan.dll'
assert sha(normal_path) == update['current_normal_module_preserved_sha256']
images = {p.name: sha(p) for p in sorted((ROOT / 'Saved/SnowQA').glob('Snow_*.png'))}
assert len(images) == 5
report = dict(success=True, utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              map_package='/Game/Maps/L_HeinMach_Environment', map_sha256=sha(map_path),
              native_assets=48, native_verification=native, source_sha256=own_source,
              module_sha256=sha(module_path), normal_module_preserved_sha256=sha(normal_path),
              collision=collision, route_summary={k: v for k, v in nav.items() if k != 'actions'},
              floor_summary=dict(component=floor['component'], roughness_ratio=floor['roughness_ratio'],
                  reduction_percent=(1-floor['roughness_ratio'])*100,
                  passes=[{k: p[k] for k in ('mode','distance_cm','resampling_cm',
                      'height_second_difference_rms_cm')} for p in floor['passes']]),
              cpu_perf=perf, screenshot_sha256=images,
              last_read_only_interactive_state=dict(pid=17552, world='/Game/Maps/DevMap.DevMap',
                  game_world=None, dirty_content=0, dirty_maps=0,
                  snow_native_class='/Script/Khazan.KZSnowDeformation',
                  observation='2026-10-07 ~04:26 UTC; opened independently; no save/reload/PIE/close by snow task'),
              limits=['Original cooked shader graph/HLSL and same-frame snow parity not recovered',
                      'Lying torso and isolated equipment poses are contact fixtures, not gameplay knockdown/attack animation validation',
                      'Bounded 2D height-gated tile cache; far old history can be evicted; no timed refill',
                      'Shipping GPU/frame-rate, hardware input and network behavior not verified'])
(OUT / 'FinalVerification20261007.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')

marker = '## 2026-10-07 — HeinMach 눈 변형 메인 반영·최종 검증 완료'
art = '''
메인 `/Game/Maps/L_HeinMach_Environment`에 눈 변형을 선택 반영했다. 원래 weighted terrain의 텍스처·레이어·UV를 보존한 전용 Nanite 지면 46개와 머테리얼 2개, `HM_SnowDeformation` Actor 1개다. 총 9,869 actors이며 기존 9,868 actor의 transform/PlayerStart와 화로 작업 258 actors를 보존했다. 48 asset/맵의 전달·최종 SHA는 `Saved/ImportReports/HeinMachSnow_20261006/Delivery20261007.json`, 최신 검증은 `FinalVerification20261007.json`이다.

파임은 실제 높이 변위, 압축 field의 미분 normal, 압축 색·roughness로 표현한다. quintic 타원 brush와 완만한 rim, max 누적으로 둥근 경계와 압축 한계를 둔다. 발/발끝, 몸통·팔다리, 실제 부착 장비와 합쳐진 원작 장비 메시의 접촉을 소비한다. 원래 눈/얼음/바위 가중치를 유지하며 공중 무기는 눈에 기록하지 않는다. Nanite와 physics substrate의 약 8cm 오차는 전용 메시 precision12/MaxEdgeLengthFactor2.0 및 recook로 교정했다. 이는 엔진 기술 설정이며 원작 수치가 아니다.

원작 출처는 `OriginalSnowContracts.json`의 package/file/SHA/field와 원시 `Saved/Extracted/HeinMachSnow_20261006/Source`다. WLM_HeinMach의 SnowHeight15/DeepSnow Displacement15, WLM_HeinMach2의 SnowHeight25/DeepSnow15/DeepSnow2 7.5는 원작 shader 계수다. 이 작업의 15cm/7.5cm는 계수를 높이로 해석한 native 설정이며 원작 실행 cm 직접 확인이 아니다. 일반 눈4cm, rim2.5cm, 압축 darkening.06/roughness+.08, 발17×9cm/reach12cm, 몸22×18cm/reach24cm, 무기5cm, height gate32cm/normal.Z.5/teleport256cm는 어시스턴트 임시값이다. 둥근 윤곽, 얕은 접촉, 바닥 관통 방지 및 중첩 층 오염 억제를 위해 선정했고 Actor 조정 속성/전용 material에 집중했다. 원작 writer 실행 식/동일 프레임 비교는 미확보다.

최종 실제 메인 DX12 PIE `Khazan.Snow.PIE` Success: 2026-10-07 04:22:07 UTC, PID27452. 깊이 capture785.0→799.5, 실제 파임14.5cm, compressed render/기존 collision 차이<1cm. 실제 Player run447.37cm/압축485샘플, Dodge383.41cm/5샘플, toe contact85프레임/압축1.0. 4 Monster family 이동·몸 접촉·원본 장비 접촉, 공중 negative, 반복 압축/창 이동 cache/EndPlay 복구 통과. 몸·무기 격리 pose는 실제 gameplay 넘어짐/공격 montage의 전체 재생을 검사한 것과 구분한다. 화면은 `Saved/SnowQA/{Snow_Untouched,Snow_Compressed,Snow_Player_Run_Dodge,Snow_Weapon_Contact,Snow_Monster_Torso}.png`; 무파임/파임 이미지 직접 검수 및 SceneDepth 값 검증 완료다. 원작과 픽셀 동일 완료로 표현하지 않는다.

최종 편집 대상은 `/Game/Maps`의 플레이 맵이다. 별도 `_Art/.../Maps` 보관 맵과 GameDefaultMap은 이 작업에서 교체하지 않았다. 후속 조정은 현재 메인 맵의 46 surface/Actor/2 material만 수정하며 초기 authoring/full map 복원을 반복하지 않는다. 원작 shader와 동일 카메라 연속 프레임을 확보하면 압축 재질·rim·높이 해석을 그 근거로 조정한다. runtime/충돌·경로·성능 계약은 `../Engineering/HEINMACH_SNOW_IMPLEMENTATION_20261006.md` 마지막 절에 분리했다.
'''
engineering = '''
실제 메인 Source에 level presentation owner `AKZSnowDeformation` h/cpp 2개와 development-only `KZSnowDeformationPIETest.cpp`를 반영했다. 기존 ASC/Ability/CMC/Locomotion/AnimInstance/AI 상태·입력·취소 수명은 변경하지 않는다. finalized pose를 game-thread TG_PostUpdateWork에서 읽고 발/Toe0, pelvis/spine/head/팔·다리를 관측한다. 몸 접촉은 MOVE_None에서도 가능하다. 발 중앙이 작은 돌을 맞추면 실제 발끝을 같은 reach12cm로 재검사한다. 접촉 height를 늘려 공중을 땅으로 취급한 변경은 없다.

장비는 기존 부착 component의 actual bounds 경로, 합쳐진 장비는 실제 imported LOD0 지배 weapon bone vertex를 editor에서 bone-local center/극점으로 굽는다. 11 actual component mesh 입력에서 원작 장비 4 profile을 저장했다(`Resume20261007/MergedWeaponProfiles.json`). runtime에 전체 vertex CPU skinning이나 gameplay 무기 상태 사본을 추가하지 않는다. 약한 component/bone contact history와 자기 MID만 소유하며 EndPlay에 자신이 계속 소유한 material slot만 복구한다.

40.96m 이동 창/2cm texel/2048² RGBA16F, tile128/cache256, CPU field 약48MiB/GPU32MiB는 기술 예산이다. toroidal GPU addressing으로 겹친 tile을 보존하고 새 strip/dirty tile만 region update, zero tile batch로 clear한다. 오래된 먼 CPU tile은 예산 초과 시 퇴거한다. window 바깥 모든 actor의 무제한 영구 이력/중첩 층 분리 field/원작 refill 시간을 보장하지 않는다. 수치 provenance와 material은 Art 정본에 분리했다.

지형 떨림은 nav 간격만으로 단정하지 않았다. 작은 돌의 실제 Pawn blocking과 아래 walkable substrate를 9점 검사해 노출 bump≤12cm/bounds height≤60cm/XY≤800cm의 65 component만 Pawn Ignore·CanEverAffectNavigation=false·HeinMachMicroDressing으로 저장했다. 임시 선별 기준이며 원작 데이터가 아니다. 큰 돌·낭떠러지·route wall2,281/NavBounds242/Null26/Links24/기존 actor pose를 보존했다. 이전 private 작업의 표적 외16개는 unchanged main baseline 응답/nav/tag로 복구했고 81개×노출 표준 collision 8채널 저장/reload를 검사했다(`CollisionChannelsPreserved.json`). 65개 이외의 채널 응답은 baseline과 같다. 실제 새 메인 saved audit65개를 재확인했다.

Recast build 완료를 대기하고 map을 저장한 후 기존 원작 MoveTo63/1,485 point/1,422 complete segment 모두 통과, collapsed17/실패0(`Resume20261007/NavigationFinal.json`). 표적 WaterfallUp StaticMeshActor_6987 bump11.807cm 위에서 actual CMC가 약685/682cm 이동한 전후 비교: 10cm 재표본화 높이 2차 차분 RMS1.81303582→1.50061163cm, 비율.82767898/17.2321% 감소(`FloorCMCBeforeAfter.json`). 전 맵/모든 animation jitter 완전 제거의 증거로 확대하지 않는다. 전역 CMC MaxStep/slope/nav voxel이나 별도 smooth-path manager는 추가하지 않았다.

격리 ColdBuild_LatestMainFinal/ColdBuild_ToeEdgeContact/ColdBuild_DodgeContactSamples 모두 Succeeded. 최신 main runtime Source를 수령해 빌드했으며 독립 Monster 작업의 development-only KZMonsterAIPIETest.cpp 변화만 module snapshot guard에서 제외/보존했다. 앞선 main Dodge QA 두 번의 압축0 실패 로그는 남겼다. 실제 착지 종료 대기/발끝 fallback/접촉 diagnostics 보완 후 final main PIE Success 04:22:07 UTC: GPU파임14.5cm, render/physics<1cm, 실제 Player 이동/회피 및 4 Monster 발·누운 torso·merged weapon, airborne suppression/반복50회/6000cm 창 이동 이력/EndPlay 복구. 격리 몸/장비 fixture를 gameplay knockdown·attack hit QA로 승격하지 않는다.

성능은 메인 `Saved/Profiling/CSV/Profile(20261007_132110).csv`, SnowTick active1,094 samples 평균.9883947ms/P95 3.0408ms/max19.9835ms. 최초 asset/cache 작업과 다른 editor 경쟁을 포함한 Development Editor 게임 스레드 값이다. 이전 warm .5019ms와 cold1.7657ms는 다른 범위이며 개선율로 계산하지 않는다(12:59 기록의 `.1.7657`은 `1.7657`의 표기 오류). shipping FPS/GPU cost/network 검증은 미완료다.

전달 결과:48 native assets+현재 map+Snow Source3+private RHI 의존+Nanite tessellation SystemSettings. 다른 AI 의존/Config 변경은 기존 사용자 작업으로 보존했다. DLL은 manifest-selected `UnrealEditor-KhazanSnow20261007.dll`, BuildId55116800, SHA c76703374ec0573caba7948d4cbcef1e8058d3e749711de2e2f859ac6af0e3ce. 일반 UnrealEditor-Khazan.dll은 독립 작업의 최신 hash17b0a230...49 상태를 그대로 보존했으며 덮어쓰지 않았다. mapSHA4560f07aa655421056cb6846b2df4646778b01636f752c4e3d2e2cfda8256129. 백업은 DeliveryBackup20261007 및 ModuleBeforeContact 파일이다. MainVerification20261007/FinalVerification20261007이 latest source/asset/module/scene/PIE 증거다.

사용자 editor를 save/reload/PIE/camera/close하지 않았다. 작업 전용 main PID27452는 검증 후 정상 종료. 독립적으로 새로 열린 main PID17552를 ~04:26 UTC read-only 확인: DevMap/PIE없음/dirty0/native KZSnowDeformation class 존재, 실제 log의 alias module 로드도 확인. 에디터를 다시 종료·재시작할 필요 없이 사용자가 `/Game/Maps/L_HeinMach_Environment`를 열어 Play할 수 있다. initial deliver.py는 재실행하지 않는다. 후속 Source 변경은 current main을 stage에 수령/빌드하고 guarded update_module.py를 사용하며, 다른 build가 일반 DLL을 재작성해도 그 DLL을 이전 snapshot으로 복구하지 않는다. 현재 소스가 전부 정상 빌드되면 일반 DLL 경로도 동일한 native class를 포함한다.
'''
entries = {
    'Docs/Art/HEINMACH_SNOW_DEFORMATION_2026-10-06.md': art,
    'Docs/Engineering/HEINMACH_SNOW_IMPLEMENTATION_20261006.md': engineering,
    'Docs/Art/ART_PROJECT_STATE.md': '''
`/Game/Maps/L_HeinMach_Environment`의46 native snow surface/2 material/field Actor를 실제 메인에 반영했다. 발·무기·몸 접촉에 둥근 높이 파임과 압축 재질을 적용, 기존9,868 poses/화로258 보존(총9,869). Main saved reload/native PIE Success04:22:07 UTC 및48 assetSHA passed. 원작 계수의 native cm 해석/임시 contact·rim·재질 값과 original shader/pixel 비교 미완료는 [눈 정본](HEINMACH_SNOW_DEFORMATION_2026-10-06.md) 마지막 절을 따른다. 지면 충돌/경로/성능은 Engineering 정본에 분리했다. 다른 Monster/PlayerParts 작업 완료 여부를 이번 결과로 승격하지 않는다.
''',
    'Docs/Engineering/ENGINEERING_PROJECT_STATE.md': '''
새 runtime 파일2(h/cpp)의 AKZSnowDeformation level Actor와 dev QA1을 실제 메인에 반영, finalized contact→bounded CPU tile/toroidal GPU field→material 경로다. character gameplay source/상태·CMC 전역 tuning은 추가하지 않았다. 작은 돌65개의 실제 Pawn/Nav 기여를 제외하고 원작63 MoveTo/1,422 segments 통과, 표적 CMC 높이 차분17.23% 개선. main Khazan.Snow.PIE Success04:22:07 UTC/PID27452, aliasDLL/source/48asset/map SHA 및 native scene passed. SnowTick Development Editor 평균.9884ms/P95 3.0408ms, shipping GPU/FPS 미검증. [구현 정본](HEINMACH_SNOW_IMPLEMENTATION_20261006.md) 마지막 절과 Saved/ImportReports/HeinMachSnow_20261006/FinalVerification20261007.json을 따른다. 새 main PID17552는 native class가 있는 DevMap/dirty0/PIE없음으로 read-only 확인했다.
''',
    'Docs/Art/ART_KNOWLEDGE_INDEX.md': '''
첫 자료는 [HEINMACH_SNOW_DEFORMATION_2026-10-06.md](HEINMACH_SNOW_DEFORMATION_2026-10-06.md) 마지막 절과 `Saved/ImportReports/HeinMachSnow_20261006`: OriginalSnowContracts(package/field/raw/SHA), Topology/Authoring/ShaderStats, Delivery20261007/SnowContactModuleUpdate/MainVerification20261007/FinalVerification20261007. raw는 Saved/Extracted/HeinMachSnow_20261006/Source. final48 asset/mesh46/material2은 Rendering/HeinMachSnow, 플레이 map은 /Game/Maps. SnowQA5PNG/RuntimeGeometry가 실제 main 화면·14.5cm 변위 증거다. stripped source shader를 확보한 것으로 해석하거나 initial full author/deliver를 최신 사용자 맵 위에서 반복하지 않는다.
''',
    'Docs/Art/ART_WORK_CONTINUITY.md': '''
메인 Art 반영/48asset+맵 SHA/기존9,868poses·화로258 및 actual saved reload 통과. 현재 총9,869, Snow46+material2+HM_SnowDeformation. final actual main PIE04:22:07 UTC Success/PNG5 및 NativeGeometry14.5cm. 앞선 전달 전·Dodge 실패 checkpoint는 latest 성공이 대체한다. 정본 HEINMACH_SNOW_DEFORMATION_2026-10-06.md 마지막 절 및 Saved/ImportReports/HeinMachSnow_20261006/FinalVerification20261007.json이 재개 시작점이다.

이 구현 전달에 pending 파일은 없다. 후속 룩 조정은 current /Game/Maps 맵의 snow46/2material/Actor만 대상으로 하며 initial author/deliver/full-map 복사를 반복하지 않는다. 원작 same-camera snow 연속 프레임/shader 실행 식/원본 coefficient 단위가 확보되면 radius/rim/PBR/native15·7.5cm를 재검토한다. 지금 값은 원작 직접 검증·pixel 동일이 아니다. 기존 사용자 editor 변경은 보존했다. runtime/충돌/nav 및 모듈 재개는 Engineering continuity에 분리한다.
''',
    'Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md': '''
Snow 자체의 메인 Source3/RHI/Nanite/48assets/map/aliasDLL 전달 완료, final main PID27452 Khazan.Snow.PIE Success04:22:07 UTC와 source/module SHA passed. 최신 Actor cppSHAa0b29dec3a1ab141fb5ffbd76e20af4cb93f32927e3efcb4d0981b6bb12afe97, aliasDLL c7670337...2e2f859ac6af0e3ce, map4560f07a...2cfda8256129. FinalVerification20261007.json과 HEINMACH_SNOW_IMPLEMENTATION_20261006.md 마지막 절이 재개 정본이다. native foot/toe·4family/body/actualequipment/airnegative/depth/cache/repeat/EndPlay 통과. 앞선 두 main Dodge 실패는 보완 전 기록으로 보존한다.

65 supported micro stone Pawn/Nav 제외, 표적 외 private16개 복원,81×8 표준 collision response 저장/reload passed. 원작63 MoveTo/1,485point/1,422segment passed. actual CMC 표적 차분RMS17.23% 감소. 마지막 CSV1094 active mean.9884/P95 3.0408ms; shipping GPU/전체FPS 및 모든 knockdown/attack montage parity는 미검증이다. Original shader/same-frame 미확보/2D cache budget 한계는 유지한다.

Snow own background editor 정상 종료; 새 main17552(독립 작업이 실행)를 read-only 관측해 native class/DevMap/dirty0/PIE없음 확인, 사용자 Play 준비 상태는 변경하지 않았다. initial deliver.py 재실행 금지. 후속 Source 수정 시 최신 main Source/Config를 snow stage에 받아 필요분만 유지→stage ColdBuild→update_module.py가 current ownSHA/다른 runtimeSource를 검증해 ownalias만 갱신→launch_main_verify.py로 background main QA. 타 작업의 Monster dev test snapshot 차이는 명시해서만 제외하며 runtime Source 차이는 수령 후 재빌드한다. 일반 DLL을 이전 snapshot으로 덮어쓰지 않는다. 다른 Monster foot/PlayerParts pending 진행은 그 정본을 따르며 여기서 완료로 읽지 않는다.
''',
    'Docs/Engineering/PHYSICS_DIAGNOSTICS.md': '''
증상은 HeinMach의 작은 바닥 돌 위에서 capsule/CMC가 표면 요철을 따라 높이가 변하는 현상이다. nav 해상도만의 문제로 확정하지 않았다. actual Pawn block과 그 아래 walkable substrate를 검사해65 supported micro dressing만 Pawn Ignore/Nav 영향false로 저장, 큰 돌/절벽/기존2,281route wall/poses는 보존했다. 81component의8노출 표준 channel을 원본과 비교 저장/reload하여 Pawn65개 외 응답을 보존했다. 재검증 Recast63MoveTo/1,485points/1,422complete segments 통과.

WaterfallUp StaticMeshActor_6987(노출bump11.807cm) 전후 actual CMC 약685/682cm 이동을 10cm 재표본화한 높이2차차분RMS1.81303582→1.50061163cm(17.2321% 감소). 원인·결과의 범위는 이 표적 fixture이며 모든 map animation 떨림 제거로 확대하지 않는다. CMC/nav 전역 MaxStep/slope/voxel과 character physics source는 이 눈 작업에서 수정하지 않았다. snow visual 변위는 기존 substrate collision 위로 쌓이고 접촉 시 substrate까지 압축한다. Actual RHI 압축깊이14.5cm/render-physics<1cm/main Khazan.Snow.PIE Success04:22:07 UTC. 근거는 Saved/ImportReports/HeinMachSnow_20261006/Resume20261007/{FloorCMCBeforeAfter,CollisionChannelsPreserved,NavigationFinal}.json와 FinalVerification20261007.json, 상세는 HEINMACH_SNOW_IMPLEMENTATION_20261006.md 마지막 절이다.
''',
}
for rel, body in entries.items():
    path = ROOT / rel
    assert path.is_file(), rel
    if marker not in path.read_text(encoding='utf-8-sig'):
        with path.open('ab') as f:
            f.write(('\n\n' + marker + '\n' + body.rstrip() + '\n').encode('utf-8'))
print('SNOW_FINAL_VERIFIED', len(asset_files), 'assets;', len(entries), 'documents appended')
