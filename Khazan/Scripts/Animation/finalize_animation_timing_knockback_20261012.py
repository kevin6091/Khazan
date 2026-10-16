from pathlib import Path
from datetime import datetime
import hashlib,json
P=Path(__file__).resolve().parents[2];O=P/'Metadata/AnimationTimingKnockback_20261012'
def read(n):return json.loads((O/n).read_text(encoding='utf-8-sig'))
assert read('MainBuild01/Exit.json')['exit']==0
assert read('MainSaved01/Driver.json')['status']=='passed'
assert read('MainSaved01/SavedAudit.json')['success']
assert read('MainKnockback01/Driver.json')['status']=='passed'
assert read('MainKnockback01/KnockbackRuntime.json')['passed']
assert read('PrivateMonsterHits01/Driver.json')['status']=='passed'
inv=read('MainInventory01/Inventory.json');assert inv['success']
assert all(s['fps'][0]%s['fps'][1]==0 and s['sampling_fps'][0]%s['sampling_fps'][1]==0 for s in inv['sequences'])
assert all(c['engine_sampling_fps'][1]==1 and c['engine_sampling_fps'][0]<100000 for c in inv['composites'])
delivery=read('Delivery.json');drift=[]
for r in delivery['files']:
 if hashlib.sha256((P/r['file']).read_bytes()).hexdigest()!=r['after']:drift.append(r['file'])
assert not drift,drift
stamp=datetime.now().astimezone().isoformat();saved=read('MainSaved01/SavedAudit.json');rt=read('MainKnockback01/KnockbackRuntime.json')
final={'status':'MainDeliveredAndFreshVerified','complete':True,'date':stamp,'files':delivery['files'],
 'source_count':5,'asset_count':511,'new_runtime_classes':0,'new_runtime_files':0,'dll_delivery':0,'config_delivery':0,
 'sequences_normalized':461,'montages_rebound':45,'fractional_sequence_clocks_after':0,'amplified_montage_clocks_after':0,
 'current_inventory_counts':{'sequences':len(inv['sequences']),'montages':len(inv['composites'])},
 'unchanged_bone_keys':saved['unchanged_bone_keys'],'maximum_montage_seconds_difference':saved['maximum_montage_duration_error'],
 'concurrent_attack_effects_preserved':88,'numeric_provenance':'New raw seconds=existing frame count/nominal integer clock30 or60; alpha=new/old seconds; new RateScale=old RateScale*alpha. Local events/markers/presentation curve time/tangents and source trim map by alpha. No bone-key resampling.',
 'montage_clock_policy':'Integer sampling/display derives from sequences. Existing montage precision-model clock retained to preserve exact runtime seconds on reload.',
 'knockback':'Human4: previous250cm and HitLand deadline retained, assistant TEMP normalized2u-u*u curve adds deceleration. Apes/Yetuga original NoAir/NoBlow replacement instance suppresses paired-grapple root travel; no shared source sequence/root option edit.',
 'runtime_cases':len(rt['cases']),'runtime':'MainKnockback01/KnockbackRuntime.json','saved':'MainSaved01/SavedAudit.json',
 'build':'MainBuild01/Exit.json','inventory':'MainInventory01/Inventory.json','collision_regression':'PrivateMonsterHits01/Driver.json',
 'actual_loaded_module':read('MainKnockback01/Driver.json')['actual_loaded_module'],'module_sha256':read('MainKnockback01/Driver.json')['module_sha256'],
 'editor_control':'Task-owned processes only; user/foreign editor save/reload/PIE/terminate0.',
 'remaining_required':[],'limits':'Knockback deceleration curve keys are explicit assistant TEMP; original CV_common_groundKnock_strong reference confirmed but original curve keys/native use not recovered. No full original-game visual/native/network/shipping parity claim.'}
