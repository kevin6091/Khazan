"""Record applied changes and their actual validation, preserving older domain notes."""
from pathlib import Path
import datetime
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/ImportReports/HeinMachGhosting_20261008'
def read(name):return json.loads((OUT/name).read_text(encoding='utf-8'))
main=read('MainDelivery.json');fresh=read('FreshRuntimeVerification.json');config=read('FreshConfigAudit.json')
assert main['success'] and fresh['success'] and config['success']
viewport=read('MainViewportReadback.json')
assert viewport['success'] and viewport['after']['r.Editor.Viewport.ScreenPercentage']==100
marker='<!-- HeinMachGhosting_20261008_applied -->'
title='## 2026-10-08 — HeinMach 이동 캐릭터 선명도·잔상 수정'
reference=r'''
현재 Main3528은 내부 해상도87%, sg.AntiAliasingQuality2, TSR history100%, velocity weight-clamp sample4였다. AA2는 UE의 High 그룹이며, 이전 세션의 Epic3/100%가 계속 유지된 상태는 아니었다. 8개 PP volume은 이미 motion-blur override0이고, regional look은 BL_SCENE_COLOR_BEFORE_DOF였다. 이번에 다시 blur/DOF를 원인으로 단정하거나 기존 pass 수정을 반복하지 않았다.

실제 입력으로 실행한 BP_Player는 본체만 CustomDepth=True/Stencil254였고 Original Torso/Shoes/Leg/Hair/Arm 및 양쪽 무기는 False/0이었다. 따라서 현재 PP가 visible 의상·무기 표면과 본체를 서로 다른 character/world shading 및 outline 분기로 분류하는 구체적인 불일치가 있었다. 이 계약은 원작 stencil 값의 복원이 아니라 기존 native 룩의 캐릭터 예약값이다. 기존 template7에 True/254만 복원했다. 에셋·Config 변경의 세부 책임은 Engineering의 SOURCE_BP_CONFIG_ARCHITECTURE 이번 절을 따른다.

원작 shader 수치가 아닌 명시적 native 튜닝: r.TSR.Velocity.WeightClampingSampleCount4→2. 설치 UE5.8 Renderer/Private/PostProcess/TemporalSuperResolution.cpp의 해당 CVar 설명은 값이 클수록 움직임이 흐려지며 선명도에2를 제시한다. native100 viewport/PIE를 프로젝트 DefaultEditor에 저장했다. AA2/history100은 유지했고 Epic history200을 전달하지 않았다. history200은 각 축2배라 history 픽셀 수4배이며, 이번 해결에 필요하다고 검증되지 않았다. count2 설정은 프로젝트의 TSR 전체에 적용된다. 해상도87→100은 내부 픽셀 수가 1/(0.87²), 약1.321배가 되는 비용이 있다. 이를 FPS 향상으로 표현하지 않는다.

검증은 hidden private real-RHI game의 EnhancedInput action 주입→기존 PlayerController/CMC/GAS→실제 ABP/weak attack montage 경로다. single-node pose/SceneCapture/HighResShot 비교가 아니다. baseline87/AA2/count4, native100/AA2/count4, native100/AA2/count2, native100/AA3/count2, native100/AA2/count2/parts254의5조건을 각각200프레임/13사진으로 관측했다. 모든 조건에서 실제 이동과 공격 montage를 확인했고 TSR history100은 동일하게 유지했다. 정성적으로 native100/짧은 history/통일된 mask 쪽의 의상·무기 경계가 선명해졌다. 물리의 시간 누적·눈 파임·노출 차이가 있어 이미지 차이를 정량적 ghosting 점수나 완전한 동시 pose 비교로 사용하지 않는다. sample tick 평균은37.68/37.67/37.85/38.12/38.72ms였으며 dual-editor·30FPS 제한·Shot 계측이 포함돼 제품 성능 벤치마크가 아니다.

추가 실제 velocity/reprojection viewport와 regional PP on/off를 확인했다. 캐릭터 전체의 공통 velocity 누락을 근거로 per-bone velocity/CopyPose/의상 physics를 비활성화하지 않았다. r.MotionVectorSimulation0은 camera-cut simulation 기본값이며 이를 general skeletal velocity-off로 오인하지 않는다. UE5.8의 미등록 r.PostProcessAAQuality 조회0도 AA-off 근거로 사용하지 않는다. per_bone_motion_blur=True/URO=False/AlwaysTickPoseAndRefreshBones 및 독립 CopyPose/RigidBody를 보존했다. 빠른 masked hair·모든 전투 pose에서 잔상0/원작과 동일함까지 검증한 것은 아니다.

증거: Saved/ImportReports/HeinMachGhosting_20261008의 RuntimeProbe/MaterialProbe/MainReadOnly, Parts authorReport/auditReport/FreshConfigAudit, Captures/20261007T221643_574561Z/CaptureMetadata, VelocityCapture, MainDelivery, FreshRuntimeVerification.json. 실패한 delegate-handle JSON 기록은 계측 cleanup을 수정했고, BG game의 Main BP 파일 잠금은 해당 소유 game만 정상 종료해 해제한 뒤 선택 전달했다. 실패 기록 MainDelivery_BackgroundGameLock.json을 보존했다. 사용자 editor3528의 dirty content/map0를 확인한 후 BP_Player package만 fully_load/reload했으며 map save/reload·PIE·close는 하지 않았다.

Main canonical/Contact55 preview map 및 Snow source·module manifest SHA를 유지했다. 기존 Contact55 worker2256의 canonical 대기 작업을 이번 ghosting 수정의 미완료로 합치지 않는다. 작업 결과는 Main 적용/선택 reload 및 별도 fresh runtime 검증 완료다. 재검사는 별도 background 게임에서 heinmach_ghosting_game.py의 새로운 pid/session mailbox를 사용하고 actual-input 캡처를 실행한다. 기존 user editor를 capture 대상으로 사용하지 않는다.
'''
engineering=r'''
실제 Main 적용은 BP_Player.uasset의 Original5+weapon2 SCS render_custom_depth=True/custom_depth_stencil_value254, Config/DefaultEngine.ini 기존 SystemSettings의 r.TSR.Velocity.WeightClampingSampleCount2, Config/DefaultEditor.ini의 EditorPerformanceProjectSettings Realtime/NonRealtime mode=Manual 및 ManualScreenPercentage100이다. 새 runtime 파일·class·helper·C++ 변경·빌드는0이다. existing native mask 계약만 복구하며 body·mesh·ABP·PhysicsAsset override·CopyPose/RigidBody·tick·URO·visibility·scale·per-bone motion blur를 보존했다. count2/native100은 원작 근거 미확인의 native 튜닝이며 선정/비용/검증은 Art HEINMACH_REFERENCE_MATCH_2026-10-06.md 이번 절에 기록했다.

저장은 private Parts stage에서 BP만 수행하고 fresh-process asset audit를 통과했다. Main3528에서 PIE없음·dirty content/map0·현재 HeinMach world를 확인, Main BP SHA ce037c64d7af2e85d61f8e2d7160f7ad615f3fc5be4c159f0bc1d3b585be70f5를 CAS 기준으로 전달 SHA76a65789f117d72913168e4c5f55da1a258f8ae0e6a3466595f8318467f2cfa4로 교체했다. BP package만 fully_load/reload(return True/빈 오류)한 뒤 본체 포함8template True/254와 dirty0를 readback했다. 사용자 map·actor path·선택 및 Snow h/cpp·module manifest는 보존했다. first attempt는 소유 background game이 Main BP를 junction으로 읽어 file lock이 있었으며, 해당 game만 정상 종료 후 성공했다. 전역 DEBUG RESETLOADERS나 user editor 종료/PIE/save는 사용하지 않았다.

DefaultEditor는 프로젝트 전용 config다. engine 공용 AppData EditorPerformanceSettings/Scalability를 저장하지 않았다. 현행 user session은 r.ScreenPercentage/sg.ResolutionQuality100 및 count2만 즉시 적용했고 sg.AntiAliasingQuality2/history100은 유지했다. Fresh hidden NullRHI editor는 console setter 없이 새 config의 manual100·realtime/nonrealtime Manual·TSR count2와 user override 조건을 검증했다. 새 real-RHI game에서는 저장된 BP의8component254, 실제 EnhancedInput 이동/weak montage, per-bone velocity·Original5 animation class를 다시 확인했다. fresh 증거는 Saved/ImportReports/HeinMachGhosting_20261008/Parts/FreshConfigAudit.json 및 FreshRuntimeVerification.json이다. 일반 게임의 user 선택 resolution/AA 품질은 강제 고정하지 않는다. 프로젝트 전체 TSR count2의 적용 범위는 명시적으로 공통이다.

이번 delivery는 canonical HeinMach map/Contact55 preview map/보호된 snow source3/QA alias manifest를 바꾸지 않았다. Contact55의 기존 canonical pending CAS 조건은 유지된다. physics 전체 관통 제거나 모든 공격 pose의 temporal artifact0 검증은 별도 미확인 범위다.
'''
short_art='실제 변경·원인·원작 수치와 native 튜닝 구분·RHI 비교·검증 한계는 HEINMACH_REFERENCE_MATCH_2026-10-06.md의 이번 절을 따른다. native100/TSR 이동 누적2와 캐릭터 파츠 mask 복원이 Main 적용/선택 reload·fresh runtime 검증됐다. 기존 PP BeforeDOF/blur0·의상 물리·Snow canonical pending 작업을 보존했다.'
short_eng='SOURCE_BP_CONFIG_ARCHITECTURE.md의 이번 절을 따른다. 변경은 BP_Player template7의 기존254 mask 복원과 프로젝트 Config2이며 runtime Source/build0이다. Main3528 선택 reload 후8template254/dirty0 및 fresh saved-config·actual-input runtime 검증 성공. Original5 CopyPose/RigidBody·PA2, 열린 HeinMach map 및 Snow canonical pending guard를 보존했다.'
notes={
 'Docs/Art/HEINMACH_REFERENCE_MATCH_2026-10-06.md':reference,
 'Docs/Art/ART_PROJECT_STATE.md':short_art,
 'Docs/Art/ART_KNOWLEDGE_INDEX.md':'재사용 근거는 Saved/ImportReports/HeinMachGhosting_20261008이다. MainDelivery/FreshRuntimeVerification와 Parts/FreshConfigAudit가 최종 증거이며 actual-input5조건65사진은 Captures/20261007T221643_574561Z에 있다. 상세는 Art reference-match 정본 이번 절과 Engineering Source/BP/Config 정본으로 분리 기록했다.',
 'Docs/Engineering/SOURCE_BP_CONFIG_ARCHITECTURE.md':engineering,
 'Docs/Engineering/ENGINEERING_PROJECT_STATE.md':short_eng,
 'Docs/Engineering/PLAYER_ORIGINAL_PARTS_PHYSICS_20261007.md':'HeinMach 잔상 수정에서 BP_Player의 Original5/weapon2 render mask만 기존 body의 True/254에 맞췄다. Independent CopyPose/RigidBody·PA2·tick·scale·skeletal velocity는 바꾸지 않았다. mesh·ABP·PhysicsAsset override·transform 비교와 fresh saved audit는 Saved/ImportReports/HeinMachGhosting_20261008/Parts에 있다. physics tuning 결과를 shader ghosting 완전 해결의 근거로 사용하지 않는다. Main 선택 전달·Config·fresh actual-input 검증은 SOURCE_BP_CONFIG_ARCHITECTURE.md 이번 절을 따른다.',
}
for relative,body in notes.items():
    body=body.replace('Parts/FreshConfigAudit','FreshConfigAudit').replace('Parts authorReport/auditReport/FreshConfigAudit','Parts authorReport/auditReport 및 FreshConfigAudit')
    path=ROOT/relative
    if marker not in path.read_text(encoding='utf-8'):
        with path.open('a',encoding='utf-8',newline='\n') as handle:handle.write('\n\n'+marker+'\n'+title+'\n\n'+body.strip()+'\n')
