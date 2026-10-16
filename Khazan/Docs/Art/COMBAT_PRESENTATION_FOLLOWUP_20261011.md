# CombatPresentationFix Art 후속 — 2026-10-11

Main 통합 요청으로 미완료 후속을 재개했다. 원본 source timing/pose/lifetime/velocity/material dependency는 기존 CombatEffects metadata/CombinedPreparedPlaybackPlan을 재사용한다. UI 원본과 Shader 수정은 [UI 감사](COMBAT_UI_SOURCE_AUDIT_20261011.md), runtime/취소/검증 계약은 [Engineering](../Engineering/COMBAT_PRESENTATION_FOLLOWUP_20261011.md)으로 분리한다.

## 실제 저장 내용과 수치 출처

혈흔4에 기존 `PP_Dmg_Blood_Trail_Sub`의 실제 physical sprite를 추가했다. 첫 emitter는 mesh였으므로 material `Base_DefaltParticle_Masked` 및 type으로 실제 sprite를 선택한다. source PS를 engine API로 target 안에 복제하여 Cascade sibling spawn/distribution의 package 참조를 함께 remap하고, 실제 사용할 sprite만 유지한다. source 색/속도/수명/물리 module을 재사용하며 mesh-decal emitter를 추가하지 않는다. 기존 최종 death Frequency3와 continuous rate0은 유지했다.

기존 shared plane slash에서 DAS 전용 variant1을 만들고 color-over-life에 (1,.12,.08)을 곱했다. core6 및 variant의 sprite burst/constant spawn rate는2배다. 두 값 모두 사용자의 표현 보강 요청에 따른 **어시스턴트 임시 튜닝**, 원작 직접 수치가 아니다. 원작 창과 transform을 유지하고 실제 montage3의 기존 이벤트36개만 variant로 재연결했다. source shared particle 자체를 다른 무기용으로 일괄 덮어쓰지 않는다. VFX 저장14개와 exact 이름은 VFXAuthorResume03/VFXAuthored.json이다.

눈은 사용자 요청 최대40cm를 기존 DeepSnow55cm 대신 적용한다. 다른18/36cm layer는 유지하며 발35cm는35/40=.875, 이전 weapon50cm는 substrate 때문에40cm/압축1로 제한한다. contact padding15cm는 기존에 알린 capsule 경계 밖 추가 여유라는 해석이다. 원작 직접 값이 아니다. 기존 정확한 baker profile2/4,783,236bytes를 적용하고 material2/map만 저장했다. GPU 측정40cm/foot34cm는 직접 원작 metadata가 아닌 실제 프로젝트 관측값이다.

Sun7000→5000 lux/Sky1→1.1은 하이라이트·암부 가독성을 위한 **어시스턴트 임시 조명 튜닝**이다. 원작 확인값으로 표시하지 않는다. 기존 light color/방향, Fog/weather/terrain/비대상 actor pose를 유지하고 PP를 다시 넣지 않았다. actor9861/PP0 및 전 actor transform이 보존됐다. MainHeinMachAfterResume01의 동일 카메라3/Exit0/save0 사진을 before와 직접 비교했다. lowering snow로 일부 돌이 더 드러났고 기존 풍경과 그림자를 유지했다. pixel parity나 모든 clipped highlight 해결을 주장하지 않는다.

MainVFXResume01의 실제 native18+Brutal5는 Success이며383 PNG를 기록했다. 기본 붉은 slash와 증량 혈흔의 실제 frame을 직접 검수했다. 전체 observer는 당시 UI ring mask 입력 누락으로 실패했고 두 default-pin을 수정한 뒤 UI PIE05의 새 RHI shader fallback0을 확인했다. source radii/color는 유지했다. 마지막 VFX observer 완료 상태는 하단 완료 절/FinalVerification을 따른다. 이전 완료 VFX/VAT/charge/노출 보정을 구버전으로 되돌리지 않았으며 author 증량은 반복 실행하지 않는다.
## 2026-10-11 — 실제 Main RHI 최종 완료

MainVFXResume02는 native18+Brutal5 Success/392 captures/save0/material compile fallback0/Exit0이다. UI PIE05의 수정된 실제 링/B 표시와 동일 native module을 사용했다. source timing·수명·geometry/원작 asset dependencies 및 기존 VAT/charge/혈흔 최종 수정을 유지했다. Main 전달 Content19/source8, 의도된 후속 UI ring1/DEV fixture1, backup/current SHA는 [최종 receipt](../../Metadata/CombatPresentationFix_20261011/MainResume/FinalVerification.json)를 따른다. 실제 RGB/혈흔 분사·원작 슬래시와 같은 카메라의 설원은 직접 검수했다. 필수 잔여는 없고 full pixel/frame·원작 stripped shader·Shipping 검증 경계는 유지한다.

