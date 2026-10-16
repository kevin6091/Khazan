"""Bind final Main evidence/hashes and append completion only after actual verification."""
from pathlib import Path
import datetime,hashlib,json
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Metadata/MonsterSecondaryPhysics_20261013'
def read(name):return json.loads((OUT/name).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=read('DeliveryManifest.json');assert manifest['complete']
assert read('PreparedVerification.json')['passed']
assert read('MainBuild01/Exit.json')['exit']==0
saved=read('MainSaved02/MainSavedVerification.json');assert saved['passed'] and len(saved['meshes'])==35 and saved['save_count']==0
driver=read('MainFinalQA01/Driver.json');assert driver['status']=='passed' and len(driver['tests'])==2 and all(t['passed'] for t in driver['tests'])
assert read('MainFinalQA01/Exit.json')['exit']==0
runtime=read('MainFinalQA01/Runtime.json');assert len(runtime['families'])==6
for f in runtime['families']:
    assert f['finite'] and all(p['simulated']>0 and p['responding']>0 and p['joint_peak_deg']<45. for p in f['parts'])
    assert (OUT/'MainFinalQA01'/f"Physics_{runtime['families'].index(f):02d}.png").exists()
for row in manifest['files']:assert sha(ROOT/row['path'])==row['prepared'],('Concurrent delivered target change',row['path'])
protected=read('ProtectedBeforeDelivery.json')
changed=[name for name,before in protected.items() if not (ROOT/name).exists() or sha(ROOT/name)!=before]
assert not changed,('Protected source/config/player changed',changed)
module=Path(driver['actual_module']);assert module.is_relative_to(ROOT/'Binaries') and sha(module)==driver['module_sha256']
stamp=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
report=dict(passed=True,completed=stamp,delivered_files=len(manifest['files']),
    physics_assets=35,secondary_postprocesses=20,modular_copy_pose=1,modified_meshes=35,modified_blueprints=6,
    configured_simulated_bones=317,new_runtime_classes=0,new_runtime_files=0,new_development_tests=1,
    main_saved=saved,main_native_rhi=driver,main_runtime=runtime,protected_changed=changed,
    sources=['OriginalAnatomyShapes.json','Author01/MonsterSecondaryPhysicsAuthor.json','FurSupport01/MonsterSecondaryPhysicsFurSupport.json','FurTips01/MonsterSecondaryPhysicsFurTips.json','FurJointInertia01/MonsterSecondaryPhysicsFurJointInertia.json','FurBundleStability01/MonsterSecondaryPhysicsFurBundleStability.json','GiantClothStability01/MonsterSecondaryPhysicsGiantClothStability.json'],
    limitations='Other imported variants statically configured, runtime gameplay six families tested. Current player feel reuse plus explicit technical/TEMP adaptations; no claim of original-game physics parity, all-triangle zero penetration, network/shipping verification.')
(OUT/'FinalVerification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
marker='<!-- MonsterSecondaryPhysics_20261013_main_complete -->'
peaks=' / '.join(f["family"]+':'+','.join(f"{p['joint_peak_deg']:.2f}°" for p in f['parts']) for f in runtime['families'])
engineering=f'''

## {stamp} — 몬스터 PhysicsAsset / 천·Hair Main 완료

사용자 요청을 Main에 적용했다. imported SK35 전부 PA35를 연결했고, explicit cloth/hair가 있는20 메시에는 engine RigidBody post-process, 중검병3 모듈에는 shared CopyPose1을 연결했다. 기존 gameplay BP6와 SK35 수정, 신규 PA35/ABP21의97 package + 기존 KZMonster.BeginPlay 파츠 block1 + DEV 검증1의99행을 exact SHA/CAS로 전달했다. 신규 runtime class/file/component/manager/tag0, private DLL/Build.cs/Config/author source 전달0이다. protected Player/Config/기타 Source SHA 차이0이다. 기존 GAS/AI/Ability/피해·몽타주·root motion·VFX 소유자는 유지한다.

MainBuild01 Exit0, MainSaved02 저장0·35 링크/게임플레이 파츠 연결, MainFinalQA01 실제6 family 이동→방향 전환→authored attack section 모션→피격→회복·finite/물리 반응/몸 접촉/중검 CopyPose 및 PlayerAttackCollision 회귀2검사 Success다. 실제 loaded canonical Main module SHA와99 target SHA는 `Metadata/MonsterSecondaryPhysics_20261013/FinalVerification.json`이다. 최종 실제 peak: {peaks}. 정상 캐릭터 전체 world ragdoll은 off이고 engine post-process가 보조 뼈317개의 수명/취소/EndPlay를 소유한다. 테스트 floor/camera/fixture와 검사 settings는 별도 owned process에서만 사용했고 map/asset 저장0, user/foreign editor 제어0이다.

수치/형상 출처: Human Adult17/Elite17/Halberd16 원작 anatomy capsule은 OriginalAnatomyShapes.json의 package/export field/raw Center·Rotation·Radius·Length/SHA다. 해당 reference bone에만 사용하고 source NoCollision policy는 몸 접촉 목적의 활성 collision으로 변경했다. 그 외 anatomy는 실제 LOD0 dominant skin AABB에서 계산했다. feel은 현재 Player_Original_Hair/Torso_RigidBody_PhysicsAsset의 player TEMP spring/damping/각도/몸 damping·반경·mass-per-length와24/4/4·1/60을 재사용한 것이다. source original physics 전체 동일값으로 기록하지 않는다.

일반19 post-process는 unit enemy ComponentSpace, Yetuga1은 WorldSpace다. Yetuga37 짧은 털의 source784/56·8/8/3도·0.1/1.5·0.5cm는 유지하고 hard angular bounds/exact solver/실제 dominant skin tip sphere를 사용했다. skin uniform-box + pivot parallel-axis virtual inertia와 어시스턴트 TEMP 배율2로 과한 뒤집힘을 줄였고 큰 cloth4는 기존 virtual inertia TEMP2를 적용했다. 근거/수식/원시 support와 각 저장 값은 위 final report의 sources 및 saved native report다. 원래 고정점에서 겹치는 anatomy proxy pairs는 분리하고 그 외 몸 접촉을 유지한다. PA editor의 DefaultInstance.InertiaTensorScale, constraints의 spring/damping/limits/collision을 조정 위치로 사용한다. 새 gameplay tuning literal/runtime settings owner는 추가하지 않았다.

PrivateFinalQA01 Yetuga cloth49.67° 실패는 geometry/숫자를 바꾸지 않고 QA를 느슨하게 통과시킨 것이 아니다. cloth 관성만 보완한 PrivateFinalQA02의 fresh saved/RHI/gameplay3검사와 Main 최종 검증으로 대체한다. 이전 broad nonlinear/alpha1/geometry/soft limit 및 도구 compile/link 실패는 보존했다. ParticleConstraints count0은 immediate-mode의 등록 경로 차이이므로 관절 미생성으로 확정하지 않는다. debugger session/agent breakpoint는 정리하고 user exception 상태는 유지했다.

필수 잔여0이다. 현재 gameplay6 family runtime 검증과 그 외 저장 library variants 설정을 구분한다. 전체 source-game physics parity/모든 skin 삼각형 관통0/network/shipping은 검증하지 않았다. 후속은 이 완료 → final evidence → 대상 PA의 설정만 표적 확인한다. full author/메타데이터 전수 추출/원본 재임포트/Player 전체 author/FPS/root/VFX 재실행·옛 DLL 전달은 하지 않는다. 앞선 Main 미반영/검증 대기 절은 이 완료로 대체한다.

'''+marker+'\n'
for rel in ('Docs/Engineering/MONSTER_SECONDARY_PHYSICS_20261013.md','Docs/Engineering/ENGINEERING_PROJECT_STATE.md','Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md','Docs/Engineering/PHYSICS_DIAGNOSTICS.md'):
    p=ROOT/rel
    if marker not in p.read_text(encoding='utf-8-sig'):
        with p.open('a',encoding='utf-8') as f:f.write(engineering)
short=f'\n\n## {stamp} — 몬스터 보조 물리 Main 완료 (ARCH-06/07/10/16 유지)\n\n기존 engine SkeletalMesh/RigidBody/CopyPose가 보조 포즈·수명·EndPlay를 소유한다. ASC/Ability/Task/CMC/AI 소유자는 그대로다. 새 runtime class/component/manager/tag0이다. 중검의 기존 BeginPlay만 follower 독립 평가·parent tick prerequisite·full parent cloth collision source로 보완했다. 실제99SHA/Main build/saved/RHI/gameplay 완료 정본은 MONSTER_SECONDARY_PHYSICS_20261013.md 및 Metadata/MonsterSecondaryPhysics_20261013/FinalVerification.json이다. 기존 착수/미반영/검증 대기 기록을 이 완료가 대체한다.\n'+marker+'\n'
for rel in ('Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md','0_DOCUMENT_ROUTER.md'):
    p=ROOT/rel
    if marker not in p.read_text(encoding='utf-8-sig'):
        with p.open('a',encoding='utf-8') as f:f.write(short)
art=f'''\n\n## {stamp} — 몬스터 PhysicsAsset 형상 Main 전달 완료\n\nSK35/PA35/post-process20/shared CopyPose1/기존 gameplay BP6의97 package를 Main에 전달했다. 원본 vertex/skeleton/animation/texture/material/LOD 재임포트0이다. source metadata anatomy17/17/16 capsule의 package/field/raw/SHA는 OriginalAnatomyShapes.json, 그 외 dominant LOD0 skin bounds와 Yetuga actual skin tip sphere/질량·관성 계산은 final evidence의 source reports다. Feel은 current Player TEMP 재사용과 명시된 virtual-inertia TEMP2/기술적 adaption이며 원작 physics 전체 복원으로 표현하지 않는다. 최종 explicit simulated317이며 초기378/미완료 기록을 대체한다. Runtime 품질/검증/cleanup은 ../Engineering/MONSTER_SECONDARY_PHYSICS_20261013.md 및 Metadata/MonsterSecondaryPhysics_20261013/FinalVerification.json을 따른다. 필수 잔여0; full 원본 추출/재임포트/기존 shader·VFX·animation 변경을 반복하지 않는다.\n'''+marker+'\n'
for rel in ('Docs/Art/MONSTER_PHYSICS_ASSET_RESTORATION_20261013.md','Docs/Art/ART_PROJECT_STATE.md','Docs/Art/ART_WORK_CONTINUITY.md'):
    p=ROOT/rel
    if marker not in p.read_text(encoding='utf-8-sig'):
        with p.open('a',encoding='utf-8') as f:f.write(art)
(OUT/'ResumeState.json').write_text(json.dumps(dict(status='complete',main_applied=True,completed=stamp,remaining=[],
    evidence='FinalVerification.json',next='No pending mandatory work; targeted PA tuning only if requested'),indent=2),encoding='utf-8')
print('MAIN VERIFIED / DOCUMENTS APPENDED / COMPLETE',len(manifest['files']))
