"""Record selected Main implementation and native QA evidence; never modify game files."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import sys

MAIN = Path(__file__).resolve().parents[2]
ROOT = MAIN / 'Metadata/BeastDodge_20261012'

def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

receipt = read('Completion/InstallReceipt.json')
build = read('MainBuild04/Exit.json')
inputs = read('MainBuild04/Input.json')['source_sha256']
drift = [{'path': p, 'build_input_sha256': s, 'current_sha256': sha(MAIN / p)}
         for p, s in inputs.items() if sha(MAIN / p) != s]
runtime_drift = [r for r in drift if '/Tests/' not in r['path']]
files = [{**r, 'current_sha256': sha(MAIN / r['path']),
          'matches_install': sha(MAIN / r['path']) == r['prepared_sha256']}
         for r in receipt['files']]
asset_drift = [r['path'] for r in files if r['path'].startswith('Content/') and not r['matches_install']]
module = MAIN / 'Binaries/Win64/UnrealEditor-Khazan.dll'
preview = {'runtime_source_drift': runtime_drift, 'development_test_drift': drift,
           'selected_asset_drift': asset_drift, 'current_module_sha256': sha(module)}
if '--check' in sys.argv:
    print(json.dumps(preview, indent=2)); raise SystemExit(0)

assert receipt['status'] == 'installed' and build['exit_code'] == 0
assert not runtime_drift, runtime_drift
assert not asset_drift, asset_drift
final = read('MainFinalQA04/Driver.json')
assert final['status'] == 'passed' and len(final['tests']) == 6
assert read('MainFinalQA04/Exit.json')['exit_code'] == 0
assert final['module_sha256'] == build['module_sha256']
guard = read('MainGuardQA02/Driver.json')
assert guard['status'] == 'passed'
saved = read('MainSavedAssets01/SavedAssets.json')
assert saved['status'] == 'passed'
old = read('MainQA01/Driver.json')
fall = next(t for t in old['tests'] if t['test'] == 'Khazan.GiantFall.PIE')
assert fall['passed']
log = (ROOT / 'MainFinalQA04/Editor.log').read_text(encoding='utf-8', errors='replace')
assert 'PATTERN_CASES_COMPLETE total=47' in log
old_crash = read('MainFinalQA03/Progress.json')
old_crash['status'] = 'failed'
old_crash['error'] = 'Test driver unnecessarily queued PIE for synchronous SourceAudit, then stopped it before viewport startup completed; UE SLevelViewport GameViewport.IsUnique assertion. Driver now excludes SourceAudit from PIE.'
if not (ROOT / 'MainFinalQA03/Driver.json').exists():
    (ROOT / 'MainFinalQA03/Driver.json').write_text(json.dumps(old_crash, indent=2), encoding='utf-8')

stamp = datetime.now().astimezone().isoformat()
limits = [
    'Original custom BehaviorTree native abort, RNG normalization and omitted CDO defaults were not supplied.',
    'Yetuga Group1 part destruction producer is not implemented because its native contract is unconfirmed; the source gate is retained but this route cannot be claimed complete.',
    'Selected-step float semantics, original movement/navigation/physics operators and original executable equivalence remain unverified.',
    'Apes >= threshold, history reset and independent chance draws are explicit project adapters, not verified native semantics.',
    'These tests verify current saved metadata contracts and actual UE execution, not zero-error parity with the original game. Shipping and network play were not tested.'
]
report = {
    'status': 'MainDelivered_Built_NativeValidated', 'at': stamp,
    'project': str(MAIN), 'installed': 'Completion/InstallReceipt.json',
    'game_files': {'initial_selected_files': len(files), 'source_files': 21, 'asset_files': 19,
                   'runtime_source_files': 18, 'total_source_files': 22,
                   'subsequent_existing_qa_file': 'Source/Khazan/Tests/KZPlayerAttackCollisionPIETest.cpp',
                   'total_task_source_asset_files': 41, 'new_runtime_files': 0,
                   'new_development_qa_files': 3, 'maps_written': 0, 'config_written': 0,
                   'imported_vfx_source_packages_written': 0, 'private_dll_copied': False},
    'files': files,
    'existing_qa_current_sha256': sha(MAIN / 'Source/Khazan/Tests/KZPlayerAttackCollisionPIETest.cpp'),
    'main_build': {'evidence': 'MainBuild04/Exit.json', **build, **preview,
                   'note': 'The build waited for another build. Only concurrent development-test source drift remains; all recorded runtime inputs match the current files.'},
    'final_native_batch': {'evidence': 'MainFinalQA04/Driver.json', **final},
    'additional_regressions': [
        {'evidence': 'MainGuardQA02/Driver.json', **guard},
        {'evidence': 'MainQA01/Driver.json', 'test': fall,
         'module_sha256': old['module_sha256'], 'scope': 'Previously published same feature contracts; includes fall/plunge, actual AI and conditional/projectile/field/capture paths.'}],
    'saved_assets_readback': 'MainSavedAssets01/SavedAssets.json',
    'source_tree': {'original_bt': 'Metadata/EnemyBehaviorResearch_20261008/YetugaOriginal/BT_Yetuga.json',
                    'original_bt_sha256': read('YetugaStateTreeAuthor.json')['source_sha256'],
                    'yetuga_original_nodes': 121, 'routes': 11, 'gates': 49, 'skill_nodes': 46,
                    'move_nodes': 10, 'lock_on_move_nodes': 5, 'yetuga_runtime_states': 173,
                    'apes_runtime_states': 9, 'apes_grants': 19, 'yetuga_grants': 28,
                    'yetuga_aliases': ['NormalAtk02_NoCoolTime', 'TurnBackRun_Short_Nocool', 'SideMove_Step2', 'DempseyRoll_Step3'],
                    'structure_check': 'Native SourceAudit reads compiled states, raw gate fields, exact skill classes/entry steps and action success/failure continuations.'},
    'player': {'control_lock_seconds': .1, 'control_lock_source': 'Assistant TEMP; adjustable KZHitReactionAbility.PlayerControlLockSeconds; latest accepted player non-shield reaction',
               'dodge_invulnerability_seconds': .1, 'invulnerability_source': 'User requested value; Dodge Ability owns its contribution/timer and actual world-time deadline',
               'defense_cases': 11, 'recovery_cases': 6, 'cancel_directions': 8,
               'defense_scope': 'Real melee/field/projectile GEs, before/after deadline, cancel, hit-group dedup, independent immunity contribution and cost failure',
               'recovery_scope': 'Short/Knock/Launch plus re-hit: old timer cannot unlock a new reaction; real next Dodge and CMC movement'} ,
    'feedback': {'dodge_vfx': '/Game/VFX/05_CursedMagic/NS_Cursed_Magic_Dash1',
                 'success_vfx': '/Game/VFX/05_CursedMagic/NS_Cursed_Magic_Blink1',
                 'success_sfx': '/Game/Monsters/Shared/Feedback/SW_Player_DodgeSuccess',
                 'source_audio': 'Feedback/AudioSource.json', 'source_wav': 'Feedback/Player_Dodge_Success.wav',
                 'dodge_scale_factor': .12, 'success_scale_factor': .15, 'scale_source': 'Assistant visual TEMP; factors multiply preset default float User.Scale_All before activation',
                 'runtime_evidence': 'DefensePIE confirms actual new Niagara and playing SoundWave on accepted Dodge defense; finite WAV 0.18s/48000Hz/clipping0; screenshots retained in QA evidence directories'},
    'failures_retained': [
        {'evidence': 'MainQA01/Driver.json', 'failure': 'OverFury observation ended before actual montage clock completed at low rendering frame rate; native QA now waits authored montage clock with bounded timeout, preserves expected 19 hits.', 'superseded_by': ['MainCollisionQA02/Driver.json', 'MainFinalQA04/Driver.json']},
        {'evidence': 'MainFinalQA03/Driver.json', 'failure': old_crash['error'], 'superseded_by': 'MainFinalQA04/Driver.json'},
        {'evidence': 'FinalWorkQA01/Driver.json', 'failure': 'Duplicate Parry PIE request and first OverFury observation failure; retained.', 'superseded_by': ['FinalWorkQA02/Driver.json', 'MainGuardQA02/Driver.json', 'MainFinalQA04/Driver.json']}],
    'concurrent_changes': 'Latest combat Niagara, swordsman candidate filter, plunge feedback and ARCH-96 animation/knockback changes preserved; Main canonical build used current Main source, no old Work DLL delivery.',
    'fidelity_limits': limits, 'verified_scope_checks_remaining': [],
    'full_original_parity_status': 'unverified_with_explicit_gap',
    'original_parity_remaining': limits
}
(ROOT / 'Completion/FinalVerification.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')

engineering = f'''\n\n## {stamp} — ARCH-94 Apes·Yetuga StateTree / 짧은 피격·Dodge Main 완료\n\n메인에 선택 Source21/asset19를 CAS 전달했고 기존 PlayerAttackCollision 개발 검사의 몽타주 시계 대기만 추가 수정했다(게임 Source/asset 총41, 새 runtime 파일·class·manager0, 신규 개발 QA3). `Metadata/BeastDodge_20261012/Completion/FinalVerification.json`을 후속 정본으로 사용한다. 과거 Main 미반영·검사 대기 기록은 이 완료 절로 대체하며 원래 실패·중간 보고서는 보존한다.\n\nYetuga 원본 BT121노드(Route11/Gate49/UseSkill46/MoveTo10/LockOnMove5)를 source export·원시 property·성공/실패 후속과 함께 StateTree173상태로 구체화했다. 깊은 조건/route와 skill 선택 proxy는 선택 시 transition을 따라가고 실행 leaf46개는 실제 GAS 완료/취소 결과를 반환한다. MoveTo 성공 뒤 사용할 수 없는 기술은 원래 실패 후속으로 진행한다. Apes9상태는 기존 Early 후보/추격을 재사용하며 실제 HP 피해 이력의 SideMove passive3행을 연결한다. Definition의 OriginalPatternStateTree가 기존 배치 override보다 우선한다. Apes19/Yetuga28(24+NoCool/선택 step alias4) 기술을 기존 PatternAbility·Combo/Notify/발사체/필드로 실행한다.\n\n플레이어 non-shield 피격의 마지막 실행에서0.1초 뒤 자기 montage/RMS/제약·root mode를 정리하고 다음 이동·회피를 허용한다. 이0.1초는 어시스턴트 TEMP이며 실제 조정 위치는 `KZHitReactionAbility.PlayerControlLockSeconds`다. 착수 계약의 Definition 소유 제안은 실제 구현과 달라 이 Ability 설정으로 정정한다. 몬스터/Shield 수명은 이번 단축 대상이 아니다. 동시 ARCH-96의 몬스터 curve/자기 montage root disable을 보존했다.\n\nDodge 시작0.1초 무적은 사용자 지정값이다. `State.Invulnerable`의 자기 기여만 추가/회수하며 실제 world-time deadline을 검사해 timer 지연이 무적 시간을 늘리지 않는다. melee/field/projectile/직접 capture 피해는 Guard·HP/ST·피격 적용 전에 ASC의 동일 승인 경로를 소비한다. 같은 공격 group의 회피 접촉을 소비하고 성공 표현은 한 Dodge 실행에서1회다. 종료/취소/실패의 timer·태그·자기 VFX cleanup과 타 원인의 무적 기여 보존을 확인했다.\n\nMainBuild04 stock canonical build Exit0, runtime Source hash 일치다. 기다리는 동안 동시 개발 QA 파일만 바뀐 사실은 보고서에 따로 남겼다. 최신 MainFinalQA04의 compiled SourceAudit·실제7피격 SideMove·방어11사례/8방향 취소·피격 복구6사례·Sight→Roar→전투 및 실제47기술·PlayerAttackCollision(OverFury19회)이 모두 성공했다. Guard/Parry MainGuardQA02와 낙하/거대 몬스터 연계 MainQA01 성공도 보존한다. QA03은 synchronous 감사 뒤 불필요한 PIE 요청의 viewport 종료 race였고 driver만 수정해 QA04로 대체했다. 실제 native 실행이며 저장된 테스트 actor/fixture는 없다. Shipping/network 검증은 수행하지 않았다.\n\n원작 custom BT의 native RNG/abort/CDO 생략값, Group1 부위 파괴 producer, selected-step float 및 원작 navigation/physics 의미는 미확인이다. Apes >=임계·history reset·독립 난수는 명시된 프로젝트 어댑터다. 원본 조건/연계 자료와 현재 UE 실행 검증을 원작 전체 무오차 동일성으로 확대하지 않는다. 후속은 이 보고서→기존 원작 metadata→필요한 native/원작 통제 자료만 표적 확보한다. 전체 재추출/과거 author·install/Work DLL 전달·재임포트는 반복하지 않는다.\n'''
reaction = f'''\n\n## {stamp} — 플레이어 짧은 피격 복구 / Dodge 승인 Main 완료\n\nARCH-94의 실제 반영·빌드·native 검증은 `Metadata/BeastDodge_20261012/Completion/FinalVerification.json`이다. Player non-shield HitReaction의 마지막 실행부터0.1초 TEMP(`PlayerControlLockSeconds`, Ability EditDefaultsOnly)에서 자기 실행을 끝내고 montage blend-out의 자기 root motion만 억제해 CMC 이동을 즉시 복구한다. 반복 피격은 execution serial과 timer 교체로 이전 종료가 새 실행을 풀지 않는다. Short/Knock/Launch 및 재피격 총6사례에서 조기 잠금·정상/재피격 deadline·다음 Dodge·실제 CMC 이동을 MainFinalQA04로 확인했다. Launch의 정상 Falling은 제어 실패로 오판하지 않는다.\n\nDodge 무적0.1초는 사용자 지정값이며 actual world-time deadline과 자기 `State.Invulnerable` contribution이 소유한다. melee/field/projectile/captured 피해의 공통 ASC 승인·같은 group dedup·타 기여 보존·8방향 취소·비용 실패를 확인했다. 방어11사례는 실제 GE 경로이고 성공 feedback은 실제 방어1회만 생성한다. 몬스터/Shield 수명과 동시 ARCH-96의 optional KnockbackTimeMappingCurve/자기 대체 clip root disable은 보존했다.\n'''
behavior = f'''\n\n## {stamp} — 원본 경로의 StateTree 구체화 Main 완료\n\nARCH-94로 Yetuga 원본121노드의 source property/49gate/46skill/10MoveTo/5LockOnMove·성공/실패 후속을 `ST_Yetuga_Original`173상태로 옮겼다. Apes는 `ST_Apes_Original`9상태와 기존 Early 후보, actual damage passive3행을 사용한다. original24+alias4/Apes19의 실제47기술, actual Sight→Roar→combat, deterministic7피격 SideMove 및 compiled 원시 field/정확 class·entry/후속은 최신 MainFinalQA04에서 성공했다. 과거 공통 Chase/평탄화 후보만으로 대체되던 Yetuga 전용 순서·NoCool·selected substep의 구조 제한은 이 구체화 범위에서 대체된다.\n\n정확한 전달 SHA/빌드/module/검사와 수치 출처는 `Metadata/BeastDodge_20261012/Completion/FinalVerification.json`이다. native RNG·abort·생략 CDO·Group1 producer·selected float/이동 물리 전체 동일성은 미확인이다. Apes 임계 >=/history reset/독립 chance draw는 원작 직접 검증값이 아닌 프로젝트 어댑터다. 모든 실제 UE 기술 실행 성공과 원작 native 전체 동등성을 구분한다. 후속은 저장 plan/report 및 exact package에서 부족한 근거만 확보한다.\n'''
art = f'''\n\n## {stamp} — 플레이어 Dodge·성공 회피 표현 Main 완료\n\n8방향 Dodge BP는 기존 Fab `/Game/VFX/05_CursedMagic/NS_Cursed_Magic_Dash1`(회피 자체)과 `NS_Cursed_Magic_Blink1`(실제 공격 회피 성공)을 참조한다. source NS/머티리얼/텍스처 수정0이다. 새 `/Game/Monsters/Shared/Feedback/SW_Player_DodgeSuccess`는 어시스턴트 저작 WAV0.18초/48000Hz/mono/peak0.16/clipping0/양끝0이며 원작 SFX가 아니다. 원본 WAV와 표시 TEMP는 `Metadata/BeastDodge_20261012/Feedback/AudioSource.json`에 보존한다.\n\n단위 없는0.12/0.15는 어시스턴트 표시 TEMP이고 preset의 노출 FLOAT `User.Scale_All` 기본값에 곱한 뒤 Activate한다. component scale만 바꾸거나 절대 parameter값으로 덮던 trial은 채택하지 않는다. 실제 RHI 화면에서 발 주변의 얇은 trail과 캐릭터 가독성을 확인했다. MainFinalQA04 방어 검사에서 실제 새 Niagara component와 SoundWave 재생·Dodge 종료의 자기 표현 정리를 확인한다. 성공 SFX/VFX는 피해 producer가 Dodge 방어를 승인한 경우 실행당1회만 발생한다. canonical 근거는 `Metadata/BeastDodge_20261012/Completion/FinalVerification.json`이며 gameplay 무적·제어 수명은 Engineering 기록을 따른다. 필수 잔여0, 원작 pixel/audio 전체 일치는 주장하지 않는다.\n'''
continuity = f'''\n\n## {stamp} — ARCH-94 Main 반영·현재 실행 검증 완료 / 원작 전체 동일성 미확인\n\n정본은 `Metadata/BeastDodge_20261012/Completion/FinalVerification.json`과 최신 `ResumeState.json`이다. Source22/asset19 실제 반영, MainBuild04 Exit0/runtime input hash 일치, MainFinalQA04의 SourceAudit/Passive/Defense/Recovery/47기술/PlayerAttackCollision 모두 성공, Guard/Parry·GiantFall 회귀도 성공했다. 과거 Main미반영/OverFury/Parry/최종 검사 대기는 이 검증으로 대체한다. QA03의 불필요한 synchronous 감사 PIE 요청은 driver만 수정해 QA04로 검증했다. 임시 author는 제거됐고 private DLL 전달·Config/map/원본 VFX 수정0이다. 동시 ARCH-95/96 변경을 보존했다.\n\n원작 native RNG/abort/생략값·Group1 부위 파괴 producer·selected float/물리 동일성은 남아 있다. Group1 gate만으로 완성 경로라고 부르지 않는다. 후속은 보고서→기존 정확 metadata→부족한 native 계약/원작 통제 자료 확보 순서다. 현재 검사를 재현할 때 `run_beast_dodge_editor_20261012.py`에 새 고유 label, `beast_dodge_batch_driver_20261012.py`, `--main --pie`, MainFinalQA04/Driver.json의 test목록을 사용한다. 과거 prepare/author/install 및 Work DLL 복사를 다시 실행하지 않는다. foreign editor 저장·종료·reload0이며 pending 재시작 승인을 받았다고 기록하지 않는다.\n'''
contract = f'''\n\n## {stamp} — ARCH-94 실제 소유 계약·Main 검증\n\n기존 ASC/Ability/Task/AIController/StateTree를 확장해 실제 Main에 반영했다. 새 runtime 파일·class·manager0, 개발 QA3다. Yetuga source121노드→compiled173상태, Apes9상태이며 Definition.OriginalPatternStateTree가 기존 배치 override보다 우선한다. 실행 task는 실제 PatternRun의 정상/취소 결과를 성공/실패로 반환하고 선택 실패를 원본 후속에 연결한다. passive는 AIController가 실제 accepted HP 피해 이력·pending을 소유하며 죽음/EndPlay/대상 변경 정리를 수행한다.\n\n착수 계약의 Definition 피격 시간 제안은 실제 `KZHitReactionAbility.PlayerControlLockSeconds` EditDefaultsOnly 소유로 정정한다. Player non-shield의 마지막 실행부터0.1초는 어시스턴트 TEMP이며 자기 montage/RMS/제약/root mode를 끝내 다음 입력을 허용한다. Dodge0.1초는 사용자 지정값이고 Dodge Ability의 실제 world-time deadline/자기 ASC 기여·timer가 소유한다. 모든 실제 피해 producer는 ASC의 승인 경로를 통해 Guard/피해 전에 이를 소비하고 성공 표현은 실행당1회다. 취소/실패/재피격·타 원인 기여 보존을 검증했다. 동시 ARCH-96 curve/자기 montage root 억제는 보존한다.\n\nMainBuild04 Exit0/runtime hash 일치, 최신 native 감사·passive·방어11·복구6·47개 기술·PlayerAttackCollision 및 Guard/Parry/GiantFall 성공의 정확 증거는 `Metadata/BeastDodge_20261012/Completion/FinalVerification.json`이다. 원작 native RNG/abort/defaults와 Group1 producer·selected float·물리 전체 동일성은 미확인/명시적 잔여다. 구조/원시 field/현재 UE 실행 성공을 원작 전체 무오차로 기록하지 않는다.\n'''
index = f'''\n\n## {stamp} — Dodge 표현 정본 등록\n\n`Metadata/BeastDodge_20261012/Completion/FinalVerification.json`: 8방향 Dodge의 CursedMagic Dash1/Blink1 참조, 새 SW_Player_DodgeSuccess, 실제 Niagara/Audio 검사·RHI 화면과 Main 전달 SHA. `Feedback/AudioSource.json`: 저작 WAV0.18초/48000Hz/peak0.16/clipping0 및 어시스턴트 표시 TEMP 출처. `User.Scale_All` preset기본값×0.12/0.15를 사용하며 source Fab 패키지는 변경하지 않는다. 실제 gameplay 무적·짧은 피격 계약은 Engineering ARCH-94 기록을 따른다.\n'''
records = {
    'Docs/Engineering/ENGINEERING_PROJECT_STATE.md': engineering,
    'Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md': continuity,
    'Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md': contract,
    'Docs/Engineering/COMBAT_REACTION_RUNTIME_20261008.md': reaction,
    'Docs/Engineering/APES_YETUGA_BEHAVIOR_ANALYSIS_20261008.md': behavior,
    'Docs/Engineering/APES_YETUGA_FALL_IMPLEMENTATION_20261011.md': behavior,
    'Docs/Art/ART_PROJECT_STATE.md': art,
    'Docs/Art/ART_KNOWLEDGE_INDEX.md': index,
    'Docs/Art/ART_WORK_CONTINUITY.md': art,
}
marker = '<!-- BeastDodge_20261012_MainCompleted -->'
for name, content in records.items():
    path = MAIN / name
    assert path.is_file(), name
    if marker not in path.read_text(encoding='utf-8-sig'):
        with path.open('a', encoding='utf-8') as f:
            f.write(content + '\n' + marker + '\n')
resume = {'status': 'delivered_validated_original_parity_unverified', 'timestamp': stamp, 'main_product_writes': 41,
          'final_verification': 'Completion/FinalVerification.json',
          'author_removed': True, 'verified': [r['test'] for r in final['tests']] + ['Guard/Parry', 'GiantFall', 'Saved8Dodge/2Definition'],
          'remaining': limits, 'verified_scope_checks_remaining': [], 'fidelity_limits': limits,
          'restart_approval_received': False, 'foreign_editor_quit_or_reload': False,
          'resume': 'Read Completion/FinalVerification.json; do not rerun preparation/author/installation or copy the private DLL. Native parity gaps require new source evidence, not arbitrary values.'}
(ROOT / 'ResumeState.json').write_text(json.dumps(resume, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps({'status': report['status'], 'at': stamp, 'native_tests': len(final['tests']),
                  'docs_appended': len(records), 'runtime_source_drift': len(runtime_drift),
                  'selected_asset_drift': len(asset_drift)}, indent=2))