viewport_marker='<!-- HeinMachGhosting_20261008_viewport_readback -->'
viewport_note='최종 현재 뷰포트 readback 보완: 에디터 전용 real-time mode1/display-resolution 및 non-real-time mode2/DPI도 현재 세션에서 Manual0으로 바꿨다. r.ScreenPercentage100만으로 에디터의 별도 resolution driver가 Manual이 됐다고 가정하지 않았다. r.Editor.Viewport.ScreenPercentageMode.RealTime0/NonRealTime0/ScreenPercentage100 및 TSR count2를 Main3528에서 확인했다. AppData 전역 사용자 config를 저장하지 않았고 dirty0/noPIE·현재 world를 유지했다. MainViewportReadback.json이 증거다. 재시작은 프로젝트 DefaultEditor로 동일하게 검증됐다.'
for relative in ['Docs/Art/HEINMACH_REFERENCE_MATCH_2026-10-06.md','Docs/Engineering/SOURCE_BP_CONFIG_ARCHITECTURE.md']:
    path=ROOT/relative
    if viewport_marker not in path.read_text(encoding='utf-8'):
        with path.open('a',encoding='utf-8',newline='\n') as handle:handle.write('\n\n'+viewport_marker+'\n## 2026-10-08 — 현재 에디터의 별도 해상도 driver 확인\n\n'+viewport_note+'\n')
final=dict(success=True,main_applied=True,main_selective_reload=True,fresh_config_verified=True,fresh_runtime_verified=True,current_viewport_native100_verified=True,
    runtime_source_files_changed=0,other_map_and_physics_preserved=True,
    changes=['Config/DefaultEngine.ini','Config/DefaultEditor.ini','Content/_Art/Player/Character/Bluprints/BP_Player.uasset'],
    validation_limits='Qualitative real-input viewport comparison; no claim of zero artifacts in every pose or recovered original shader fidelity.',
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),docs=list(notes))
(OUT/'FinalVerification.json').write_text(json.dumps(final,indent=2),encoding='utf-8')
print(json.dumps(final,indent=2))
