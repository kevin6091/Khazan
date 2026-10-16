"""Freeze selected current Main bytes and stage current C++ in the existing private author project."""
from pathlib import Path
from datetime import datetime, timezone
import json, shutil, hashlib
MAIN=Path(__file__).resolve().parents[2]
WORK=Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan')
OUT=MAIN/'Metadata/MonsterBloodReference_20261012'
manifest={'utc':datetime.now(timezone.utc).isoformat(),'selected':{},'staged_source':{}}
selected=['Source/Khazan/Character/KZMonster.cpp','Source/Khazan/Character/KZMonster.h','Content/_Art/Effects/Combat/Blood/FP_Monster_HitBlood.uasset','Binaries/Win64/UnrealEditor.modules']
for rel in selected:
    src=MAIN/rel;dest=OUT/'Before'/rel;dest.parent.mkdir(parents=True,exist_ok=True)
    assert not dest.exists(),str(dest);shutil.copy2(src,dest);manifest['selected'][rel]=hashlib.sha256(src.read_bytes()).hexdigest()
for src in (MAIN/'Source/Khazan').rglob('*'):
    if src.suffix not in ['.cpp','.h']:continue
    rel=src.relative_to(MAIN);dest=WORK/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
    manifest['staged_source'][str(rel)]=hashlib.sha256(src.read_bytes()).hexdigest()
shutil.copy2(MAIN/selected[2],WORK/selected[2])
ref=Path('C:/Users/user/AppData/Local/Temp/ai-chat-custom-attachment-temp-file-540d730b-a65d-42a0-9771-a18462d3f752-6570571023603619246.png')
shutil.copy2(ref,OUT/'Reference.png');manifest['reference_sha256']=hashlib.sha256(ref.read_bytes()).hexdigest()
(OUT/'Baseline.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
for path,text in [
('Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md','\n\n## 2026-10-12 — ARCH-88 사진 기준 혈액/지면 혈흔 후속 계약\n\n사용자의 첨부 Reference.png 직접 수정 요청으로 기존 floor blood 전면 억제를 이번 피격 표현에 한해 대체한다. 기존 accepted-hit producer와 AKZMonster::PlayHitBlood, 엔진 Cascade/SpawnDecalAtLocation을 재사용한다. 실제 피해 승인·dedup·취소·GAS/사망/UI/사운드는 그대로이며 새 runtime 파일/class/manager0이다. GT에서 현재 피격 지점→월드 지면 trace로 표면과 normal을 확인하고 해당 지면에만 불규칙한 원본 texture의 혈흔을 유한 수명으로 생성한다. 피 분사는 큰 sheet/덩어리와 미세 방울의 복수 층을 기존 HitBloodEffect asset에 저작한다. 설정은 현행 Monster Class Defaults/particle/material parameters에 모으고 원작 직접 값과 사진 비교 TEMP를 구분한다. Work에 최신 Main C++를 stage하되 private author/build 의존성은 Main에 전달하지 않는다. Main 사용자 editor PID19752는 제어하지 않으며 fresh own editor에서 검증한다. 이 절은 착수 계약으로 아직 적용/build/PIE 완료가 아니다. 근거·exact baseline은 Metadata/MonsterBloodReference_20261012/Baseline.json이다.\n'),
('Docs/Art/MONSTER_PRESENTATION_REPAIR_20261011.md','\n\n## 2026-10-12 — 첨부 사진 기준 혈액·바닥 혈흔 후속 착수\n\n최신 사용자 요청은 큰 검붉은 분사와 넓고 불규칙한 바닥 혈흔이며 이전 바닥 혈흔 제거 지시를 이 후속 표현에 한해 대체한다. 첨부는 Metadata/MonsterBloodReference_20261012/Reference.png로 byte 보존한다. 관찰: 작은 점만 아니라 뭉친 혈액/찢어진 sheet/주변 방울, 지면의 긴 번짐·가느다란 가지·불규칙한 빈 경계가 함께 보인다. 원본 FT_Decal_Blood_* packed texture 및 현재 blood resources를 표적 조사하고 공용 원본/기존 사망·UI를 일괄 덮어쓰지 않는다. burst/크기/지속 시간은 screenshot에서 원작 숫자를 직접 확인할 수 없으므로 명시한 TEMP asset/default 설정으로 조정한다. 구현/검증 결과는 하단에 추가한다.\n')]:
    with (MAIN/path).open('a',encoding='utf-8') as f:f.write(text)
print('BASELINE_AND_WORK_SOURCE_STAGED',len(manifest['staged_source']))
