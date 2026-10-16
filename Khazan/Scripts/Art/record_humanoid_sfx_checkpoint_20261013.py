from pathlib import Path
import datetime
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Metadata/HumanoidSFX_20261013'
now=datetime.datetime.now().astimezone().isoformat(timespec='seconds')
paths=['Animation/Notifies/KZAnimNotify_PlayAudio.h','Animation/Notifies/KZAnimNotify_PlayAudio.cpp','Animation/Notifies/KZAnimNotifyState_PlayAudio.cpp']
state={'time':now,'scope':['Player','Swordsman','SwordShield','HeavySwordsman','HalberdElite'],'excluded':['Yetuga','ApesStoneHandElite'],
 'status':'Current audit/source composite mapping/new31 cue resource conversion; authoring and actual QA remain',
 'inventory':'Inventory02 success:936 animations/58 combo definitions/5 character definitions/84 grant observations. Old audio events0 missing;359 clocks changed by later integer-FPS work, preserved.',
 'mapping':'17 player composite-parent canonical tracks identified; current1586-event/495-sequence plan includes45 explicit temporary ordinary damage cry dispatches.',
 'original':'34 targeted event metadata,196 missing archive bank/media files,12 reused; WWiser generated31 audible cue graphs/149 wave recipes. Two stop controls and hardware-motion event are not audible cues.',
 'source_edits':{p:hashlib.sha256((ROOT/'Source/Khazan'/p).read_bytes()).hexdigest() for p in paths},
 'assets_saved':0,'user_editor_control':0,
 'resume':['Check old-root GameplayAudio_20261011/Build_HumanoidSFX01 result (build helper output remains there).',
 'Finish new waveform decode/reuse/import with scoped plan and preserve shared settings.',
 'Fill actual Fall/DodgeAttack/Guard/Heal/Strong/Spinning source action closure; resolve control stop targets; author only Player/human tracks and current window impact/guard fields.',
 'Fresh reload and actual5-family/all Player action/hit/guard/parry/dodge/cancel/death-tail/mixer QA; record exact Main hashes and domain completion. Never copy old37 payload over new StrongVictimFront/physics/VFX data.']}
(OUT/'ResumeState01.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
art=f'''\n\n## {now} — Player·인간형4종 SFX 누락/끝음 Mixed 요청 착수\n\n현재936 animation/58 ComboDefinition/5 CharacterDefinition/84 grant를 새 background read-only process에서 읽었다. 이전1462 audio event 누락0이지만, later integer-FPS359 clock 변경은 현재 정본으로 보존한다. raw 시퀀스만 조사하던 이전 사운드 계획이 상위 원작 Composite의 Strong/Charge/Guard/Heal 등 이벤트를 놓친 것을 확인했다. 기존 InGame inverse_map 함수를 재사용해 raw parent→matching raw leaf→현재 baked clock으로 계산했다. 신규 원작34 event 표적 추출/196 bank·media+12 reuse→31 audible cue/149 leaf recipe이며 기존 chunk0/chunk1 index와 FModel settings를 재사용한다. 재전수추출0이다. 기존 ordinary reaction composite에 audio notify가 없는45 clip에는 같은 family의 원본 short cry를 첫 피격 pose에 두는 명시적 TEMP adapter를 준비했다. 동작 없는 silent loop에 임의 소리를 계속 붙이는 방식은 쓰지 않는다. 원본 시각·raw/group/gain/loop/끝음은 보존하고 native mix는 별도 TEMP로 기록한다. current PlaybackPlan01/Inventory02/ResourcePlan01/NativeCuePlan01/ResumeState01이 재개 근거이며 Main 새 asset 저장은 아직0이다. Yetuga/Apes asset·HeinMach map은 이번 scope에서 제외한다.\n'''
eng=f'''\n\n## {now} — ARCH-89 SFX coverage·natural tail 작은 확장\n\n현재 직접 요청은 Player와 인간형4종의 모든 현행 action/interaction을 대상으로 한다. 기존 ASC/Ability/Task/피해·Guard/Dodge 승인·Animation ownership를 유지한다. 새로운 runtime class/file/component/manager/tick0이다. 기존 PlayAudio Notify의 optional VolumeMultiplier(default1)와 PreserveFiniteTailOnOwnerDestroyed(defaultfalse)를 추가했다. per-source bank gain 위에 asset-authored TEMP trim을 곱하고, 적용한 finite one-shot만 actor destroy 후 자연 drain한다. loops/명시 stop은 이전 cleanup을 유지한다. EndSound도 같은 정책/볼륨을 소비한다. defaults는 scope 밖 giant 기존 data를 보존한다. 엔진 AudioComponent::OnUnregister는 owner destruction의 one-shot에 bStopWhenOwnerDestroyed=false를 지원하고 BeginDestroy는 loop만 stop한다는 source 근거를 확인했다.\n\n임시 voice0.85/footstep0.90/weapon1은 숫자 출처를 PlaybackPlan01 profile에 모았으며 원작 gain과 구분한다. 아직 실제 믹서 조정/완료 검증이 아니다. 이후 현재5 family data에만 적용하고 peak/tails/combination/cancel/loop/death output으로 조정한다. 이전 미전달37 DataAsset bytes를 복사하지 않고 최신 Main에서 audio field만 수정하여 StrongVictimFront/Root/FPS/physics/VFX·Parry 후속을 보존한다. source3 수정·build 진행/새 asset0이며 exact resume는 Metadata/HumanoidSFX_20261013/ResumeState01.json과 Art 같은 날짜 절이다. 사용자·foreign editor 제어0이다.\n'''
for rel,text in [('Docs/Art/ART_WORK_CONTINUITY.md',art),('Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md',eng),('Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md',eng)]:
 with (ROOT/rel).open('a',encoding='utf-8') as f:f.write(text)
print(now)
