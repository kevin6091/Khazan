"""Close this asset-only task from actual Main receipts; append domain documentation."""
from pathlib import Path
import datetime,hashlib,json
main=Path(__file__).resolve().parents[2]
base=main/'Metadata/HeinMachLookSpin_20261015'
read=lambda rel:json.loads((base/rel).read_text(encoding='utf-8'))
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
delivery=read('MainDelivery02/Receipt.json');assert delivery['status']=='delivered'
latest=read('LatestMainRevision.json')
assert latest['status']=='preserved_concurrent_revision_verified'
for row in delivery['rows']:
    expected=latest['current_map_sha256'] if row['file'].endswith('.umap') else row['after_sha256']
    assert sha(main/row['file'])==expected,row['file']
prep=read('Preparation.json')
for rel,digest in prep['protected'].items():assert sha(main/rel)==digest,rel
saved=read('MainLatestSaved02/Verification.json');assert saved['status']=='passed'
portal=read('MainLatestSaved02/PortalPreservation/Readback.json');assert portal['status']=='passed'
assert portal['map_sha256']==latest['current_map_sha256']
scene=read('MainScene01/Capture.json');assert scene['success'] and scene['asset_saves']==0
native=read('MainDevSpin01/Driver.json');assert native['status']=='passed'
assert len(native['tests'])==2 and all(row['passed'] for row in native['tests'])
assert not native['material_compile_failures'] and native['saved_packages']==0
assert native['module_sha256']==scene['module_sha256']
assert read('Review/VisualReview.json')['status']=='reviewed'
hein=read('MainHeinSpin02/Driver.json')
assert hein['tests'][1]['passed'] and hein['saved_packages']==0 and not hein['material_compile_failures']
hein_log=(base/'MainHeinSpin02/Editor.log').read_text(encoding='utf-8',errors='replace')
assert 'CombatEffect Natural Node=SpinningAttack01 SeenEvents=29 Sections=3' in hein_log
assert 'CombatEffect boundary fixtures complete' in hein_log
for run in ['MainSaved01','MainLatestSaved02','MainScene01','MainHeinSpin02','MainDevSpin01']:
    assert read(run+'/Exit.json')['exit']==0
for run in ['VFXDevFinal03','VFXHeinFinal03']:assert read(run+'/Probe.json')['status']=='passed'
colour=read('ColourFinal03/Comparison.json');assert colour['paired_images']==322
review=read('ColourComparison01/Review.json');assert not review['unresolved']
policy=read('CandidateAuthor01/Author.json')['lighting_policy_TEMP']
current_rows=[dict(file=row['file'],before_sha256=row['before_sha256'],
    delivered_sha256=row['after_sha256'],current_sha256=sha(main/row['file'])) for row in delivery['rows']]
