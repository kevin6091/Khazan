from pathlib import Path
from datetime import datetime
import csv, json
ROOT = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT = ROOT/'Metadata/EnemyAnimationOrganization_20261007'
pre = {r['old']:r for r in json.loads((OUT/'Preflight.json').read_text(encoding='utf-8'))['rows']}
rename = {r['old']:r for r in json.loads((OUT/'RenamePlan.json').read_text(encoding='utf-8'))['rows']}
audit = json.loads((OUT/'SavedAnimationAudit.json').read_text(encoding='utf-8'))
with (OUT/'CurrentAnimationLibrary.csv').open('w',newline='',encoding='utf-8-sig') as stream:
    fields=['Family','Category','CurrentAsset','LegacyAsset','OriginalPackage','TimelineDerivation','Frames','FPS','Seconds','RateScale','RootBone','EnableRootMotion','ForceRootLock','RootLock']
    writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
    for row in audit['sequences']:
        old=row['source_before'];r=rename[old];p=pre[old]
        writer.writerow(dict(Family=row['family'],Category=row['category'],CurrentAsset=row['asset'],LegacyAsset=old,
                             OriginalPackage=r.get('original_package',''),TimelineDerivation=r.get('derivation',''),Frames=p['frames'],FPS=f"{p['fps'][0]}/{p['fps'][1]}",Seconds=row['length'],RateScale=row['rate_scale'],RootBone=row['root'],EnableRootMotion=True,ForceRootLock=True,RootLock='AnimFirstFrame'))
title='\n\n## 2026-10-07 17:52 KST — Enemy 정리 적용 및 stock 검증 checkpoint\n\n'
engineering='별도 MonsterWork21492/DevMap/renderoffscreen에서 검증 중이다. Source2+development test1만 수정, 신규 runtime 파일0. author helper cpp/dependency 제거 및 최신 Main 비관련 Source/Config intake89 완료, stock cold build10action/30.36초 Succeeded. 22 신규 data-only ComboAction 패턴 생성 성공, 기존13을 더해35(5/3/7/20), Attack68클립 saved readback coverage 완료. interval2..4→2/1.1..4/1.1초, combo.75→.85, ChaseReactionSeconds.4초는 임시 조정값이다. 현재 행동 완료 계약을 보존하고 Chase Task의 기존 TimeRemaining으로 반응 대기를 처리한다.\n\nSourceAudit는813시퀀스/18,958,755 raw transforms와 곡선·마커·재생률/메타데이터 비교가 동일하다. 압축 루트 샘플44 translation+1 quaternion 항목은 과도하게 엄격한 기술 허용 오차로 실패했고 실패 로그를 보존했다. 실제 최대 positional 차이는.0060654cm이므로 최종 test는 .01cm 및 normalized quaternion angular1e-4rad QA 허용치를 사용한다(게임 수치가 아니다). 변경 test는 아직 새 build 전이다. 실제4종/35attack/8방향 보행/HP/cleanup Monster.PIE가 현재 진행 중이며 관측420에서 새 BackDashCounter Action의 capsule velocity/변위를 확인했다.\n\nMain21248은 최신 read-only audit에서 DevMap/PIE없음/dirty0였다. 제품 코드·에셋 Main 전달은 아직 없다. 다음: native PIE 결과 저장→CombatPolicyPIE/WaitingPIE 및 Heal/Guard 필요한 회귀→own 정상 종료→최종 stock QA precision build/SourceAudit success→최신 Main SHA guard/선택 전달/현재 Main build와 saved reload. Main의 Snow/PlayerParts와 기존 모듈 alias를 보존한다. mailbox 다음421, owned PID21492만 제어한다.\n'
art='별도 workspace에서 original769(Art676+gameplay93) 시퀀스와 기존 montage33 rename/options 저장, 신규 gameplay44+montage22가 생성돼 최종813시퀀스/55montage다. 12category로 분류했으며 Archer는 제외한다. CurrentAnimationLibrary.csv가 현재 경로, 과거 경로, original package, timeline derivation, frame/FPS/length/RateScale/root/options를 연결한다. 원본 export CSV의 역사적 경로를 현재 경로로 오해하지 않는다.\n\nroot bone0/첫 트랙 일치 전부 검증, Root765/Weapon_R1/B_Rock3은 source676+game93 기준이다. root/pose 재작성·Skeleton/Actor scale 변경·retime/reimport 없음. EnableRootMotion=true/ForceRootLock=true/AnimFirstFrame 저장 readback813 passed. 4 NPC ABP는 기존 RootMotionFromMontagesOnly를 유지해 몽타주의 이동을 소비하고 Nav 보행은 기존 CMC/foot placement로 구동한다. 전체 sequence 옵션 활성화와 root-driven Nav 보행 구현을 구분한다.\n\nAssetTools fixup는801옛 경로를 이미 제거한 뒤 catalogue 로딩에서 완료를 못했고 owns16212만 종료했다. debugger는 engine PDB가 없어 GameThread top unknown/지역값 없음으로 원인 미확정; agent breakpoint 모두 제거, 사용자 breakpoint 변경0. 첫 commandlet의 없는 옛 패키지801 에러는 보존했다. 마지막 남은 YetugaRockSmall redirector는 fresh registry refs0 확인 후 정확한2package commandlet로 정상 삭제(0error)했다. 재시작 saved audit의 remaining old packages=[]다. Main 미전달, runtime 검증/선택 전달 후 정본 ENEMY_ANIMATION_ORGANIZATION_20261007.md에 최종 결과를 기록한다.\n'
for relative,note in [('Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md',engineering),('Docs/Art/ART_WORK_CONTINUITY.md',art)]:
    with (ROOT/relative).open('a',encoding='utf-8') as stream:stream.write(title+note)
print('Current library and resumable checkpoint written')
