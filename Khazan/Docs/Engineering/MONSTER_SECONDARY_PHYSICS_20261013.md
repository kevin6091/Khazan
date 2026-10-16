# 2026-10-13 — 몬스터 보조 물리

사용자의 직접 수정 요청으로 모든 몬스터 PhysicsAsset을 연결하고 플레이어의 현재 Hair/Cloth 반응을 재사용한다. Engineering 표현/물리와 Art 미복원 PhysicsAsset 생성에 걸치며 게임 상태·공격·넉백은 기존 GAS/CMC/Ability가 계속 소유한다. Router → 최신 Architecture/Migration → PHYSICS_DIAGNOSTICS → PLAYER_ORIGINAL_PARTS_PHYSICS 정본/저장 튜닝 보고서를 확인했다.

## 착수 계약

- 현재 gameplay BP 6종의 본체·파츠·무기 PhysicsAsset은 모두 None이다. 저장 enemy 라이브러리에 복원된 PhysicsAsset이 없다. 원작 metadata의 Human Adult/Elite/Halberd anatomy 형상은 표적 재사용하며 그 외 형상은 실제 임포트 뼈/skin에서 계산하고 출처를 구분한다.
- 플레이어 현재 Hair/Cloth PhysicsAsset의 drive·damping·각도·solver와 저장 TemporaryTuning을 기준으로 사용한다. 원작 물리 전체 동일값이라고 기록하지 않는다. 천은 Hair보다 소폭 넓은 각도를 갖는 현재 cloth 계약을 따른다.
- 엔진 RigidBody가 보조 포즈와 시뮬레이션 수명을 소유한다. 본체 anatomy는 animation-driven kinematic이다. 전체 캐릭터 world ragdoll을 켜거나 ASC 상태/Manager/새 runtime component를 추가하지 않는다.
- 기존 main animation을 입력받는 post-process ABP와 PhysicsAsset을 메시별 설정으로 사용한다. 중검병의 LeaderPose 파츠는 독립 CopyPose 평가가 필요한 부분만 기존 BeginPlay 조립을 최소 보완한다. 기존 montage/slot/root motion/notify/mesh scale/무기 부착/피해 policy는 보존한다.
- 작업용 `Khazan_PlayerPartsWork_20261007`의 idle build cache를 재사용하되 최신 Source/Config/Player 설정과 대상35 메시·6 BP를 독립 복사했다. 오래된 work author/test2는 `Metadata/MonsterSecondaryPhysics_20261013/BeforeWork`에 보존 후 build에서 제외했다. 원본 Main 보호와 선택 SHA 전달이 완료 조건이다.

## 마지막 상태

Inventory03 저장 구성 조사 성공. Inventory01/02 Python protected Sockets/ParentClass 접근 오류는 검사 도구 실패로 보존했고 제품 에셋 수정0이다. PrivateBuild01은 다른 Main build의 UBT mutex를 기다린다. 독립 native Audit로 weighted 보조 뼈와 좌표/스케일을 확인한 후 author → fresh saved → 실제 이동/공격/몸 충돌/finite·각도·bounds·cleanup → Main 선택 전달/새 프로세스 확인 순으로 진행한다.


## 2026-10-13 — 저장 후보의 품질 조정 / 메인 전달 전

현재 PA35 / SK35 / post-process20 / Elite CopyPose1 / 기존 gameplay BP6의97 package는 격리 작업본에만 있다. 초기378개에서 giant의 미분류 facial/muscle controls61개를 animation-driven으로 되돌려 explicit cloth/hair317개다. Main 게임 Source/asset 반영0이다. 기존 skeletal vertex/skeleton/animation/texture/material 재임포트0이다.

enemy reference root35개 모두1을 확인하여 player wrapper100용 world-space 설정 대신 ComponentSpace를 사용했다. thin capsule 관성은 실제 dominant skin support의 uniform box 관성으로 보완하고 player mass-per-length·반경·spring/damping/각도·24/4/4·1/60 solver 값을 유지했다. hair angular projection은 현재 player Torso의0.8을 사용한 기술적 어댑터다. 중검병 분리 head/upper는 내부 anatomy 중복 접촉을 제거하고 full parent17 anatomy를 AddClothCollisionSource로 받는다.

PhysicsPIE04~08에서 검병/방패병/중검병/할버드/Apes5 family는 finite/실제 simulation·반응·body contact 및 기존 cloth45도 QA를 통과한다. PhysicsPIE08 peak는32.426/29.823/중검 upper30.800 head25.621/할버드30.265/Apes39.931도다. Yetuga178.218도는 실패이며 Main 전달 근거로 사용하지 않는다. ProjectionBound01/02와 nonlinear 전체 Stability trial은 품질 실패 기록으로 보존한다. alpha1은 철회하고 current player Hair profile + Torso alpha0.8로 복원했다. Yetuga의 single-bone tuft는 머리→attachment 거리를 hair 길이로 쓰지 않도록 FurSupport01에서 실제 skin AABB 길이를 사용한다(예 Hair14:88.627→52.621cm, mass0.177253→0.105242kg). Yetuga만 nonlinear angular solver 적용 FurSolver01 후 fresh PhysicsPIE09를 검증 중이다. 변경은 원작 직접 수치라고 표현하지 않는다.

