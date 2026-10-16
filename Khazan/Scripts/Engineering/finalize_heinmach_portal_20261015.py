"""Bind the actual saved map, runtime binary, source and native evidence; append continuity."""
from pathlib import Path
import datetime, hashlib, json, math, struct

root = Path(__file__).resolve().parents[2]
base = root / 'Metadata/HeinMachPortal_20261015'
load = lambda p: json.loads((base / p).read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
driver = load('RHI06/Driver.json')
saved = load('Readback05/Readback.json')
placement = load('Placement06/Placement.json')
look = load('PortalLook03/PortalLook.json')
assert driver['status'] == saved['status'] == 'passed'
assert driver['saved_packages'] == saved['asset_saves'] == 0
build = (base / 'Build07.log').read_text(encoding='utf-16')
assert 'Result: Succeeded' in build
log = (base / 'RHI06/Editor.log').read_text(encoding='utf-8', errors='replace')
assert 'Actual Player locomotion walked into the saved entrance volume' in log
normal = [line for line in log.splitlines() if 'LogTemp: KZ_PORTAL KZBossPortal_0 ' in line]
assert len(normal) == 1 and 'moved=1 black=1.000' in normal[0], normal
assert 'moved=0 black=1.000' in log
module = Path(driver['actual_module'])
assert module.is_relative_to(root / 'Binaries') and sha(module) == driver['module_sha256']
map_file = root / 'Content/Maps/L_HeinMach_Environment.umap'
assert sha(map_file) == saved['map_sha256']
assert not(set(saved['unrelated_transform_changes'])-{'PlayerStart'})
assert saved['preserved_original_actors']+len(saved['unrelated_transform_changes']) == 10010

def package(path):
    return root / ('Content/' + path.split('.')[0][6:] + '.uasset')

assets = {look['system']: sha(package(look['system']))}
assert assets[look['system']] == look['system_sha256']
for row in look['materials']:
    assets[row['copy']] = sha(package(row['copy']))
    assert assets[row['copy']] == row['sha256']
for path, expected in look['shared_originals_sha256'].items():
    assert sha(package(path)) == expected
sources = {p: sha(root / p) for p in [
    'Source/Khazan/Environment/KZBossPortal.h', 'Source/Khazan/Environment/KZBossPortal.cpp',
    'Source/Khazan/Tests/KZBossPortalPIETest.cpp']}
captures = []
for name in ['Entry', 'Black', 'Arrival']:
    path = base / 'RHI06' / (name + '.png')
    data = path.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    width, height = struct.unpack('>II', data[16:24])
    captures.append(dict(file=str(path.relative_to(root)), width=width, height=height, sha256=sha(path)))
origin = placement['source_anchor']['world_location_cm']
boss = placement['source_boss']['world_location_cm']
facing = math.degrees(math.atan2(boss[1] - origin[1], boss[0] - origin[0]))
assert abs(facing - placement['source_anchor']['world_rotation_degrees']['yaw']) < 0.0001
report = dict(status='complete_main_saved_built_and_actual_walking_pie_verified',
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), project=str(root), remaining=[],
    runtime_files=2, development_test_files=1, source_sha256=sources,
    actual_module=str(module), module_sha256=sha(module), build='Build07.log',
    build_kind='Main source module suffix2026101517; standard Build06 could not replace a DLL in the live user editor',
    map='/Game/Maps/L_HeinMach_Environment', map_sha256=sha(map_file), placement_map_sha256=placement['after_sha256'],
    map_revision_after_placement=sha(map_file)!=placement['after_sha256'], new_assets_sha256=assets,
    shared_originals_sha256=look['shared_originals_sha256'], shared_originals_preserved=True,
    preserved_original_actor_transforms_at_placement=10010,
    current_unchanged_original_actor_transforms=saved['preserved_original_actors'],
    concurrent_post_placement_changes=saved['concurrent_post_placement_changes'],
    added_actors=['HM_Yetuga_EntrancePortal','HM_Yetuga_ArenaArrival'],
    concurrent_added_actor_labels=sorted(set(saved['added_actors'])-{'HM_Yetuga_EntrancePortal','HM_Yetuga_ArenaArrival'}),
    concurrent_additional_actor_count=saved['actor_count']-10010-2,
    entry=dict(label='HM_Yetuga_EntrancePortal', gate_cube_xy_cm=[19550,4270],
        floor_cm=placement['gate_floor'], trigger_half_extent_cm=[80,140,160],
        niagara=look['system'], niagara_relative_yaw_degrees=90),
    arrival=dict(label='HM_Yetuga_ArenaArrival', floor_cm=placement['exit_floor'],
        source=placement['source_anchor'], facing_yaw_degrees=facing, source_boss=placement['source_boss'],
        selection='TEMP portal arrival choice using original arena marker; not an original teleport rule'),
    fade_seconds=saved['fade_seconds'], numeric_policy='Fade durations and entry dimensions are editable assistant TEMP. Coordinates use saved original metadata and current collision measurements; yaw is calculated from original marker to original boss spawn.',
    validation=dict(actual_walking='RHI06/Driver.json', saved='Readback05/Readback.json',
        receipt=normal[0], idle_tick=False, duplicate_teleports=0, screenshot_files=captures,
        cases=['Player intent and CMC walking into saved entry', 'opaque black before teleport and camera cut',
            'arena arrival facing and walkable floor', 'input/action/invulnerability release',
            'repeated overlap ignored', 'missing destination rejected',
            'portal EndPlay preserves outside counted locks', 'destroyed destination fades back at source'],
        qa_only_texture_quality=2, qa_only_streaming_pool_mb=800, asset_saves=0,
        saved_dirty_maps=saved['dirty_maps'], readback_transient_dirty_content=saved['dirty_content'],
        observed_gpu_budget_warning='Video memory has been exhausted' in log),
    limitations=['Single-player same-world transition only; no Shipping/performance certification. Concurrent editor RHI capture showed an actual VRAM budget warning; no smooth-frame-rate claim.',
        'UnPossess and physically obstructed destination have runtime guards but no separate forced automated case.',
        'Existing encounter/monster spawning is unchanged.'],
    supersedes=['Boss_Start approach-corridor destination from Placement04/05',
        'RHI02 QA wrong input axis', 'RHI03 QA overly strict 1cm collision-adjustment tolerance',
        'RHI04 failure fixture offsets reached the arena cliff; final fixture uses proven standing floor',
        'Build06 LNK1104 locked standard DLL; RHI05 stopped before validation, final Build07 suffix/RHI06 used'])