report=dict(status='complete_main_saved_and_native_pie_verified',
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),remaining=[],
    project=str(main),main_asset_rows=current_rows,protected_packages=len(prep['protected']),
    new_runtime_files=0,main_source_writes=0,main_config_writes=0,main_dll_writes=0,
    build='No new build: this request changes presentation assets only. Fresh tests use the currently loaded Main module.',
    scene_policy_TEMP=policy,exposure_bias_change_ev=-1.05,
    saved_audit=saved,raw_level_actor_count=portal['actor_count'],
    unique_actor_labels=saved['actor_count'],
    newer_main_map_rebased=True,rebase='MapRebase.json',
    preserved_portal_contract='MainLatestSaved02/PortalPreservation/Readback.json',
    delivered_map_digest=delivery['rows'][0]['after_sha256'],
    current_map_digest=latest['current_map_sha256'],later_concurrent_revision=latest,
    portal_and_arrival_preserved=True,concurrent_player_start_and_monster_placement_preserved=True,
    source_particle_copy_changes='Exactly two Required.Material references; other modules, lifetime, curves and shared source remain unchanged.',
    native_main=native,native_hein=hein,scene_capture='MainScene01/Capture.json',
    dark_shape_diagnostic='MainHeinNoCharacter03 hides player skeletal meshes only; the large dark cloak disappears while particles remain. No additional particle or costume edits.',
    hein_scope='Natural Spin29 events/3 sections and boundary cleanup passed; collision suite passed. The broad suite subsequently failed an unrelated rear-Brutal B target fixture on this map; retained as a failure, not a full Hein suite pass.',
    work_native='SpinRefinedRHI05/Driver.json',
    colour_capture_module=read('VFXDevFinal03/Probe.json')['module_sha256'],
    colour_comparison='ColourFinal03/Comparison.json',colour_review='ColourComparison01/Review.json',
    colour_pairs=322,visible_both=colour['visible_in_both'],other_contexts=42,
    independent_random_and_physical_lighting_flags=14,
    spinning_colour_signature_angle_deg=0.0,spinning_energy_ratio=1.03663446,
    limitations=[
        'Art values are assistant TEMP tuning against supplied original photos, not original shader/light metadata.',
        'No original-game pixel parity, all-frame or Shipping FPS measurement is asserted.',
        '42 raw fixed-age systems require other times, parameters or interaction contexts.',
        'Native tonemapping, refraction and physically lit stone/ice response remain; universal VFX lighting bypass is not claimed.',
        'The 322-system comparison reuses the baseline current-reference catalogue plus the new Spin copy; concurrently added portal materials were checked separately by the preserved portal contract.'
    ],
    diagnostic_history=[
        'MainDelivery01 rejected changed Main map before any writes; MainDelivery02 preserves the newer map.',
        'MapRebaseAuthor01/02 superseded by current-schema, dependency-complete MapRebaseAuthor03 and RebasedSaved02.',
        'MainHeinSpin01 failed its unsaved early editor-world floor fixture before tests; MainHeinSpin02 warms physics first.',
        'MainHeinSpin02 broad CombatEffect failed after the completed natural Spin/boundary stages at the rear-Brutal target fixture. Main DevMap full regression is recorded separately.',
        'Earlier immediate readback and debug-overlay colour captures are superseded by the two Final03 captures.',
        'The initial protected ParticleLODLevel setter failed without saving; the final copy edits editable Required.Material only.'
    ],
    user_or_foreign_editor_controls=0,owned_final_editors_exited=True,
    screenshots=['Review/HeinMach_Before_After.jpg','Review/Spinning_Main_Sequence.jpg'])