## 2026-10-13T08:42:00+09:00 — 사용자 패링·공격 적중 사진 대비 부족점 분석

이번 요청은 비교·리스트 작성이다. 게임 C++/BP/에셋 변경, 새 build/PIE는 하지 않았다. 사용자 사진은 첫 번째가 패링, 두 번째가 플레이어의 몬스터 적중이다. Temp 첨부의 유실을 방지해 [패링 사진](../../Metadata/CombatVFXReferenceReview_20261013/References/01_Parry.png), [적중 사진](../../Metadata/CombatVFXReferenceReview_20261013/References/02_PlayerHitMonster.png)을 복사했다. 사진의 모든 레이어가 패링/일반 적중만의 효과인지는 미확인이다. 특히 적중 사진의 넓은 분홍·보라 광막이 일반 적중/강공격/스킬 중 어느 조건인지 사진만으로 확정하지 않는다.

### 현재 비교 기준과 역사 기록의 구분

- 비교 대상은 현재 Main `Khazan/Khazan`이다. 첨부된 `Khazan_GiantVFXWork_20261013`의 검사 파일은 별도 작업 사본이다. `Metadata/GiantVFX_20261013/ResumeState.json`은 이번 확인 시 `main_applied=false`였으므로 사본의 개선을 Main 완료로 계산하지 않았다.
- 최신 성공 패링은 `GA_Player_Guard.ParryImpactEffect → /Game/_Art/Effects/Combat/AttackContact/PP_Combat_HitBurst`다. 과거 `Parry_20261012/MainPIE02`의 원본 JustGuard 13-emitter 재생 사진은 현재 패링의 주 근거로 사용하지 않는다. 현재 burst는 파랑/보라/빨강의 3-emitter 방사형 입자다. 색·폭·속도 등은 기존 어시스턴트 TEMP이고 원작 확인값이 아니다.
- 현재 GA SHA `794c2b284b616f40961559eb76e296d2ad6c24904d2a43c49bc9e96b58f75766`는 `CombatImpactUpgrade_20261012/MainSaved03/IntegratedPackages.json`과 일치한다. HitBurst SHA `0f7e11716af9187914a41a262e3b6399b15ade581df0f3d13ff4931c1314e087`, `FP_Monster_HitBloodReference` SHA `72f520c38f6ec3f64b9b8575a077c46392824856843b4dd487c9a824ffdff6e6`는 해당 작업의 최신 FinalVerification과 일치한다. Guard/Combo 실행 Source도 최신 완료 보고서와 일치했다. `KZMonster.cpp` 전체 SHA는 후속 작업으로 달라져 현재 `PlayHitBlood`를 직접 읽었다.
- 직접 본 최신 화면: [패링 충돌](../../Metadata/CombatImpactUpgrade_20261012/AdditiveRegression01/01_ActualParryImpact.png), [패링 후속 프레임](../../Metadata/CombatImpactUpgrade_20261012/AdditiveRegression01/02_ActualParryMotion.png), [성공 적중](../../Metadata/CombatImpactUpgrade_20261012/PlayerAdditivePIE03/ActualMonsterHit.png), 같은 폴더 `PlayerSlash_09.png`, `BurstVisual05/01_ActualParryFlash.png`. 적중 화면의 녹색 wire box는 검사 표시이며 VFX의 녹색 카드/알파 불량으로 분류하지 않는다.
- 기존 혈액 3-emitter와 바닥 혈흔·산포, 무기 궤적은 존재한다. 최근 알파 수정은 `ParticleAlpha_20261013/FinalVerification.json`을 따른다. 이를 미구현으로 다시 나열하지 않는다. 현재 RiderLink 연결은 false였으며 이번 비교는 저장된 실제 전투 화면과 현재 저장 에셋/Source 확인 범위다.

### 부족점과 우선순위

