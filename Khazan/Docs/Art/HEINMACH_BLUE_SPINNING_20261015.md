# HeinMach의 어두운 푸른 룩과 SpinningAttack 효과

## 2026-10-15 — 원작 사진 대조·격리 후보 검수

사용자의 후속 지시는 이전 HeinMach보다 노출을 더 낮추고 푸른 분위기를 강화하되 VFX 색은 유지하는 것이다. SpinningAttack에서는 KZ_Slash를 제외하고 OverFury/ChargeAttack의 기존 효과를 많이 차용한다. 이전 완료 작업을 재추출·재저작하지 않고 현재 Main과 저장 metadata에서 시작했다. 근거는 Metadata/HeinMachLookSpin_20261015이다. 이 절 작성 시 Main은 아직 미반영이며 최종 적용은 하단 완료 절로 구분한다.

### 룩 판단과 수치의 출처

Docs/Art의 HeinMach 원작 사진5장과 Saved/ImportReports/HeinMachReference_20261006/OriginalReferences.jpg를 재사용했다. 사진은 위치·영상 버전·조명 조건이 서로 다르다. 사용자가 요구한 푸른 분위기는 어두운 튜토리얼 동선의 HeinMach 원작.png를 우선 대조했다. 현재 Main은 밝은 눈/직접광과 거의 검은 바위의 대비가 강하고 푸른 그늘이 약했다. 원작 사진을 원작 광원/HDR 셰이더 수치로 역산했다고 표현하지 않는다.

LookTrials01은 같은 실제 game viewport, 카메라2곳, 품질·settling에서 현재 룩과 BlueA/B/C를 비교한 저장0 PIE 시험이다. BlueB를 선택했다. 모든 새 수치는 원작 직접값이 아닌 **TEMP 미술 튜닝**이고 기존 소유자의 Details에서 조정한다.

| 소유자·필드 | 시작 Main 값 | 선택 BlueB | 의도·단위 |
| --- | --- | --- | --- |
| Art_NaturalLighting_HeinMach.AutoExposureBias | −1.1 | −2.15 | TEMP EV. 이전보다 보상 −1.05 EV |
| HM_PreviewSun.Intensity | 1800 | 1000 | TEMP lux. 직접광과 눈의 강한 밝은 면 완화 |
| HM_PreviewSun.LightColor | R205/G225/B255 | R150/G186/B255 | TEMP sRGB8. 차가운 직접광 |
| HM_PreviewSkyLight.Intensity | 8 | 10 | TEMP 환경광 배율. 그늘의 읽힘을 유지 |
| HM_PreviewSkyLight.LightColor | R195/G218/B255 | R108/G157/B255 | TEMP sRGB8. 푸른 그늘 강화 |
| HM_PreviewVolumetricFog.VolumetricFogEmissive | linear .025/.04/.06 | linear .010/.024/.050 | TEMP 약한 차가운 자체발광. 밀도/높이/시작 거리 보존 |

명시한 FColor는 Python 이름 인자 r/g/b/a로 기록해 BGR 위치 인자 오류를 피한다. 기존 histogram 범위·적응 속도, Sky/SkyLight capture 정책, 나머지 지역/횃불 광원과 배치, 안개50장·캐릭터/환경 재질은 보존한다. 새 전체 화면 필터/LUT/색보정은 추가하지 않는다. 이전 custom blendable0과 LocalExposure 중립1을 유지한다.

LookTrials01의 실제939×510 중 눈길 ROI (350,260)–(580,400)의 sRGB8 평균은 Before R166.97/G176.74/B186.05에서 BlueB R108.47/G138.65/B170.22로 바뀌었다. 이는 특정 시야의 관측이고 전체 맵·원작 일치·선형 노출 배율의 측정은 아니다. 움직이는 눈/횃불도 두 프레임 사이 달라진다.

### Spinning의 실제 조합과 최소 수정

기존 AM_DAS_Player_SpinningAttack의 여섯 KZWeaponSlash start/end쌍에서 KZ_Slash 연결을 제외하고 기존 CombatEffect batch/정상·취소 cleanup을 재사용했다. 공격·section/애니메이션 clock/GUID·피해/오디오·원래 효과176객체는 보존한다. 새 runtime class/component/manager/파일은 없다.

| 레이어 | 재사용 리소스 | 쌍 수 | 배치·수치 출처 |
| --- | --- | --- | --- |
| 붉은 OverFury 궤적 | FP_Kazan_DualaxeSword_Overfury_slash_01의 Spin 전용 사본 PP_Spinning_OverFury_Accent | 6 | 기존 Spin의 socket/위치·회전/시작·종료. XY1.12/Z1은 TEMP |
| 차지 잔광 | FP_PlaneSlash_Flow_Strong | 3 | 원래 Spin window c85f84be/1e4b39e6/df5d8525. 균일1.08은 TEMP |
| 차지 소용돌이 | FP_Kazan_Dualaxesword_flow_burst_01 | 2 | 원래 Spin window c85f84be/a6066b61. Bip001/위치·회전0/균일1.2는 TEMP |