(base / 'FinalVerification.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')

marker = '<!-- HeinMachPortal_20261015_complete -->'
def append(path, body):
    path = root / path
    if marker in path.read_text(encoding='utf-8-sig'):
        return
    body = body.replace('Entry/FadeOut/Black/Arrival', 'Entry/Black/Arrival').replace('4장', '3장').replace('4화면', '3화면').replace('4 PNG', '3 PNG')
    with path.open('a', encoding='utf-8', newline='\n') as stream:
        stream.write('\n\n' + body.strip() + '\n\n' + marker + '\n')

append('Docs/Engineering/HEINMACH_YETUGA_PORTAL_20261015.md', '''
## 2026-10-15 — 최종 Main 완료: 실제 걸어서 진입 → 전장 내부

앞선 Boss_Start 채택을 현재 목적지로 사용하지 않는다. 실제 도착 화면이 전장 직전 통로였으므로 원본 같은 JSON의 export482 `Yetuga_TargetPoint` → root470 `Properties.RelativeLocation=(-3761.6345,-11455,-4455.1245) cm`를 전장 내부의 기준으로 선택했다. 원본의 grab marker를 포탈 도착 기준으로 사용하는 선택은 TEMP이며 원작 포탈 동작의 복원이라고 표현하지 않는다. `SA_Yetuga` export1081/root450의 원시 위치 `(-5471.6367,-10702.597,-4276.216) cm`까지의 XY 벡터에 atan2(dY,dX)를 적용한 yaw는 156.25044846566882°다. 현재 맵 Pawn trace의 바닥 Z는 -4572.605507799506cm, normal.Z=.998964이며 배치 영수증은 Placement06이다. 현재 Encounter/보스 생성 방식은 변경하지 않았다.

최종 Main suffix Build07 성공 후 새 Main D3D12 RHI06의 `Khazan.Portal.PIE`가 Success다. 실제 Player intent → CMC → 동굴 충돌을 따라 걸어서 entry overlap을 발생시킨다. 실제 전장 이동은 1회이며 black=1에서만 TeleportTo를 실행했고, camera cut/지연 이력 초기화/도착 yaw·보행 가능 바닥/암전 복원/자기 입력·action block·무적 기여 회수가 통과했다. 중복 overlap, 목적지 없음, 외부 count를 유지한 portal EndPlay, 진입 후 목적지 소멸의 유한 복귀도 통과했다. 원본에 없던 영구 State/Manager/Subsystem/Ability나 기존 combat Source 변경은 없다. runtime 파일2, DEV test1, Main map1 및 전용 VFX 사본4개다.

검증 오류 이력도 보존한다. RHI02는 QA가 프로젝트의 X=전방 입력을 (0,1)로 호출한 오류였으며 게임 이동은 수정하지 않았다. RHI03은 실제 진입/전장 이동이 성공했으나 엔진 encroachment 및 지면 안착의 작은 위치 보정을 1cm 이내로 제한한 QA가 실패했다. 최종 검사는 실제 capsule radius 이내 도착·보행 가능 floor와 출발점 유지로 의미를 바로잡았다. runtime TeleportTo의 충돌 안전 보정을 제거하지 않았다. 각 실행의 실제 DLL SHA는 해당 Driver.json에 보존하며 최신 Source/표준 DLL/Map/4asset SHA 및 화면은 `Metadata/HeinMachPortal_20261015/FinalVerification.json`에 결속한다.

Fresh Readback05(save0/dirtyMap0)는 기존10009 actor transform·class 동일 및 포탈 배치 후 동시 저장의 PlayerStart1 수정을 구분해 기록했다. 우리 Placement06까지의 기존10010 actor transform/class 보존 이후에 생긴 별도 수정을 되돌리지 않았다. 추가2 actor, GateCube hidden/collision 설정, 목적지 참조/회전, trigger 크기, 전용 Niagara/상대 yaw90, 재질 alpha·blend·MI parameters 및 공유 원본4파일 SHA 보존이 통과했다. 마지막 Entry/FadeOut/Black/Arrival 실제 game viewport 4장은 해상도를 PNG header로 기록하며 요청 창 크기와 혼동하지 않는다. Editor QA texture quality2/pool800MB는 저장하지 않았다. Shipping/성능 인증, 별도의 강제 UnPossess/막힌 목적지 사례는 이번 완료 범위가 아니다.

조절은 World Outliner의 `Gameplay/YetugaPortal/HM_Yetuga_EntrancePortal`을 선택해 Portal Fade 설정과 `EntryVolume` box extent, `PortalEffect`의 Niagara·상대 위치/회전/크기를 편집한다. `HM_Yetuga_ArenaArrival`은 capsule 발 기준이며 위치와 yaw를 수정한다. runtime C++에 Level 좌표는 없다. 재검사만 필요하면 새 출력 폴더의 KZ_PORTAL_OUT/KZ_PORTAL_CAPTURE=1과 `heinmach_portal_validation_driver_20261015.py` 또는 readback script를 사용한다. 완료된 authoring을 반복 실행하거나 과거 map/DLL을 복사하지 않는다.

RHI04는 실제 이동·도착과 복구가 실행됐으나 반복 +1000cm 배치한 마지막 실패 시험체가 전장 절벽에 닿아 physics settling이 227.348cm였다. 최종 QA는 정상 도착으로 검증한 동일한 walkable floor를 실패 시험체에도 재사용한다. 게임 코드·목적지·암전 수치는 이 QA 수정 과정에서 바꾸지 않았다. fresh Readback05의 dirty map/content 목록은 최종 receipt에 보존하며 조회에서 dirty로 표시된 자원은 저장하지 않았다. 모든 content package가 dirty0이었다고 표현하지 않는다.

마지막 QA 빌드 중 메인 에디터가 실행돼 stock Build06이 LNK1104 공유 잠금으로 실패했다. 사용자 에디터를 종료하거나 reload/save하지 않고 Main Source의 suffix2026101517 모듈을 Build07로 빌드해 RHI06에서 검증했다. runtime portal 코드는 최초 stock 빌드 이후 바꾸지 않았고 후속 Source 수정은 DEV QA뿐이다. 열려 있던 Main HeinMach의 native portal 및 arrival 배치를 read-only로 관측했다. 이후 Main map 바이트가 재저장돼도 최신 디스크의 포탈 계약을 Readback05에서 다시 확인하며 과거 map으로 되돌리지 않는다.

최종 RHI 캡처에는 동시 에디터 실행 중 실제 VRAM budget 경고가 표시됐다. 전환 기능 Success와 단일 실행 프레임 성능 검증을 구분한다. 최신3장은 진입/완전 암전/전장 도착의 실제 화면이며 부분 fade-out 샘플은 이 실행에서 별도 PNG로 잡히지 않았다. 이전 RHI04/FadeOut.png는 이전 모듈/실행의 보조 화면으로만 남긴다. concurrent 추가 actor도 최종 영수증에 별도로 기록하고 이 작업의 추가 actor2개로 합산하지 않는다.
''')
append('Docs/Art/HEINMACH_YETUGA_PORTAL_20261015.md', '''
## 2026-10-15 — 최종 배치·외관 Main 완료

GateCube의 원래 transform은 보존하고 게임 표시·solid collision만 껐다. `HM_Yetuga_EntrancePortal` 중심은 (19550,4270,-6.752918548882)cm, entry half extent는 TEMP (80,140,160)cm다. portal/arrival 두 객체는 Gameplay/YetugaPortal 폴더에서 편집한다. 최신 도착점은 전장 내부 (-3761.6345,-11455,-4572.605507799506)cm, yaw156.25044846566882°이며 원작 Yetuga_TargetPoint의 XY와 현행 맵의 지면을 사용했다. 초기 Boss_Start는 전장 직전 통로여서 최종 목적지로 폐기했다. source RootComponent export470의 원시 위치와 SA_Yetuga export450까지의 방향 계산·TEMP 목적지 선택을 구분하며 정확한 원본·SHA는 Readback05와 Placement06에 있다.

현재 `/Game/VFX/Portal/YetugaEntrance/NS_YetugaEntrance`는 기존 N_Portal4Boss의 전용 사본이다. 실제6 renderer의 재질을 전용 master sprite/MI/core material 3개로 연결했으며 공유 원본4파일은 SHA 동일하다. 포탈 plane은 XZ이므로 컴포넌트 상대 yaw90으로 gate의 통과 방향을 향하게 했다. 재질 발광에 엔진 EyeAdaptationInverse Alpha1을 사용해 물리 노출에서 꺼지던 core를 보완했다. 색·alpha·blend·MI parameters와 입자 simulation/분산은 원본을 유지한다. 재질 compile error0이며 원본 graph를 추출 불가한 Khazan 원작 shader라고 주장하지 않는다. 기존 Fab portal의 현행 맵 적용이다.

Main D3D12 RHI06의 실제 game viewport에서 청록색 안개 gate, 진입 암전, 전장 내부 도착을 검수했다. Entry/FadeOut/Black/Arrival4장과 실제 PNG 해상도/해시는 FinalVerification.json에 있다. 이전 VisualTrials02의 회전만 한 어두운 후보와 RHI02/03/04 QA 실패는 최종 완료본으로 오인하지 않는다. 원본 alpha/blend/MI parameters와 공유 원본4파일 보존을 fresh saved Readback05에서 확인했다. 포탈 배치 시 기존10010 actor transform/class를 보존했고, 그 뒤 Main 동시 저장에서 이동한 PlayerStart1개는 되돌리지 않았다. 최신10009 actor 동일 및 PlayerStart의 전후 transform을 별도로 기록한다. Source/전환 수명 검증은 Engineering 동명 문서에 분리했다.

동시 HeinMachLookSpin 작업은 이 최신 Main map을 보존해야 한다. 오래된 Work map 전체를 복사하면 portal/arrival actor가 사라진다. Main 최신 Source로 빌드된 DLL을 사용해 필요한 look 필드만 반영하며, KZBossPortal class가 없는 과거 private DLL로 최신 map을 열어 저장하지 않는다. 완료 영수증의 map SHA/두 actor/전용 Niagara 참조를 반영 후 다시 표적 확인한다.
''')
append('Docs/Engineering/ENGINEERING_PROJECT_STATE.md', '''
## 2026-10-15 — HeinMach GateCube → Yetuga 전장 포탈 Main 완료

배치 Actor KZBossPortal(runtime2/DEV1)로 실제 capsule 진입·암전·같은 월드 이동·복원 및 원인별 입력/ASC cleanup을 구현했다. Main suffix Build07/새 Main D3D12 RHI06 실제 walking suite/fresh Readback05가 통과했다. 기존 combat Source/Config 수정0이며 실제 목적지는 Boss_Start 통로가 아닌 Yetuga_TargetPoint 기준 전장 내부다. 조절 위치·TEMP·검증 한계는 HEINMACH_YETUGA_PORTAL_20261015.md, 정확 SHA/범위는 Metadata/HeinMachPortal_20261015/FinalVerification.json을 따른다. 필수 잔여0이다.
''')
append('Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md', '''
## 2026-10-15 — HeinMach 포탈 완료 / 재개 기준

Main 저장·Main suffix Build07·RHI06의 실제 Player intent/CMC walking·암전·전장 이동 및 실패/EndPlay count cleanup, Readback05의 저장 계약 검증이 완료됐다. 상태는 Metadata/HeinMachPortal_20261015/FinalVerification.json 및 ResumeState.json, 상세는 HEINMACH_YETUGA_PORTAL_20261015.md가 정본이다. 현재 필수 미완료0이다.

후속은 Router → 관련 Architecture/현행 문서 → FinalVerification → 현재 map/Source의 해당 필드만 읽는다. 단순 확인은 readback_heinmach_portal_20261015.py, 실제 재실행은 새 KZ_PORTAL_OUT과 KZ_PORTAL_CAPTURE=1의 heinmach_portal_validation_driver_20261015.py를 사용한다. 과거 실패 autorun/old DLL/old Work map을 전달하지 않는다. Source의 runtime 좌표 hardcode0/자원 owner는 portal 한 개이며 별도 manager나 Interact Ability를 선행 추가하지 않는다. Art 배치/노출·공유원본 보호는 Art 동명 문서를 따른다. 동시 look 작업이 Main map을 바꿀 때 portal2 actor와 새 Niagara 참조를 보존해야 한다.
''')
append('Docs/Art/ART_PROJECT_STATE.md', '''
## 2026-10-15 — GateCube 포탈과 Yetuga 전장 도착점 Main 완료

Main HeinMach에 Gameplay/YetugaPortal의 portal/arrival2 actor 및 전용 VFX4asset을 추가했다. 배치 단계의 GateCube transform과 기존10010 actor class/transform, 공유 포탈 원본4파일을 보존했다. 이후 동시 저장의 PlayerStart1 수정은 유지했으며 최신10009 actor 동일과 해당 전후 transform을 별도로 기록했다. 상대 yaw90/발광 노출 보상과 전장 내부 지면 배치를 RHI06 실제 walking/4화면 및 fresh Readback05에서 확인했다. 최신 map을 과거 Work map으로 교체하지 않는다. 세부·수치 출처·한계는 HEINMACH_YETUGA_PORTAL_20261015.md 및 Metadata/HeinMachPortal_20261015/FinalVerification.json을 따른다.
''')
append('Docs/Art/ART_WORK_CONTINUITY.md', '''
## 2026-10-15 — HeinMach 포탈 완료 / Main map 보존

현재 필수 잔여0이다. Metadata/HeinMachPortal_20261015/FinalVerification.json, Placement06/PortalLook03/Readback05/RHI06가 최종 근거다. Boss_Start 통로 위치/회전만 한 어두운 shared N_Portal4Boss 후보는 현재 설정이 아니다. 현재는 전장 내부의 HM_Yetuga_ArenaArrival과 전용 NS_YetugaEntrance다.

후속 look/Level 작업은 새 Main의 portal/arrival actor2, ExitPoint 참조, Niagara 상대 yaw90과 전용4asset을 보존한다. 과거 private Work map을 통째로 복사하지 않으며 KZBossPortal class가 포함된 최신 Main DLL로 편집한다. Router → Art 현행 동명 문서 → FinalVerification → 필요한 해당 actor/material만 확인한다. 단순 재감사는 readback script(save0)로 충분하고 author/원본 추출/Content 전수조사는 반복하지 않는다. 전환 gameplay 검증은 Engineering 동명 문서를 따른다.
''')
append('Docs/Art/ART_KNOWLEDGE_INDEX.md', '''
## 2026-10-15 — HeinMach GateCube 포탈 조회

GateCube 위치/실제 동굴 지면·포탈 정면·전장 내부 도착점은 HEINMACH_YETUGA_PORTAL_20261015.md 및 Metadata/HeinMachPortal_20261015/{FinalVerification,Placement06/Placement,PortalLook03/PortalLook,Readback05/Readback}.json을 우선한다. 실제 전장 source는 기존 HeinMach_Spawn_Main01.json의 Yetuga_TargetPoint(root470)/SA_Yetuga(root450)이며 Boss_Start는 전장 직전 통로다. 전체 환경을 다시 조사하지 않는다. 실제 화면은 RHI06의4 PNG다.
''')
append('Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md', '''
## 2026-10-15 — ARCH-05/09/11/15 포탈 실행 검증 완료

앞선 자동 진입 portal 계약을 Main runtime2/DEV1/배치2 actor로 구현했다. 독립 수명은 기존 engine Actor가 소유하고 ASC action block/tag count 및 Controller ignore count의 자기 기여만 회수한다. 실제 Player intent/CMC walking, black-before-teleport, 전장 floor/yaw와 중복/소멸 cleanup이 RHI06에서 통과했다. 새 범용 Interaction manager/Ability/태그 사본은 없다. 최신 좌표/전용 Niagara·TEMP·정확 검증은 HEINMACH_YETUGA_PORTAL_20261015.md 및 FinalVerification.json을 따른다. 이는 포탈 한 수직 절편이며 전체 Interaction/Encounter 마이그레이션 완료를 뜻하지 않는다.
''')
append('0_DOCUMENT_ROUTER.md', '''
## 2026-10-15 — HeinMach GateCube 포탈 후속 조회

같은 월드의 Yetuga 전장 포탈 동작은 Docs/Engineering/HEINMACH_YETUGA_PORTAL_20261015.md, 배치·전용 Niagara는 Docs/Art/HEINMACH_YETUGA_PORTAL_20261015.md를 따른다. 최신 증거는 Metadata/HeinMachPortal_20261015/FinalVerification.json이다. 현재 Main의 portal/arrival2 actor와 전용4asset을 기존 look/Level 작업에서 보존한다. 과거 Work map/DLL 전달이나 완료된 authoring을 반복하지 않는다.
''')
resume = load('ResumeState.json')
resume.update(status=report['status'], remaining=[], next=[], final_receipt='FinalVerification.json',
    last_pass=['Build07 Succeeded', 'RHI06 actual walking/native portal suite Success', 'Readback05 saved contract passed'],
    placement_launch='Placement06/Launch.json', build='Build07.log: Succeeded')
(base / 'ResumeState.json').write_text(json.dumps(resume, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(dict(status=report['status'], new_assets=len(assets), runtime_files=2,
    current_unchanged_original_actors=saved['preserved_original_actors'],
    preserved_concurrent_changes=list(saved['concurrent_post_placement_changes']),
    module_sha256=sha(module), map_sha256=sha(map_file)), indent=2))