| ID | 우선순위 | 대상 | 사진 대비 현재 차이 | 보완 방향/판정 범위 |
| --- | --- | --- | --- | --- |
| P-01 | 높음 | 패링의 주 형태 | 사진은 무기 접촉을 따라 길고 가는 백색 중심·붉은 외곽의 대각선이 눈에 띈다. 현재는 원형으로 고르게 퍼지는 다색 방사선이 주 형태라 금속 충돌선의 방향성이 약하다. | 접촉/무기 방향을 읽게 하는 선형 flash와 보조 방사 sparks를 구분한다. 사진의 선형 레이어 소유자가 무기 궤적인지 패링 효과인지 추가 확인한다. |
| P-02 | 높음 | 패링 색·명도 중심 | 사진은 백색의 밝은 선과 국소 붉은 빛이 중심이다. 현재 파랑/보라/빨강 개별 streak가 비슷한 비중으로 튀어 중심이 분산된다. | 백색 중심과 얇은 색 외곽의 위계를 우선 검토한다. 입자 수의 단순 증량은 해결 근거가 아니다. |
| P-03 | 중간 | 미세한 금속 sparks | 사진에는 가는 선 주변/아래로 작은 백색 점과 짧은 꼬리가 촘촘히 보인다. 현재는 비교적 긴 다색 streak 중심이며 크고 작은 입자의 대비가 부족하다. | 긴 주선·짧은 꼬리·작은 점의 형태와 밀도 차이를 만든다. 실제 낙하 속도/수명은 정지 사진으로 확정하지 않는다. |
| H-01 | 높음 | 적중의 넓은 광막 | 사진은 접촉 주변에 넓은 분홍/보라색 반투명 호·광막이 캐릭터를 감싼다. 현재 성공 적중은 국소 혈액과 직선 burst가 앞서며 같은 면적의 부드러운 광막이 부족하다. | 현재 붉은 무기 slash와 적중 광막을 별도로 판단한다. 해당 공격/스킬 조건 확인 전 모든 일반 적중에 공통 추가하지 않는다. |
| H-02 | 높음 | 적중 중심과 바깥 glow | 사진은 밝은 분홍·백색 중심에서 붉은 근접 glow, 보라색 외곽으로 퍼지는 층이 읽힌다. 현재는 혈액 덩어리·개별 다색 불꽃이 두드러져 중심 hotspot과 넓은 falloff의 연결이 약하다. | 중심/중간/외곽 밝기와 투명도 구조를 보완한다. DevMap과 사진의 노출 차이 때문에 절대 밝기 배율은 결정하지 않는다. |
| H-03 | 중간 | 혈액·빛의 결합 | 혈액과 바닥 혈흔은 이미 있지만 현재 붉은 혈액과 다색 burst가 별개 요소로 읽힌다. 사진은 붉은 접촉부와 보라색 미세 빛이 이어지는 인상이다. | 기존 혈액을 보존하면서 광원 중심·분사 방향·미세 sparks의 색과 배치를 맞춘다. 혈액 전체를 발광 재질로 바꾸는 제안이 아니다. |
| C-01 | 높음 | 실제 접촉 위치 | 현재 패링 위치는 두 캐릭터 위치의 중간과 가슴 높이 평균이며, 적중 혈액 위치는 전달 Contact를 capsule 표면으로 이동시킨 근사점이다. 무기끼리/무기와 몸의 실제 접촉점과 항상 일치하는 계약이 아니다. | 참조 사진의 정확한 native 접점은 미확인이나 현재 근사 계산은 Source로 확인됐다. 높이·방향이 다른 공격과 큰 몬스터에서 접촉과 효과가 어긋나는지 표적 검증이 필요하다. |
| C-02 | 중간 | 패링과 타격의 시각 구분 | 현재 패링과 적중/플레이어 피격은 같은 계열의 3색 burst를 재사용한다. 두 사진에서 읽히는 금속성 백색 선과 분홍·보라 타격 광막의 구분이 약하다. | 성공 패링/명중의 기존 실행 경로는 유지하고 표현 형태·색 위계를 구분하는 작은 에셋 설정 변경부터 검토한다. |
| C-03 | 추가 확인 | 주변 표면과의 결합 | 적중 사진에서는 인물·바닥에 분홍/보라색이 넓게 비친다. 현재 DevMap 화면에서는 같은 색 번짐이 뚜렷하지 않다. | 실제 조명, 반투명 광막의 중첩, bloom 중 무엇이 만든 것인지 미확인이다. HeinMach의 같은 노출/카메라 조건을 맞춘 뒤 light나 bloom 추가 여부를 결정한다. |

### 검증 공백과 다음 절차

첨부 `KZMonsterPresentationRepairPIETest.cpp`는 실제 입자 수, 데칼 수/방향, 생존·사망 및 giant 실행/attachment 등의 기능 검증을 한다. 입자가 존재한다는 성공 조건은 사진처럼 보인다는 기준과 다르다. 현재 성공 적중 캡처에는 검사 wire box가 겹치므로 세부 hotspot/alpha 판정의 한계도 있다.

