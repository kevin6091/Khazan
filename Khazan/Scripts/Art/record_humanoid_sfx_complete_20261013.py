"""Record only observed Main delivery, saved/native/mixer results, append docs."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import math

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Metadata/HumanoidSFX_20261013'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
now=datetime.now().astimezone().isoformat(timespec='seconds')
saved=read(OUT/'MainSavedFinal01/SavedAudit.json');assert saved['success']
delivery=read(OUT/'MainDelivery01/Delivery.json');assert delivery['complete']
mixer=read(OUT/'MixerStage02_RHI/Driver.json');assert mixer['status']=='passed' and len(mixer['observations'])==78
first=read(OUT/'MainInteraction01/Regression.json')
tests=first['tests'][:3]
assert all('Success' in t['completion'] and not t['output']['clipped_samples'] for t in tests)
for name in ['MainParry03_Balanced','MainDodge01']:
    result=read(OUT/name/'Regression.json');assert result['status']=='passed'
    tests+=result['tests']
plan=read(OUT/'AudioAuthoringPlan01.json');stage=read(OUT/'Stage01.json')
hashes={r['relative']:hashlib.sha256((ROOT/r['relative']).read_bytes()).hexdigest() for r in stage['isolated']}
module=read(ROOT/'Binaries/Win64/UnrealEditor.modules')['Modules']['Khazan']
fact={'complete':True,'time':now,'scope':plan['scope'],'excluded':['Yetuga','ApesStoneHandElite'],
    'inventory':{'animations':936,'combo_definitions':58,'character_definitions':5,'ability_grant_observations':84},
    'saved':saved,'delivery':{'assets':len(stage['isolated']),'applied':len(delivery['applied']),'already_applied':len(delivery['already_applied']),
        'locks':0,'conflicts':0,'current_sha256':hashes},
    'resources':{'original_event_cues_added':51,'wave_recipes':262,'new_imported_waves':248,'fallback_recipes':0,
        'both_chunks':'Reused verified Index03 covering chunk0 and chunk1; all additional packages targeted, no whole archive rescan'},
    'mixer':{'actual_fixtures':78,'completion':mixer['native_completion'],'master':mixer['output'],'destroyed_owner_tail':mixer['destroyed_owner_tail'],
        'family_capture_count':len(mixer['family_captures']),'clipped_samples':0},
    'actual_interactions':tests,'numeric_policy':{'source':'Original event/media, bank leaf gain/randomization, source curves and source/inverse timeline maps retained.',
        'temporary':{'voice':.85,'footstep':.9,'weapon':1.,'stop_fade_min_seconds':.08,'parry_cue_gain':.5,
            'callback_adapter_count':72,'callback_timing':'First actual action/reaction pose when native original timestamp is not serialized'},
        'parry_headroom':{'before_peak':.999847412109375,'after_peak':.76812744140625,'after_headroom_db':-20*math.log10(.76812744140625)}},
    'preserved':'Fresh native comparison: animation raw tracks/curves/frame rate/root settings + non-audio notify fields/GUID/clocks; current attack non-audio fields. No level/ambient/giant reauthor.',
    'runtime_source':['KZAnimNotify_PlayAudio.h','KZAnimNotify_PlayAudio.cpp','KZAnimNotifyState_PlayAudio.cpp'],
    'new_runtime_class_file_manager_tick':0,
    'module':{'selected':module,'sha256':hashlib.sha256((ROOT/'Binaries/Win64'/module).read_bytes()).hexdigest(),
        'verified_stage_module':read(OUT/'StageModule04.json')},
    'limitations':['Native UE distance/reverb/panning and interpolation adapters are not Wwise SDK DSP/sample parity.',
        '72 explicit native-callback presentation adapters have no original serialized dispatch timestamp.',
        'Shipping build, subjective listening across every device, and original-game full audio parity are not validated.'],
    'failed_attempts_preserved':['Main file locks:SpatialAuthor02/Author02; resolved by fresh isolated stage and guarded atomic delivery.',
        'SavedStage01/02 old same-foot duplicate outside KZAudio; class-only native DEV clear fixed and all saved checks passed.',
        'MainInteraction01 sequential restart lost Parry actor; fresh MainParry02/03 passed, no game behavior change for that failure.',
        'MainParry01 raced a separate module rebuild; fresh canonical MainParry02/03 passed.',
        'Debugger attach happened after completed mixer; owned breakpoint removed, user baseline unchanged, no session created.']}
(OUT/'FinalVerification.json').write_text(json.dumps(fact,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'ResumeState04.json').write_text(json.dumps({'complete':True,'time':now,'final':'FinalVerification.json',
    'remaining_required':[],'resume':'Read Router/domain latest final + FinalVerification; do not repeat source extraction/full author/old37 payload/old DLL delivery. Scope further sound changes to current owners and measured failures.'},indent=2),encoding='utf-8')
marker='<!-- HumanoidSFX_20261013_MainComplete -->'
art=f'''\n\n## {now} — Player·인간형4종 SFX 현재 동작·상호작용 Main 완료\n\n현재936 animation/58 ComboDefinition/5 CharacterDefinition/84 grant를 조사해 원작 상위 Composite 음원 누락, 저장되지 않았던 공격 audio array binding, 같은 발/초기 cry·Guard 성공 중복을 보완했다. Main 최종1682 audio/control occurrence·527sequence(소리 제거 callback-only3 포함)·35combo/174attack window·Dodge8 성공음이 저장됐다. 원작 추가51cue/248new wave(262recipe, 동일 원본 재사용14), fallback0이며 원래 chunk0/chunk1 index에서 필요한 metadata/bank/media만 표적 추출했다. Yetuga/Apes·map/ambient 재author0이다. 원작 random choice/gain/media tail/source curve와 현재 Root/FPS/physics/VictimFront·Slash/Parry/피격 VFX 제거를 보존했다.\n\n새 사본의78 actual mesh montage/모든 예상 cue·cancel/loop cleanup·AT actual owner destroy/PCM tail passed, Main 실제 CombatEffect/PlayerAttackCollision/Guard/Parry17/Dodge11 및 현재524+callback3 fresh saved/native pose/curve/root/GUID·non-audio 보존이 passed다. actual master peak.5539245605/RMS.0203483704/clipping0, actor destroy 후 tail peak.0198669434가 관측됐다. Main parry의 near-full-scale.999847을 보고 해당 cue 상단만 TEMP gain.5(−6.02dB)로 낮췄고 실제 재검증 peak.768127/clipping0이다. Dodge 성공은 원본 SC_efx_pc_common_justdodge를 기존 승인 callback에서 실행당 한 번 재생한다. 570asset 선택 전달은 baseline SHA guard/atomic 교체로535새 전달+35동일/lock0/conflict0이며 MainSavedFinal01은1682/527/174/8/238cue success다.\n\nTEMP voice.85/foot.9/weapon1, source stop 최소.08초, native reverb send.05/.15 및 원작 native callback이 직렬화되지 않은72 first-pose adapter를 원작 직접값과 구분한다. 유한 단발음은 action transition/owner destroy 뒤 자연 끝음 유지, loops/source stop만 fade한다. Wwise SDK DSP·모든 장치 주관 청취·Shipping·완전 원작 음향 일치는 미검증이다. 실패도 보존했고 현재 필수 잔여0이다. 정확한 원본/event/field·타임라인/수치·WAV·Main SHA는 Metadata/HumanoidSFX_20261013/FinalVerification.json 및 같은 root의 계획/보고를 따른다. 이전 prepared37이나 전체 extraction/author/old DLL 복원을 반복하지 않는다.\n'''
eng=f'''\n\n## {now} — ARCH-89 current humanoid·Player SFX Main 완료\n\n실행 상태/승인은 기존 ASC/Ability/Task·attack hit group/Guard/Dodge가 소유하고 표현은 기존 PlayAudio Notify를 재사용한다. runtime Source3에 optional VolumeMultiplier(default1), finite owner-tail(defaultfalse)와 EndSound 동일 정책만 확장했다. 해당5family authored Notify만 finite tail을 보존하며 scope 밖 default/giant data는 이전 계약을 유지한다. Body impact는 수신자 Definition, 무기 impact/Guard는 현재 attack window, 회피 성공은 기존 TryAvoidHit once-per-execution이 소유한다. 같은 성공 SFX를 Suc pose에서 또 재생하지 않는다. 새 runtime class/file/component/manager/tick0이다.\n\n기존 DEV Audio Editor에 protected Python array 대신 audio class2-only clear/no-save command, Audio PIE에 sample-plan/actual cue coverage/owner destroy tail, Dodge QA에 실제 authored SuccessSound reflection만 추가했다. build01–04 성공, 현재 Main final saved1682/527/174/8/238cue, full fresh pose/root/curve/FPS/nonaudio notify/GUID 보존 및 실제78 mixer·메인 melee/Guard/Parry17/Dodge11이 passed다. Source/자산/검증 hash·실패/버전은 Metadata/HumanoidSFX_20261013/FinalVerification.json 정본이다. 실제 핵심 root/FPS/physics/VictimFront·Parry/Slash/피격 VFX 제거 변경을 유지했고 기존37prepared bytes를 덮어쓰지 않았다.\n\n유한음은 owner destroy/몬타주 취소 후 자연 drain, loops/명시 source stop만 fade하며 새 shared mutable notify state나 MainAnimInstance member/timer를 만들지 않는다. source 수치/계산과 명시 TEMP .85/.9/1/.08s 및 측정 기반 parry cue.5·미직렬화72callback first-pose adapter를 구분한다. 원작 DSP/sample/frame 전체 동일·Shipping·전 장치 청취는 별도 검증 범위다. 필수 잔여0이며 사용자 editor·foreign process 제어0, 현재 완료를 이전 pending37/locked/prepared 기록보다 우선한다.\n'''
for rel,body in [('Docs/Art/ART_PROJECT_STATE.md',art),('Docs/Art/ART_WORK_CONTINUITY.md',art),
                 ('Docs/Engineering/ENGINEERING_PROJECT_STATE.md',eng),('Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md',eng),
                 ('Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md',eng),('Docs/Engineering/CHARACTER_TAG_ABILITY_MIGRATION.md',eng)]:
    file=ROOT/rel
    if marker not in file.read_text(encoding='utf-8-sig'):
        with file.open('a',encoding='utf-8') as f:f.write(body+'\n'+marker+'\n')
knowledge=f'''\n\n## {now} — 인간형4·Player SFX 재사용 근거\n\n`Metadata/HumanoidSFX_20261013/FinalVerification.json`이 현재 Main 완료 정본이다. `Inventory02/Inventory.json` current936/58/5/84, `PlaybackPlan01.json` source-parent→raw/inverse map 및 현재 prefix/crop, `AudioAuthoringPlan01.json` final1682/527·source event/field/clock/TEMP/stop, `Coverage01.json` current bound275/quiet hold·approved callback 분류, `NativeCuePlan01.json` 추가원작51cue/262recipe/fallback0, `NativeDecodedImport01.json` original SHA/trim/media reuse, `BankNodeFacts.json` 원본 Wwise action/volume/random/attenuation fields를 재사용한다. `Events01–04/Raw01–04`는 표적 원본 추가이며 기존 two-chunk Index03을 재전수하지 않는다. `Stage01/MainDelivery01`은 최신 Main baseline 보호·선택570 전달, `MainSavedFinal01`은 실제 저장 보존이다. `MixerStage02_RHI` actual78/WAV/finite-tail, `MainInteraction01` 첫3 성공, `MainParry03_Balanced`17성공·peak.768127, `MainDodge01`11성공·original JustDodge/foot+body cue 관측을 구분한다. stale sequential-Parry expired와 raced build 실패를 완료 증거로 읽지 않는다. 임시 callback72/voice.85/foot.9/weapon1/stop.08/parry.5·native sends와 원작 field 직접값/계산을 분리한다.\n'''
file=ROOT/'Docs/Art/ART_KNOWLEDGE_INDEX.md'
if marker not in file.read_text(encoding='utf-8-sig'):
    with file.open('a',encoding='utf-8') as f:f.write(knowledge+'\n'+marker+'\n')
router=f'''\n\n## {now} — Player·인간형 SFX 누락/끝음 Main 완료 조회\n\nMixed. Architecture ARCH-89 최신 완료→Migration/Engineering·Art continuity→Metadata/HumanoidSFX_20261013/FinalVerification.json / ResumeState04.json 순서다. 현재 원작 추가51cue/248wave·final1682 sound/control·527seq/35combo/174window/8Dodge 성공과 actual78 mixer/메인 hit·Guard·Parry·Dodge/fresh saved 보존이 완료됐다. Yetuga/Apes·map/ambient 재author는 제외했다. 원본/계산/TEMP와 Wwise DSP 미일치를 구분하며 과거 pending37/full extraction/full author/old DLL 복원을 반복하지 않는다.\n'''
file=ROOT/'0_DOCUMENT_ROUTER.md'
if marker not in file.read_text(encoding='utf-8-sig'):
    with file.open('a',encoding='utf-8') as f:f.write(router+'\n'+marker+'\n')
print('COMPLETE',now,'Main1682/527/174/8, actual78+5interaction suites, source/asset preservation')