(O/'FinalVerification.json').write_text(json.dumps(final,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(O/'ResumeState.json').write_text(json.dumps({'status':final['status'],'complete':True,'final':'FinalVerification.json','remaining_required':[]},indent=2)+'\n',encoding='utf-8')
eng=f'''\n\n## {stamp} — ARCH-96 몬스터 넉백·전체 FPS Main 완료\n\nMain516행=기존 runtime2(KZHitReactionAbility.cpp/CharacterDefinition h)+DEV2/Build editor dependency1+asset511을 선택 적용하고 새 Main build/reload/실제 RHI를 확인했다. 기존 ASC·HitReaction/JumpForce Task·Definition과 취소/root-mode·회복 수명을 재사용했다. 새 runtime class/file/manager/tag0, private DLL·Config 전달0이다. 다른 작업의 Player0.1초 제어 제한/ground-hit 분류/원작 StateTree 추가와 최신 공격 VFX88개를 보존했다.\n\nMainBuild01 exit0, MainSaved01의461 sequence3854855 bone key/notify GUID·시각·158 montage의 actual sampling 및 재생 시간 차이0, MainKnockback01의6종11case(인간 F/B8/Giant2/벽1)·회복/재피격/cancel/root-mode 복구, 기존 실제 monster collision 회귀가 성공했다. MainInventory01의 전체{len(inv['sequences'])} sequence/{len(inv['composites'])} montage에서 소수 sequence/model·sampling0,100000fps fallback0이다. native loaded module/516SHA/각 evidence는 Metadata/AnimationTimingKnockback_20261012/FinalVerification.json에 결속했다.\n\n인간4종은 기존250cm와 실제 HitLand 시간을 유지하며 Definition.KnockbackTimeMappingCurve에서 normalized2u-u² TEMP 감속을 조정한다. baseline 착지 직전 약278–375cm/s의 일정속도 → 최종 약8–28cm/s로 줄어든다. RootSource 제거는 엔진의 MarkedForRemoval/다음 이동 tick 삭제를 구분해 검증했다. Apes/Yetuga는 NoAir/NoBlow 대체 clip의 짝 grapple root 이동을 해당 실행 instance만 PushDisableRootMotion으로 억제하여 baseline−278.01/−222.11cm →0cm다. source clip/raw/root 옵션 및 Short fallback·정상 Launch Task는 보존했다.\n\n필수 잔여0이다. 현재 editor는 정상 재시작으로 새 C++/asset cache를 로딩한다. 사용자/foreign editor 제어0이며 이전 pending·failed trial 기록은 이 완료로 대체한다. 원작 curve keys/전체 pose·native/network/shipping parity는 미확인이고 TEMP를 원작 수치라고 부르지 않는다. 과거 author/추출/원본 retime/root repair/옛 DLL 전달을 다시 실행하지 않는다.\n'''
art=f'''\n\n## {stamp} — 전체 정수 FPS·몽타주 표시 증폭 수정 Main 완료\n\n원인: UE5.8 UAnimMontage::UpdateCommonTargetFrameRate가 호환되지 않는 source sampling rates를 만날 때 CommonTargetFrameRate를 무효화하고 UAnimCompositeBase의100000/1fps precision fallback을 사용한다. 원본 전체 inventory2674/158에서 fractional461/fallback36이었다. import의 (frames−1)/exact source or dilation duration으로 생성된 rational FPS가 근거이며 재생 자체가100000배 빨라진 것으로 혼동하지 않는다.\n\n461 sequence를 nominal30/60Hz로 변환하고 frame-index bone keys3854855개를 그대로 보존했다. raw duration=Dnew=N/Fint, alpha=Dnew/Dold, RateScale_new=RateScale_old×alpha로 실제 seconds를 유지한다. notify/marker local seconds·embedded visual scalar/vector curve X와 slope/weighted tangent·montage source trim 좌표를 함께 변환했다. 원본 TimingContract/metadata는 보존하고 IntegerFPSRepair tag를 덧붙였다.45 의존 montage의 표시 sampling은 모두 정수다. montage DataModel 자체를 강제 정수 grid로 바꾸는 trial은 reload 시 실제 length를 반올림하여 철회했고, 원래 precision model clock은 보존했다.\n\nfresh Main의 모든{len(inv['sequences'])} sequence/{len(inv['composites'])} montage에서 fractional sequence0/fallback0; MainSaved01은 실제 montage length 차이0·raw key/notify 일치를 확인했다. concurrent Main Niagara attack VFX88개는 최신 저장본에서 다시 보정하고 원본 pose hash/신규 notify를 보존했다. 현재 Enemy 조회는 Metadata/AnimationTimingKnockback_20261012/CurrentAnimationLibrary_IntegerFPS.csv(813행/270수정)와 전체 Plan/FinalVerification을 사용한다. 예전 CSV는 변환 전 역사값이다. original game metadata numbers와 clock 계산/knockback TEMP 표현은 구분한다. FPS 수정 과정에서 skeleton/root tracks/material/HP·ST/공격 geometry·world clock을 재저작하지 않았다.\n'''
for rel in ['Docs/Engineering/ENGINEERING_PROJECT_STATE.md','Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md','Docs/Engineering/COMBAT_REACTION_RUNTIME_20261008.md','Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md','Docs/Engineering/CHARACTER_TAG_ABILITY_MIGRATION.md']:
 with(P/rel).open('a',encoding='utf-8') as f:f.write(eng)
for rel in ['Docs/Art/ART_PROJECT_STATE.md','Docs/Art/ART_WORK_CONTINUITY.md','Docs/Art/ART_KNOWLEDGE_INDEX.md','Docs/Art/ENEMY_ANIMATION_ORGANIZATION_20261007.md','Docs/Art/COMBAT_REACTION_ANIMATION_AUDIT_20261008.md']:
 with(P/rel).open('a',encoding='utf-8') as f:f.write(art)
with(P/'0_DOCUMENT_ROUTER.md').open('a',encoding='utf-8') as f:f.write(f'''\n\n## {stamp} — ARCH-96 넉백·몽타주 FPS Main 완료 조회\n\nMixed. Architecture 최신 ARCH-96 완료 → COMBAT_REACTION_RUNTIME_20261008.md와 Art ENEMY_ANIMATION_ORGANIZATION_20261007.md 최신 절 → Metadata/AnimationTimingKnockback_20261012/FinalVerification.json/CurrentAnimationLibrary_IntegerFPS.csv. Main516/build/fresh raw3854855·montage158/실제6종11case/전체FPS가 완료됐다. 기존 precision montage model과 정수 displayed sampling 구분·TEMP·원작 미확인 범위를 유지하며 과거 전체 author/retime/Root repair/옛 alias 전달은 반복하지 않는다.\n''')
print('ANIMATION_TIMING_KNOCKBACK_MAIN_COMPLETE',stamp)