후속 구현 전에는 사진의 공격 종류·추가 광막 조건을 먼저 특정한다. 그 조건의 실제 패링/명중을 HeinMach 게임 카메라에서 검사 표시 없이 촬영하고 충돌 직전→발생→최대 강조→소멸 순서로 확인한다. 비교 기준은 접촉 정렬, 백색 중심/분홍·보라 외곽 위계, 작은 sparks의 대비, 인물 가독성, 카드/깊이 경계다. 지금 사진 두 장만으로 정확한 발생 지연·수명·잔상·hit-stop·camera shake·SFX를 부족하거나 원작과 일치한다고 판정하지 않는다. 새 튜닝 숫자는 정하지 않았다. 분석·리스트 작성은 완료이며 구현 요청은 별도다.

<!-- CombatVFXReferenceReview_20261013_analysis_complete -->

## 2026-10-13T09:47:37+09:00 — 사용자 정정 반영: 공격 선형 VFX / 패링 광막 재판정

**사용자 최신 정정이 비교 기준이다. 백색 중심·붉은 외곽의 길고 가는 선은 플레이어 공격 VFX, 넓은 분홍·보라 광막은 성공 패링 VFX다.** 앞선 08:42 비교 절은 두 사진의 효과 역할을 반대로 분류했다. 그 절의 P-01~P-03/H-01~H-03, C-02의 역할 설명, C-03의 '적중' 광막 설명과 광막을 공격/스킬 후보로 보류한 판단은 현재 비교·후속 구현 기준으로 사용하지 않는다. 역사 기록은 보존하며 아래 표가 이를 대체한다.

첨부 이미지의 픽셀과 Main 캡처는 바꾸지 않았다. 잘못된 역할로 명명한 기존 References/01_Parry.png는 공격 사진, References/02_PlayerHitMonster.png는 패링 사진이다. 혼동을 막기 위해 올바른 역할의 복사본 [Attack_LinearWhiteRed.png](../../Metadata/CombatVFXReferenceReview_20261013/References/Attack_LinearWhiteRed.png), [Parry_PinkPurpleHalo.png](../../Metadata/CombatVFXReferenceReview_20261013/References/Parry_PinkPurpleHalo.png)을 추가했다.

### 현재 프로젝트에서 확인한 내용

- Main의 Guard GA, PP_Combat_HitBurst, FP_Monster_HitBloodReference SHA는 앞선 완료 증거와 다시 일치했다. Guard의 ParryImpactEffect는 여전히 PP_Combat_HitBurst를 소비한다. 실제 성공 패링 캡처는 3색 방사형 긴 sparks가 주 표현이며 사진 같은 넓고 부드러운 분홍·보라 광막은 부족하다.
- 공격에는 기존 원작 효과와 실제 무기를 따라가는 추가 KZ_Slash가 있다. PlayerSlash_09.png에는 붉은 곡선 슬래시와 밝은 선이 보인다. 따라서 '공격 슬래시/백색 성분 자체가 없다', '무기 추적이 미구현'으로 판정하지 않는다. 보완점은 사진의 가는 백색 중심·붉은 외곽이 주 형태로 읽히도록 폭/밝기/투명도 위계를 정리하고, 성공 적중의 현재 다색 방사형 불꽃과 작은 백색 sparks를 구분하는 것이다.
- FP_Monster_HitBloodReference는 기존 혈액 3-emitter에 공통 burst 3-emitter가 더해진 상태다. 혈액 분사·바닥 혈흔은 이미 있다. 패링 사진의 바닥 혈흔이 그 패링 한 번으로 생겼다는 근거는 없으므로 패링에 혈액을 추가하는 요구로 해석하지 않는다. 이전 H-03의 사진 기반 '적중 혈액+보라 광막 결합' 제안은 철회한다.
- 현재 Guard는 두 actor 위치의 중간/가슴 평균 높이를 사용한다. PlayHitBlood는 전달 Contact에서 capsule 표면으로 이동한 점을 사용한다. 근사점이라는 사실은 현재 Source로 재확인했으며 실제 어긋남의 빈도/크기는 추가 촬영 대상이다.

### 현재 필요한 부분 — 이 표가 후속 기준