(base/'FinalVerification.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
resume=dict(status=report['status'],remaining=[],final='FinalVerification.json',
    current_main_assets=current_rows,
    current_map_sha256=latest['current_map_sha256'],later_concurrent_revision='LatestMainRevision.json',
    next='Start from current Main and this final receipt for new requests. Do not rerun completed authors/deliveries, restore old private maps/Source/DLLs, or overwrite concurrent portal/monster/PlayerStart changes.',
    background_only=True,source_or_binary_delivery_required=False)
(base/'ResumeState03.json').write_text(json.dumps(resume,indent=2,ensure_ascii=False),encoding='utf-8')
(base/'MainDelivery01/Failure.json').write_text(json.dumps(dict(status='rejected_before_writes',
    reason='Current Main map changed from the preparation digest. Rebased onto that newer map before MainDelivery02.',
    main_asset_writes=0,final_delivery='MainDelivery02/Receipt.json'),indent=2),encoding='utf-8')

marker='<!-- HeinMachLookSpin_20261015_complete -->'
feature='Docs/Art/HEINMACH_BLUE_SPINNING_20261015.md'
common='Metadata/HeinMachLookSpin_20261015/FinalVerification.json'
feature_text="""
## 2026-10-15 — Main 반영·새 프로세스 실제 HeinMach 검수 완료

앞선 후보/전달 전 기록은 이 절로 대체한다. MainDelivery01은 작업 중 Main map SHA가 달라진 것을 감지해 쓰기 전에 거절했다. 최신 맵의 portal/arrival 및 몬스터 배치11개와 PlayerStart 변경을 보존하기 위해 현재 Main map으로 격리 사본을 다시 만들고, 현재 Main DLL schema와 신규 포탈 의존4asset을 작업본에만 복사했다. 최종 MapRebaseAuthor03은 Sun/Sky의 intensity·색, exposure bias, fog emissive의 소유 필드6개만 재적용했다. 과거 Work map이나 Source/DLL을 Main에 복원하지 않았다.

RebasedSaved02와 MainSaved01은 원래176 효과·clock/GUID·donor montage2·보호324 SHA와 새6/3/2쌍, Spin KZ_Slash 참조0을 통과했다. 기존 label별 pose10021개가 최신 Main 기준으로 동일하며 실제 actor 수는10022개다(고유 label 수와 구분). PortalPreservation/Readback은 portal/arrival의 transform·ExitPoint·Niagara/상대 yaw·범위·fade 값과 원본/전용 재질 계약을 다시 확인했다. MainDelivery02는 검토한 map/Spin montage/Spin-only PS의3개 SHA만 선택 전달했고 fresh 저장 검사도 동일하다.

MainScene01은 새 Main 프로세스의 Entry/ReferenceStart/OpenSky3 실제 game viewport다. 기존 Before와 동일한939×510 카메라·QA 품질에서 눈의 강한 흰빛이 줄고 푸른 눈길/그늘이 강화되는 것을 확인했다. 새 전역 필터/LUT/grade는 없고 BlueB TEMP 값은 위 표 그대로다. 발광 VFX의 기존 inverse-exposure/fog 격리를 유지했다. [실제 전후 화면](../../Metadata/HeinMachLookSpin_20261015/Review/HeinMach_Before_After.jpg).

MainHeinSpin02의 실제 HeinMach 자연 Spinning은29 events/3 sections와 boundary cleanup까지 완료했고 PlayerAttackCollision suite는 Success다. 넓은 CombatEffect suite는 그 뒤 rear-Brutal의 B 대상 선택 fixture에서 Fail이므로 전체 HeinMach 성공으로 기록하지 않는다. MainDevSpin01은 같은 현재 Main의 DevMap에서 CombatEffect(Spinning 선택+공유 수명/취소·승인 적중/Brutal)와 PlayerAttackCollision 두 suite가 Success다. 실제 로드 모듈은 표준 UnrealEditor-Khazan.dll SHA a8df6850908f08e84b6c8cc8a555c92d46b5c34ba75b136f9eac1b841a325069이며 Scene01과 같다. 작업 초기73fed225 격리 검사와 구분한다. 실제 자연 재생의 회전 초·중·마무리를 검수했고 붉은 OverFury/Charge 잔광은 보이고 회색 헬릭스 막은 사라졌다. 새 Source/Config/DLL 저작·전달/build0이며 데이터만 변경했다. [Main 회전 공격](../../Metadata/HeinMachLookSpin_20261015/Review/Spinning_Main_Sequence.jpg).

색 비교의 최신 정본은 VFXDevFinal03/VFXHeinFinal03 및 ColourFinal03이다. 두 맵322 system씩 모두 native 촬영 완료,280개는 양쪽 .2s 신호가 보이고42개는 다른 시간/대상/파라미터가 필요하다. 14 heuristic flag는 실제 support 범위·사진과 저장 재질을 대조해 무작위 입자 면적/밀도와 물리 조명 반응으로 분류했다. 새 Spin 사본은 RGB signature angle0°/영상 에너지 비1.03663446이다. QA 수치이지 원작 오차/튜닝 값이 아니다. DefaultLit 얼음·돌은 푸른 광원에 반응하며 native HDR/tonemapping/굴절까지 완전 우회했다고 주장하지 않는다. 원작 shader/pixel parity,42개의 조건별 전체 외관 및 Shipping FPS는 미확인이다. 동시 추가된 포탈은 이전321 catalogue에 소급 포함하지 않고 별도 saved 재질 계약으로 확인했다.

pause 직후 렌더 버퍼·빨간 VRAM 문구가 섞인 초기 촬영, 추가 row class key 실패, protected LOD setter 실패는 진단 기록으로 보존한다. Final03은 QA 메시지를 숨기고 simulation pause 뒤 렌더 완료를 기다려 촬영했다. MainHeinSpin01은 초기 editor physics 준비 전 바닥 fixture에서 저장0 실패했고,02는 warmup 뒤 실제 바닥을 사용했다. 게임 동작·재질을 잘못된 촬영/fixture에 맞춰 변경하지 않았다. 최종 QA 저장0/재질 compile fallback 실패0이며 작업 소유 에디터는 모두 정상 종료했다. Rider/다른 에디터 종료·저장·reload0이다.

최종 영수증은 Metadata/HeinMachLookSpin_20261015/FinalVerification.json, 재개는 ResumeState03.json이다. 이 요청의 필수 미전달/미검증 대기는 없고 위의 검증 한계는 유지한다. 새 요청은 현재 Main/해당 saved report부터 시작하며 완료 author/refine/delivery, 전체 추출·이전 Work map/Source/DLL 복원을 반복하지 않는다.
"""
feature_text+='\n\n회전 후기의 큰 검은 면은 MainHeinNoCharacter03에서 player skeletal mesh만 숨기자 사라져 캐릭터 망토로 확인됐다. 비교는 Review/Spinning_Character_Isolation.jpg이며, 이 진단을 이유로 particle나 costume를 추가 수정하지 않았다.\n'
feature_text+='\n최종 쓰기 후 Main map이 동시 저장되어 SHA가 ff7c68d9...에서7b072b9b...로 바뀌었다. MainLatest01은 poses10021/전체 montage3·light/fog/PP가 MainSaved01과 동일함을 확인했고 MainLatestSaved02는 현재 저장본과 포탈 계약을 다시 통과했다. 최신 파일을 보존했으며 이전 전달 바이트로 되돌리지 않았다. 최종 현재 SHA와 전달 시점 SHA는 LatestMainRevision.json 및 FinalVerification.json에 분리했다. 새 게임 에셋 쓰기나 회귀 반복은 없었다.\n'
entries={
feature:feature_text,
'Docs/Art/HEINMACH_COLOUR_VFX_20261015.md':"""
## 2026-10-15 — 후속 어두운 BlueB 룩 반영

사용자 후속 요청으로 이전 exposure bias−1.1/태양1800lux 등 장면 TEMP 값은 HEINMACH_BLUE_SPINNING_20261015.md의 BlueB 표(−2.15EV/1000lux/푸른 direct·sky 및 fog emissive)로 대체됐다. 기존 혈흔/피격/95 VFX root와 화면 필터 제거 결과는 보존한다. 새 전역 색보정은 없고 후속 Final03 native 색 비교의280 가시/42 조건 필요, 물리 조명·굴절 응답 한계를 따른다. 이전105개 전달을 반복하지 않았다. 최신 맵의 포탈/몬스터·PlayerStart를 유지한3개 선택 전달과 실제 Main 검수의 정본은 Metadata/HeinMachLookSpin_20261015/FinalVerification.json이다.
""",
'Docs/Art/PLAYER_ATTACK_VFX_PLAYBACK_20261008.md':"""
## 2026-10-15 — SpinningAttack의 KZ_Slash 제외 완료

사용자 최신 지시로 Spinning의 여섯 추가 KZ_Slash 쌍을 OverFury 전용 사본6쌍으로 교체하고 Charge streak3/vortex2쌍을 더했다. 원래176 효과/Notify clock·GUID·공격/오디오와 다른 montage는 유지한다. 이전 다섯 montage 바깥 배치 절의 Spinning Niagara 연결만 이 최신 데이터로 대체된다. 원작 Spin window 재사용과 TEMP donor 조합/scale의 구분, Helix2 회색 면 제외와 실제 Main HeinMach의 자연 재생·수명/취소·충돌2 suite Success는 HEINMACH_BLUE_SPINNING_20261015.md 및 Metadata/HeinMachLookSpin_20261015/FinalVerification.json을 따른다. 공유 KZ_Slash/OverFury PS는 수정하지 않았다.
""",
'Docs/Art/ART_PROJECT_STATE.md':"""
## 2026-10-15 — HeinMach BlueB·Spinning 표현 Main 완료

HeinMach 노출 보정을−1.1→−2.15EV로 낮추고 TEMP 청회색 direct/sky/fog를 적용했다. 새 화면 필터 없이 발광 VFX 역노출 보상을 유지한다. Spinning KZ_Slash0, OverFury 사본6/Charge3+2 조합과 Helix 회색 면 제외를 Main3 asset에 반영했다. 동시 포탈/몬스터/PlayerStart를 최신 map 기준으로 보존했다. saved 검사·Main DevMap 두 suite·HeinMach 실제3시야/회전 공격·충돌 검수 완료다. HeinMach broad suite의 별도 rear-Brutal fixture 실패는 통과로 재명명하지 않는다. 원작 shader/pixel/Shipping 및42조건 한계는 유지한다. 정본 HEINMACH_BLUE_SPINNING_20261015.md, Metadata/HeinMachLookSpin_20261015/FinalVerification.json. 필수 잔여0이다.
""",
'Docs/Art/ART_KNOWLEDGE_INDEX.md':"""
## 2026-10-15 — BlueB·Spin donor 조합 재사용 근거

HEINMACH_BLUE_SPINNING_20261015.md와 Metadata/HeinMachLookSpin_20261015/{FinalVerification,MainDelivery02/Receipt,MainSaved01/Verification,ColourFinal03/Comparison}.json을 우선한다. Source timing은 기존 CombinedPlaybackWindows.csv를 재사용하고 새 source 전수조사는 없다. OverFury의 FS_Spline_Helix_08 mesh 두 emitter가 회전 합성에서 회색 막을 만들었고, Spin-only PS의 Required.Material2 교체로 해결했다. shared321+donor/DevMap/KZ_Slash 총324 SHA 유지, 원래176 effects 보존이다. Native pause 촬영은 render-settle와 QA screen message 숨김이 필요하며 기존 실패 촬영은 최종 색 근거가 아니다.
""",
'Docs/Art/ART_WORK_CONTINUITY.md':"""
## 2026-10-15 — HeinMach Blue/Spinning 최종 완료·재개 기준

앞선 renderer corrected pending 및 Main 쓰기0 기록은 완료로 대체한다. MainDelivery01은 최신 map 충돌을 쓰기 전에 거절했고, 현재 schema/새 포탈 의존4개를 Work에만 보완해 MapRebaseAuthor03→RebasedSaved02→MainDelivery02의3개 선택 전달을 완료했다. MainSaved01의 portal/arrival·새 몬스터·PlayerStart 보존, MainScene01 실제3시야, MainHeinSpin02의 실제 HeinMach 공격 초·중·후기/cleanup·충돌과 MainDevSpin01의2 suite 및 Final03 두 맵322씩을 검수했다. HeinMach broad suite의 별도 rear-Brutal fixture 실패는 그대로 보존한다. 외부 editor 제어0, Source/Config/DLL 전달0이다.

정확한 현재 상태는 Metadata/HeinMachLookSpin_20261015/FinalVerification.json 및 ResumeState03.json. 필수 잔여=[]이며 원작 pixel/shader·Shipping FPS·42개 다른 조건의 외관은 별도 한계다. 물리 조명/굴절 반응까지 VFX 완전 우회를 주장하지 않는다. 다음 요청은 현재 Main과 final receipt부터 시작한다. MainDelivery01/완료 author/refine/전체 추출이나 과거 private map/Source/DLL 복원을 재실행하지 않는다. 이전 실패·중단·촬영 오류는 보존하며 원래 Rider/foreign 에디터에는 손대지 않았다.
""",
'Docs/Engineering/COMBAT_PRESENTATION_FOLLOWUP_20261011.md':"""
## 2026-10-15 — ARCH-83/95 Spinning 표현 데이터 Main 완료

기존 Action/CombatEffect batch/receipt·정상/취소 cleanup을 그대로 사용했다. Spinning montage에서 KZ_Slash6쌍을 OverFury 전용 PS로 바꾸고 Charge3+2쌍을 조합했다. 원래176 효과·clock/GUID·donor montage/피해/HP/ST/입력/오디오·GAS 수명은 보존한다. 새 runtime file/class/manager/component/state0, 이번 Source/Config/DLL 저작·전달/build0이다. 실제 Main DevMap의 Khazan.CombatEffect.PIE(Spinning 선택+공유 회귀) 및 PlayerAttackCollision 두 suite가 Success이며 새 Main 모듈a8df6850...에 결속했다. HeinMach 자연 Spin/cleanup·충돌은 확인했고 broad suite의 이후 rear-Brutal fixture 실패는 보존했다. 타 세션 Source/진동/포탈 기능을 이 작업으로 복원하거나 별도 검증했다고 표현하지 않는다. 외관/TEMP/두 material만 다른 전용 PS와 최종 근거는 Art HEINMACH_BLUE_SPINNING_20261015.md 및 Metadata/HeinMachLookSpin_20261015/FinalVerification.json이다.
""",
'Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md':"""
## 2026-10-15 — ARCH-83/95 Spinning 표현 교체 완료

기존 montage data-only CombatEffect와 Action 실행/수명·적중·취소 계약으로 해결했으며 새 gameplay owner/State/태그/manager/runtime 파일을 추가하지 않았다. 원래176 효과·clock/GUID·피해/입력/오디오와 공유 donor는 유지한다. Main3 presentation asset 선택 전달, 실제 HeinMach Spinning/cleanup·충돌과 Main DevMap 두 회귀 suite 검사가 완료됐다. HeinMach broad suite의 별도 rear-Brutal fixture 실패는 통과로 확대하지 않는다. 이 요청의 Source/Config/DLL/build 변경0이다. 계약 변경 없이 Art의 TEMP donor 조합만 달라졌고 원작의 내부 구조/수치로 표현하지 않는다. Metadata/HeinMachLookSpin_20261015/FinalVerification.json과 Art HEINMACH_BLUE_SPINNING_20261015.md가 최종 근거다.
""",
'Docs/Engineering/ENGINEERING_PROJECT_STATE.md':"""
## 2026-10-15 — HeinMach/Spinning asset-only 후속 완료

기존 ARCH-83/95 CombatEffect 데이터만 사용해 Main3 asset을 반영했다. 신규 gameplay Source/Config/DLL/build0, 기존176 효과·clock/GUID·공격/입력/오디오 보존이다. MainSaved01과 실제 MainDevSpin01의2 suite Success, HeinMach 자연 Spin/cleanup·충돌 확인, 별도 rear-Brutal fixture 실패, 포탈 저장 계약 보존 및 actual modulea8df6850...는 Metadata/HeinMachLookSpin_20261015/FinalVerification.json에 있다. 다른 세션의 진동 장치 검증/포탈 재구현을 이번 범위에 포함하지 않는다. 외관·TEMP는 Art 정본, 필수 잔여0이다.
""",
'Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md':"""
## 2026-10-15 — Spinning 데이터 교체 Main 최종 완료

앞선 Main 미반영/Final03 진행 중 기록을 완료로 대체한다. MainDelivery02의3개 선택 전달, MainSaved01의 현재10022 actor/10021 label pose·포탈 계약 보존, 실제 Main DevMap CombatEffect(Spin 선택+공통 cleanup 회귀)/PlayerAttackCollision 두 suite가 Success다. HeinMach는 자연 Spin29event/3section·boundary cleanup/충돌을 완료했고 이후 rear-Brutal B fixture 실패는 그대로 남긴다. 현재 실제 module SHA는a8df6850908f08e84b6c8cc8a555c92d46b5c34ba75b136f9eac1b841a325069로 초기 Work73fed...와 구분한다. 이번 신규 Source/Config/DLL 저작·전달/build0이며 현재 사용자/동시 변경을 보존했다.

재개 기준은 Metadata/HeinMachLookSpin_20261015/FinalVerification.json→ResumeState03.json 및 Art feature 정본이다. 필수 잔여=[];42개 조건별 외관/원작 shader·pixel/Shipping FPS는 검증 한계다. MainDelivery01 충돌은 쓰기 전 거절/최신 map 재적용으로 해결했다. MainHeinSpin01은 준비 전 QA 바닥 fixture(save0) 실패이고02에서 warmup 뒤 실제 바닥으로 검사했다. 완료 author/delivery/전체 source·DLL/old Work map 복원을 반복하지 않는다. 사용자/Rider/foreign editor 제어0, 모든 final own editor 정상 종료다.
""",
'0_DOCUMENT_ROUTER.md':"""
## 2026-10-15 — HeinMach BlueB와 Spinning donor 표현 후속

노출 추가 감소·푸른 조명/안개와 Spinning의 KZ_Slash 교체는 Art의 HEINMACH_BLUE_SPINNING_20261015.md → Metadata/HeinMachLookSpin_20261015/FinalVerification.json을 우선한다. 기존 CombatEffect 수명/판정 검증은 Engineering COMBAT_PRESENTATION_FOLLOWUP_20261011.md 최신 완료 절을 따른다. 기존 HEINMACH_COLOUR_VFX의 장면 TEMP 값만 BlueB로 대체하며 혈흔·VFX 재질 보상은 유지한다. 최신 Main의 포탈/몬스터·PlayerStart를 보존한3 asset 선택 전달과 실제 Main 검사가 완료됐다. 이전 Work map/Source/DLL 일괄 복원·완료 author 재실행은 하지 않는다.
"""
}
player_doc='Docs/Art/PLAYER_ATTACK_VFX_PLAYBACK_20261008.md'
entries[player_doc]=entries[player_doc].replace('실제 Main HeinMach의 자연 재생·수명/취소·충돌2 suite Success',
    '실제 HeinMach 자연 재생·cleanup·충돌 및 Main DevMap2 suite Success')
entries[player_doc]+='\n\nHeinMach broad suite의 이후 rear-Brutal fixture 실패는 보존했으며 전체 HeinMach suite 성공으로 기록하지 않는다.\n'
for rel,body in entries.items():
    if rel.endswith('WORK_CONTINUITY.md'):
        body+='\n\n추가 동시 저장본은 MainLatest01에서 poses/montage/light/fog/PP 동일, MainLatestSaved02에서 현재 저장·포탈 계약을 확인해 보존했다. 최종 현재 map SHA는7b072b9bfd8c051701fa8190fb794422e33c4c1bd16c62a2370ce1831471c728이며 이전 전달 SHA와 구분한다. 최신 파일을 옛 전달 바이트로 복구하지 않는다.\n'
    path=main/rel;assert path.exists(),rel
    assert marker not in path.read_text(encoding='utf-8'),rel
    with path.open('a',encoding='utf-8',newline='') as stream:stream.write('\n\n'+body.strip()+'\n\n'+marker+'\n')
print('LOOK_SPIN_COMPLETED',len(delivery['rows']),len(entries))
