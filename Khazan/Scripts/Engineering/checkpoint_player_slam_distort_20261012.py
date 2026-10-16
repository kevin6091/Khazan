"""Leave exact private-build/asset state without replacing shared document histories."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import json
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Metadata/PlayerSlamDistort_20261012'
stamp=datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds')
state={'complete':False,'status':'PrivateNiagaraFloorExtension_BuildAndAuthorPending','utc':stamp,
    'work':str(ROOT.parent.parent/'Khazan_SlamDistortWork_20261012/Khazan'),'main_product_writes':0,
    'runtime_files':['Animation/Notifies/KZAnimNotify_CombatEffect.h','Animation/Notifies/KZAnimNotify_CombatEffect.cpp','Ability/KZActionAbility.cpp','Khazan.Build.cs'],
    'dev_file':'Tests/KZCombatPresentationPIETest.cpp','original_system':'/Game/VFX/03_SlashHit/KZ_Parring_Distort',
    'montage':'/Game/_Art/Player/Animation/InGame/DAS/FallAttack/AM_DAS_FallAttack',
    'last_verified':'Requested asset is NiagaraSystem; original landing KZExtra_PlungeGround Start3.741868 End3.863043. Probe01 report failed UObject.export_text, no saves. Probe02 fixes that.',
    'remaining':['Finish private build; author floor-only Niagara variant/paired child using existing marker clock.',
        'Fresh saved audit; actual owned plunge RHI/floor/cleanup and Cascade effect regression.',
        'CAS-merge only4 runtime/build+DEV1 and selected2 assets; current full Main build, fresh saved/actual validation; final domain records.'],
    'resume':'player_slam_distort_task_20261012.py; preserve Baseline/Before/PrivateBuild01/Probe files. Do not re-stage, reimport, copy private DLL or old Main Source.'}
(OUT/'ResumeState.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
marker='PlayerSlamDistort_20261012_PrivateStarted'
rows={
 'Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md':('플레이어 내려찍기 KZ_Parring_Distort 바닥 연결 착수',
    '기존 ARCH-83/92의 바닥 trace·WPO snow 및 Action receipt를 재사용한다. 요청 에셋은 Niagara이므로 기존 CombatEffect에 nullable NiagaraTemplate과 inactive factory spawn, 기존 Action의 FX 공통 activate/deactivate만 작은 확장으로 추가했다. runtime/build4·기존 DEV1은 별도 Khazan_SlamDistortWork_20261012에만 적용됐으며 Main 제품 쓰기0이다. 기존 KZExtra_PlungeGround 창3.741868–3.863043초를 재사용하고 gameplay 타이밍·피해·Input·Tag·애니메이션은 변경하지 않는다. 원본 Niagara는 보존하고 바닥용 clone의 local-space sprite facing/기하학적90도 회전을 저작한다. Probe01의 UObject.export_text API 실패는 저장0이며 Probe02에서 필드 조회로 수정했다. PrivateBuild01 실행 중; author/fresh saved/실제 plunge+Cascade 회귀/Main CAS와 current build·새 검증은 남아 있다. 정확 재개는 Metadata/PlayerSlamDistort_20261012/ResumeState.json과 Scripts/Engineering/player_slam_distort_task_20261012.py다. 이미 실행한 stage를 반복하거나 private DLL/Source 전체를 Main에 전달하지 않는다.'),
 'Docs/Art/ART_WORK_CONTINUITY.md':('요청 Niagara 내려찍기 바닥용 재사용 착수',
    '/Game/VFX/03_SlashHit/KZ_Parring_Distort는 사용자 지정 Fab Niagara6-emitter asset이며 원작 메타데이터 복원값으로 부르지 않는다. 원본 file/재질/graph는 보존하고 별도 Work의 /Game/_Art/Effects/Combat/PlayerSlamDistort/NS_Player_Plunge_ParringDistort에 바닥용 variant를 준비한다. 원본 local GPU sprite3의 FaceCamera를 CustomFacingVector로 조정하고 engine default SpriteFacing +X를 Notify 기하학적 pitch90도로 floor normal에 맞출 예정이다. scale1은 기존 system 단위 scale이고 새 gameplay tuning이 아니다. 실제 화면·alpha·부착/종료 검수는 아직 미완료다. Metadata/PlayerSlamDistort_20261012/{Probe01,Probe02,ResumeState.json}를 재개 근거로 사용하고 runtime 상세는 Engineering continuity를 따른다.')}
for rel,(title,text) in rows.items():
    p=ROOT/rel
    if marker not in p.read_text(encoding='utf-8-sig'):
        with p.open('a',encoding='utf-8') as f:f.write('\n\n## '+stamp+' — '+title+'\n\n'+text+'\n\n<!-- '+marker+' -->\n')
print('SLAM_DISTORT_CHECKPOINT',flush=True)