| ID | 우선순위 | 대상 | 현재 부족점 | 필요한 보완 |
| --- | --- | --- | --- | --- |
| RP-01 | 최우선 | 성공 패링 광막 | 현재는 개별 방사선 위주다. 사진처럼 플레이어 주변을 감싸는 넓은 분홍·보라 반투명 호/광막이 부족하다. | 성공 패링 경로에 넓은 광막 레이어를 마련한다. 입자 수 증량만으로 이 면 형태가 생기지는 않는다. 기존 ParryImpactEffect 참조를 활용하는 작은 에셋 설정/변형부터 검토한다. |
| RP-02 | 높음 | 패링 중심과 외곽 | 사진은 접촉 주변의 강한 붉은·분홍빛에서 바깥 보라빛으로 퍼진다. 현재는 파랑/보라/빨강 streak가 비슷한 비중이라 그 색·명도 구조가 약하다. | 밝은 접촉 중심, 분홍 중간 광막, 보라 외곽의 밝기/색/연속 alpha를 구분한다. 실제 light와 bloom의 필요 여부는 동일 환경에서 확인한다. |
| RP-03 | 중간 | 패링 보조 sparks | 광막 안쪽 접촉부의 작은 백색·보라 sparks에 비해 현재 긴 다색 streak가 두드러진다. | 큰 광막을 주 표현으로 두고 작은 입자·짧은 꼬리를 보조로 조정한다. 광막 안에서도 손/무기/피격 반응이 읽히게 한다. |
| RA-01 | 높음 | 공격 주선 | 붉은 슬래시와 밝은 선은 이미 있으나 현재 캡처에서는 넓은 붉은 곡면이 강하게 읽힌다. 사진의 가는 백색 중심·붉은 외곽 대비로 추가 정리가 필요하다. | 무기 추적과 원래 궤적은 활용하고 백색 중심/붉은 외곽의 폭·밝기·투명도 위계를 다듬는다. 사진 한 프레임의 직선을 모든 공격의 고정 직선으로 강제하지 않는다. |
| RA-02 | 높음 | 실제 적중 강조 | 성공 적중의 공통 burst가 파랑/보라/빨강으로 퍼져 공격 사진의 백색·붉은 선형 표현에서 주의가 분산된다. | 명중부는 백색 중심과 붉은 빛을 중심으로 정리하고 혈액과 무기 주선의 관계를 맞춘다. 공중 휘두름과 실제 적중의 기존 조건은 유지한다. |
| RA-03 | 중간 | 공격 미세 sparks | 사진에는 주선 주변에 작은 백색 점·짧은 꼬리가 보인다. 현재 비교적 긴 다색 streak만으로 그 세밀함을 대신하기 어렵다. | 작은 백색 입자층과 소수의 짧은 꼬리를 보완하고 긴 streak의 비중을 조정한다. 수명/낙하/밀도의 정확한 값은 원본 metadata 또는 영상 확인 뒤 결정한다. |
| RC-01 | 높음 | 패링/공격 표현 계약 | 현재 성공 패링과 타격/플레이어 피격이 같은 계열의 burst를 사용한다. 패링 광막과 공격 백색·붉은 선의 형태 구분이 약하다. | 기존 실행 소유자는 그대로 두고 ParryImpactEffect와 적중 표현의 에셋 설정을 구분한다. 공용 burst를 일괄 변경해 다른 피격 표현까지 함께 바꾸지 않는다. |
| RC-02 | 표적 검증 우선 | 효과 접점 | 패링/적중 모두 근사 spawn 지점을 사용해 실제 손/무기/몸 접점과 일치하는지 별도 확인이 필요하다. | 가까운/높은/측면 공격 및 거대 몬스터에서 검사 표시 없는 실제 게임 카메라로 접촉점을 확인한 뒤 필요한 부분만 보정한다. 근사 사용 자체를 모든 프레임의 확인된 시각 실패로 표현하지 않는다. |

### 비교와 검증 범위

이번 재판정은 사용자 정정, 두 사진 재열람, 현재 연결 에셋 SHA, 실제 저장된 패링/슬래시/명중 화면과 spawn Source를 근거로 한다. 게임 Source/BP/에셋 수정 및 새 build/PIE는 하지 않았다. 패링 사진의 넓은 주변 분홍빛이 실제 조명인지 광막 중첩/bloom인지, 정확한 시작·최대 강조·소멸 시간, hit-stop/camera shake/SFX는 사진만으로 미확인이다. 새로운 튜닝 수치를 정하지 않았다.

후속 검수는 **성공 패링에는 분홍·보라 광막 / 플레이어 공격에는 백색 중심·붉은 외곽의 주선**을 구분해 진행한다. 패링 성공, 일반 가드, 헛공격, 실제 명중을 같은 HeinMach 카메라/노출과 검사 표시 없는 화면에서 각각 비교하고 발생→최대 강조→소멸의 형태·접점·인물 가독성·카드/깊이 경계를 확인한다. 입자 수/컴포넌트 생성 검사의 성공은 이 시각 품질 기준의 통과를 대신하지 않는다. 기존 완료된 혈액/혈흔/무기 추적/알파 처리를 미구현으로 재분류하지 않는다.

<!-- CombatVFXReferenceReview_20261013_user_corrected_roles -->
