from pathlib import Path
import json

base = Path(__file__).resolve().parent
root = base.parents[1]
report = json.loads((base / 'FinalVerification.json').read_text(encoding='utf-8'))
assert report['status'] == 'complete_main_saved_built_and_actual_walking_pie_verified'
marker = '<!-- HeinMachPortal_20261015_readback05 -->'
body = f'''

## 2026-10-15 — Readback05 최종 스냅샷 보충

동시 Main 저장 뒤 fresh Readback05(save0)가 포탈/arrival2 actor의 참조·transform·범위·암전 시간과 전용4asset/공유 원본 보존을 다시 통과했다. 최종 확인 map SHA는 `{report['map_sha256']}`, 영수증 시각은 `{report['utc']}`다. 기존10009 actor 동일과 별도 PlayerStart1 수정, 이 작업 밖의 추가 actor {report['concurrent_additional_actor_count']}개를 구분해 보존했다. 앞선 Readback04 기록은 해당 시점의 기록으로 유지하며 최신 근거는 FinalVerification.json의 Readback05/RHI06이다. 실제 walking·암전·전장 이동·복구 Success 이후 게임 Source/자산을 추가 수정하거나 사용 중인 editor를 reload/save하지 않았다. 현재 요청의 필수 잔여0이다.

{marker}
'''
paths = ['Docs/Engineering/HEINMACH_YETUGA_PORTAL_20261015.md',
         'Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md',
         'Docs/Art/HEINMACH_YETUGA_PORTAL_20261015.md',
         'Docs/Art/ART_WORK_CONTINUITY.md']
for relative in paths:
    path = root / relative
    if marker not in path.read_text(encoding='utf-8-sig'):
        with path.open('a', encoding='utf-8', newline='\n') as stream:
            stream.write(body)
print('Final snapshot continuity appended; no game changes.')