원래 source clock의 출처는 Saved/ImportReports/PlayerAttackVFX_20261008/CombinedPlaybackWindows.csv의 SpinningBeast_Start/Finish와 Properties.Notifies[27/28/39/11/23/32]다. montage window는 약 .336402–.484797, .407993–.634570, .545927–.869173, 1.018174–1.145962, 1.150273–1.278226, 1.281659–1.432314초이며 이번에 옮기거나 늘리지 않았다. 이 값은 이전 원본→현행 시간 매핑의 재사용이고 새 TEMP 타이밍이 아니다. 다른 공격의 효과를 Spin에 조합한 연출·scale/anchor는 원작 Spin 직접 재현값으로 표현하지 않는다.

첫 합성 후보에서 각진 회색 면이 드러나 원래 Spin/추가 ChargeStreak/ChargeVortex를 각각 임시 제외하는 저장0 격리 검사를 했다. 이들만 제외해도 면이 남았다. DonorLayers01은 OverFury 내부 SLASH_MASK_1/SLASH_2가 FS_Spline_Helix_08을 사용하는 것을 확인했다. 공유 OverFury PS를 고치면 다른 공격에도 영향을 주므로 PS 하나만 Spin 전용으로 복사했다. 두 Required.Material만 기존 zero-output M_KZGiant_TechnicalHidden으로 바꿨다. 다른 module/곡선/입자 수/수명·sprite/GPU/주 슬래시와 원본 PS는 보존한다.

SpinRefinedRHI05의 같은 공격에서 회색 막이 사라지고 붉은 궤적·차지 잔광은 남는 것을 확인했다. CandidateSaved02는 복사본을 원본과 경로/이름 정규화해 비교하고 정확히 두 material reference만 다른 것을 검증했다. 초기 ParticleLODLevel.bEnabled 직접 setter는 protected라 저장0 실패했으며 그 방법을 사용하지 않았다. 실제 해결은 editable Required.Material의 선택 변경이다. 공유 재질/texture/mesh와 원래 particle321은 변경하지 않았다.

### 검증 상태와 다음 절차

CandidateSaved02는 actor10010 pose 변화0, 원래 효과176 객체·clock/GUID·donor montage2 보존, Spin KZ_Slash 참조0, 새11 start/end쌍 일치와 보호324 package SHA를 통과했다. SpinRefinedRHI05의 실제 Khazan.CombatEffect.PIE(Spinning 선택 + 기존 수명/취소/적중·브루탈 공통 회귀) 및 Khazan.Combat.PlayerAttackCollision.PIE가 Success다. 전체18 node 외관을 이번 선택 검사로 검증했다고 확대하지 않는다.

현재 기존321 + 새 Spin 전용 PS1의 두 맵 native 색 비교와 Main3 선택 전달/새 프로세스 검증이 남아 있다. VFXDev01의 기존321 촬영 뒤 추가 row의 class key 오류 및 VFXHein01의 own-process 중단은 실패 진단으로 남긴다. 수정 후 Dev02/Hein02의 완전한322 결과를 최종 근거로 사용한다. 원래 user/Rider/foreign editor를 제어하지 않는다. 정확한 재개는 같은 metadata root의 최신 ResumeState와 완료 영수증을 따른다.


## 2026-10-15 — Main 반영·새 프로세스 실제 HeinMach 검수 완료

앞선 후보/전달 전 기록은 이 절로 대체한다. MainDelivery01은 작업 중 Main map SHA가 달라진 것을 감지해 쓰기 전에 거절했다. 최신 맵의 portal/arrival 및 몬스터 배치11개와 PlayerStart 변경을 보존하기 위해 현재 Main map으로 격리 사본을 다시 만들고, 현재 Main DLL schema와 신규 포탈 의존4asset을 작업본에만 복사했다. 최종 MapRebaseAuthor03은 Sun/Sky의 intensity·색, exposure bias, fog emissive의 소유 필드6개만 재적용했다. 과거 Work map이나 Source/DLL을 Main에 복원하지 않았다.

RebasedSaved02와 MainSaved01은 원래176 효과·clock/GUID·donor montage2·보호324 SHA와 새6/3/2쌍, Spin KZ_Slash 참조0을 통과했다. 기존 label별 pose10021개가 최신 Main 기준으로 동일하며 실제 actor 수는10022개다(고유 label 수와 구분). PortalPreservation/Readback은 portal/arrival의 transform·ExitPoint·Niagara/상대 yaw·범위·fade 값과 원본/전용 재질 계약을 다시 확인했다. MainDelivery02는 검토한 map/Spin montage/Spin-only PS의3개 SHA만 선택 전달했고 fresh 저장 검사도 동일하다.