NoContactControl01~03은 source/body contact 분리 진단용이며 비활성 접촉 설정을 package에 저장하지 않았다. Source36/variant 및 original shape17/17/16 capsule 근거는 기존 report를 재사용한다. debugger session/agent breakpoint 정리 및 user exceptions 보존 완료다. PrivateBuild13은 foreign UBT writer 공유 실패로 unique -Log로 해결했고 foreign build mutex는 기다렸다. PrivateBuild18의 native Saved 검사 TSubclassOf 타입 오류는 도구 오류이며 PrivateBuild19/20 성공으로 보완했다. 최신 Main Source126개를 다시 intake했고 변경은 기존 modular BeginPlay block 하나다. 별도 editor만 사용한다.

정확한 재개: PhysicsPIE09 Driver/Runtime 실제 결과 확인 → 실패면 Yetuga worst bone·stage·rendered_joint_peak와 Saved 검사에서 실제 scale/inertia/contact geometry를 표적 검토(다른5 family 보존) → flag 없는 saved + 실제6종 PIE/RHI 및 PlayerAttackCollision 회귀 → current Main/source/assets SHA/CAS 검증 → 선택97 package/runtime1/DEV1 전달·Main build/새 loader/PIE 확인 → 완료 기록. full Author/구 metadata export/Player 전체 author/FPS/root/VFX author 재실행 금지. PreparedVerification은 실제 품질 통과 후에만 true로 만든다.

<!-- MonsterSecondaryPhysics_20261013_quality09 -->


## 2026-10-13 — Main 선택 전달 완료 / 최종 Main 검증 대기

97 package(PA35/SK35/post-process20/Elite CopyPose1/기존 BP6) + 기존 KZMonster.cpp의 파츠 초기화 block1 + DEV 검증1의99행을 SHA/CAS로 Main에 전달했다. 새 runtime class/component/manager/tag0, private DLL/Build.cs/Config/author source 전달0이다. 최신 Source126 intake와 보호된 Player/Config/기타 Source를 보존했다. MainBuild01을 별도로 실행 중이며 완료 기록은 아직 아니다.

PrivateFinalQA02 fresh saved/RHI의 실제6 family 모두 finite/실제 simulation·반응·접촉/45도 envelope 통과, PlayerAttackCollision 회귀 Success다. 실제 peak: 검병29.073/방패29.836/중검 upper30.802 head25.621/할버드32.513/Apes39.391/Yetuga37.864도. PrivateFinalQA01의 Yetuga cloth49.669도 실패를 보존하고 cloth 관성만 보완했다. 최종317 simulated 설정이며 Yetuga37 single-bone fur +4 cloth는 모두 활성 상태다. 현재 정상 actor 전체 world ragdoll은 off다.

일반19 post-process는 ComponentSpace, Yetuga1은 WorldSpace다. Yetuga의 짧은 털은 source player spring784/damping56/8·8·3도/몸 damping0.1·1.5를 유지하되 hard angular limit·exact solver·실제 dominant skin tip 반경0.5cm 접촉을 적용했다. 원래 고정점에서 겹치는 몸 proxy pair는 분리했고 나머지 몸 접촉은 유지한다. 피부 support uniform-box와 pivot parallel-axis를 합산한 virtual inertia + 어시스턴트 TEMP 배율2를 사용한다. 큰 cloth4에도 기존 관성 TEMP2를 적용했다. 이는 사용자 지정/원작 직접 수치가 아니며 PA의 InertiaTensorScale에 저장된 기술적 안정화다. 원작 metadata50 anatomy capsule만 직접 출처이며 feel은 기존 Player TEMP 재사용이다.

실패한 broad nonlinear/alpha1/soft limit/geometry 후보와 compile/link 도구 오류는 모두 report에 보존했다. FurActual02 실제 body inertia·velocity·PA hard flags를 관측했다. ParticleConstraints count0은 immediate mode에서 등록하지 않는 engine 경로의 값이므로 관절 미생성 증거로 해석하지 않는다. 제약 존재/정확 engine 내부 cause·원작 전체 physics parity와 모든 skin triangle 관통0은 단정하지 않는다.

재개: MainBuild01 Exit/UBT Result 확인 → owned process 목록 확인 → main_commandlet MainSaved01(verify_monster_physics_main_saved_20261013.py, 저장0) → main_rhi MainFinalQA01에서 MonsterSecondaryPhysics.PIE/PlayerAttackCollision.PIE 실제2검사(별도 owned process) → 99SHA/actual module/보호 파일 확인 → 완료 MD/ResumeState 기록. PreparedVerification.json은 실제 PrivateFinalQA02의3검사/6 PNG/원본 Source/99SHA 검증으로 true다. full Author/과거 PA/FPS/root/VFX 재추출·재임포트·private DLL 전달은 반복하지 않는다.