MainScene01은 새 Main 프로세스의 Entry/ReferenceStart/OpenSky3 실제 game viewport다. 기존 Before와 동일한939×510 카메라·QA 품질에서 눈의 강한 흰빛이 줄고 푸른 눈길/그늘이 강화되는 것을 확인했다. 새 전역 필터/LUT/grade는 없고 BlueB TEMP 값은 위 표 그대로다. 발광 VFX의 기존 inverse-exposure/fog 격리를 유지했다. [실제 전후 화면](../../Metadata/HeinMachLookSpin_20261015/Review/HeinMach_Before_After.jpg).

MainHeinSpin02의 실제 HeinMach 자연 Spinning은29 events/3 sections와 boundary cleanup까지 완료했고 PlayerAttackCollision suite는 Success다. 넓은 CombatEffect suite는 그 뒤 rear-Brutal의 B 대상 선택 fixture에서 Fail이므로 전체 HeinMach 성공으로 기록하지 않는다. MainDevSpin01은 같은 현재 Main의 DevMap에서 CombatEffect(Spinning 선택+공유 수명/취소·승인 적중/Brutal)와 PlayerAttackCollision 두 suite가 Success다. 실제 로드 모듈은 표준 UnrealEditor-Khazan.dll SHA a8df6850908f08e84b6c8cc8a555c92d46b5c34ba75b136f9eac1b841a325069이며 Scene01과 같다. 작업 초기73fed225 격리 검사와 구분한다. 실제 자연 재생의 회전 초·중·마무리를 검수했고 붉은 OverFury/Charge 잔광은 보이고 회색 헬릭스 막은 사라졌다. 새 Source/Config/DLL 저작·전달/build0이며 데이터만 변경했다. [Main 회전 공격](../../Metadata/HeinMachLookSpin_20261015/Review/Spinning_Main_Sequence.jpg).

색 비교의 최신 정본은 VFXDevFinal03/VFXHeinFinal03 및 ColourFinal03이다. 두 맵322 system씩 모두 native 촬영 완료,280개는 양쪽 .2s 신호가 보이고42개는 다른 시간/대상/파라미터가 필요하다. 14 heuristic flag는 실제 support 범위·사진과 저장 재질을 대조해 무작위 입자 면적/밀도와 물리 조명 반응으로 분류했다. 새 Spin 사본은 RGB signature angle0°/영상 에너지 비1.03663446이다. QA 수치이지 원작 오차/튜닝 값이 아니다. DefaultLit 얼음·돌은 푸른 광원에 반응하며 native HDR/tonemapping/굴절까지 완전 우회했다고 주장하지 않는다. 원작 shader/pixel parity,42개의 조건별 전체 외관 및 Shipping FPS는 미확인이다. 동시 추가된 포탈은 이전321 catalogue에 소급 포함하지 않고 별도 saved 재질 계약으로 확인했다.

pause 직후 렌더 버퍼·빨간 VRAM 문구가 섞인 초기 촬영, 추가 row class key 실패, protected LOD setter 실패는 진단 기록으로 보존한다. Final03은 QA 메시지를 숨기고 simulation pause 뒤 렌더 완료를 기다려 촬영했다. MainHeinSpin01은 초기 editor physics 준비 전 바닥 fixture에서 저장0 실패했고,02는 warmup 뒤 실제 바닥을 사용했다. 게임 동작·재질을 잘못된 촬영/fixture에 맞춰 변경하지 않았다. 최종 QA 저장0/재질 compile fallback 실패0이며 작업 소유 에디터는 모두 정상 종료했다. Rider/다른 에디터 종료·저장·reload0이다.

최종 영수증은 Metadata/HeinMachLookSpin_20261015/FinalVerification.json, 재개는 ResumeState03.json이다. 이 요청의 필수 미전달/미검증 대기는 없고 위의 검증 한계는 유지한다. 새 요청은 현재 Main/해당 saved report부터 시작하며 완료 author/refine/delivery, 전체 추출·이전 Work map/Source/DLL 복원을 반복하지 않는다.


회전 후기의 큰 검은 면은 MainHeinNoCharacter03에서 player skeletal mesh만 숨기자 사라져 캐릭터 망토로 확인됐다. 비교는 Review/Spinning_Character_Isolation.jpg이며, 이 진단을 이유로 particle나 costume를 추가 수정하지 않았다.

최종 쓰기 후 Main map이 동시 저장되어 SHA가 ff7c68d9...에서7b072b9b...로 바뀌었다. MainLatest01은 poses10021/전체 montage3·light/fog/PP가 MainSaved01과 동일함을 확인했고 MainLatestSaved02는 현재 저장본과 포탈 계약을 다시 통과했다. 최신 파일을 보존했으며 이전 전달 바이트로 되돌리지 않았다. 최종 현재 SHA와 전달 시점 SHA는 LatestMainRevision.json 및 FinalVerification.json에 분리했다. 새 게임 에셋 쓰기나 회귀 반복은 없었다.

<!-- HeinMachLookSpin_20261015_complete -->