<!-- MonsterSecondaryPhysics_20261013_delivered_pending_main -->


## 2026-10-13T05:17:23.148600+09:00 — 몬스터 PhysicsAsset / 천·Hair Main 완료

사용자 요청을 Main에 적용했다. imported SK35 전부 PA35를 연결했고, explicit cloth/hair가 있는20 메시에는 engine RigidBody post-process, 중검병3 모듈에는 shared CopyPose1을 연결했다. 기존 gameplay BP6와 SK35 수정, 신규 PA35/ABP21의97 package + 기존 KZMonster.BeginPlay 파츠 block1 + DEV 검증1의99행을 exact SHA/CAS로 전달했다. 신규 runtime class/file/component/manager/tag0, private DLL/Build.cs/Config/author source 전달0이다. protected Player/Config/기타 Source SHA 차이0이다. 기존 GAS/AI/Ability/피해·몽타주·root motion·VFX 소유자는 유지한다.

MainBuild01 Exit0, MainSaved02 저장0·35 링크/게임플레이 파츠 연결, MainFinalQA01 실제6 family 이동→방향 전환→authored attack section 모션→피격→회복·finite/물리 반응/몸 접촉/중검 CopyPose 및 PlayerAttackCollision 회귀2검사 Success다. 실제 loaded canonical Main module SHA와99 target SHA는 `Metadata/MonsterSecondaryPhysics_20261013/FinalVerification.json`이다. 최종 실제 peak: Swordsman:29.93° / SwordShield:29.18° / HeavySwordsman:30.80°,25.62° / HalberdElite:30.26° / ApesStoneHandElite:39.39° / Yetuga:37.86°. 정상 캐릭터 전체 world ragdoll은 off이고 engine post-process가 보조 뼈317개의 수명/취소/EndPlay를 소유한다. 테스트 floor/camera/fixture와 검사 settings는 별도 owned process에서만 사용했고 map/asset 저장0, user/foreign editor 제어0이다.

수치/형상 출처: Human Adult17/Elite17/Halberd16 원작 anatomy capsule은 OriginalAnatomyShapes.json의 package/export field/raw Center·Rotation·Radius·Length/SHA다. 해당 reference bone에만 사용하고 source NoCollision policy는 몸 접촉 목적의 활성 collision으로 변경했다. 그 외 anatomy는 실제 LOD0 dominant skin AABB에서 계산했다. feel은 현재 Player_Original_Hair/Torso_RigidBody_PhysicsAsset의 player TEMP spring/damping/각도/몸 damping·반경·mass-per-length와24/4/4·1/60을 재사용한 것이다. source original physics 전체 동일값으로 기록하지 않는다.

일반19 post-process는 unit enemy ComponentSpace, Yetuga1은 WorldSpace다. Yetuga37 짧은 털의 source784/56·8/8/3도·0.1/1.5·0.5cm는 유지하고 hard angular bounds/exact solver/실제 dominant skin tip sphere를 사용했다. skin uniform-box + pivot parallel-axis virtual inertia와 어시스턴트 TEMP 배율2로 과한 뒤집힘을 줄였고 큰 cloth4는 기존 virtual inertia TEMP2를 적용했다. 근거/수식/원시 support와 각 저장 값은 위 final report의 sources 및 saved native report다. 원래 고정점에서 겹치는 anatomy proxy pairs는 분리하고 그 외 몸 접촉을 유지한다. PA editor의 DefaultInstance.InertiaTensorScale, constraints의 spring/damping/limits/collision을 조정 위치로 사용한다. 새 gameplay tuning literal/runtime settings owner는 추가하지 않았다.

PrivateFinalQA01 Yetuga cloth49.67° 실패는 geometry/숫자를 바꾸지 않고 QA를 느슨하게 통과시킨 것이 아니다. cloth 관성만 보완한 PrivateFinalQA02의 fresh saved/RHI/gameplay3검사와 Main 최종 검증으로 대체한다. 이전 broad nonlinear/alpha1/geometry/soft limit 및 도구 compile/link 실패는 보존했다. ParticleConstraints count0은 immediate-mode의 등록 경로 차이이므로 관절 미생성으로 확정하지 않는다. debugger session/agent breakpoint는 정리하고 user exception 상태는 유지했다.

필수 잔여0이다. 현재 gameplay6 family runtime 검증과 그 외 저장 library variants 설정을 구분한다. 전체 source-game physics parity/모든 skin 삼각형 관통0/network/shipping은 검증하지 않았다. 후속은 이 완료 → final evidence → 대상 PA의 설정만 표적 확인한다. full author/메타데이터 전수 추출/원본 재임포트/Player 전체 author/FPS/root/VFX 재실행·옛 DLL 전달은 하지 않는다. 앞선 Main 미반영/검증 대기 절은 이 완료로 대체한다.

<!-- MonsterSecondaryPhysics_20261013_main_complete -->
