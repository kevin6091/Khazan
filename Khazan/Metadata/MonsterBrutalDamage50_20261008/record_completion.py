import datetime, json, pathlib
MAIN=pathlib.Path(__file__).resolve().parents[2]; OUT=MAIN/'Metadata/MonsterBrutalDamage50_20261008'
author=json.loads((OUT/'Authoring.json').read_text(encoding='utf-8'))
saved=json.loads((OUT/'FreshSavedReadback.json').read_text(encoding='utf-8'))
assert author['success'] and saved['success'] and len(saved['rows'])==6
assert all(r['damage_after']==50 and r['other_fields_unchanged'] for r in saved['rows'])
stamp=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M KST')
marker='<!-- MonsterBrutalDamage50_20261008 -->'
body='\n\n'+marker+'\n## '+stamp+' — 브루탈 어택 총 HP 피해 임시50 설정\n\n'
body+='사용자 요청으로 Swordsman/SwordShield/HeavySwordsman/HalberdElite/ApesStoneHandElite/Yetuga의 `/Game/Monsters/<family>/Data/DA_Character_<family>` → Monster Stamina → `BrutalHPDamage`를0에서50으로 저장했다. 단위는 HP 절대량이고 원작 환산값이 아닌 사용자 지정 임시 튜닝이다. 앞/뒤 공통 브루탈1회당 총량이며 기존 `BrutalHit2`에서 한 번 적용한다. 패링·일반 공격의 Stamina 감소량과는 별개다. 이전 미할당0/조건부혈흔0 기록은 당시 검증 상태로 보존하며 현재 설정은 이 절의50을 따른다.\n\n'
body+='수정은 CharacterDefinition6개의 해당 필드뿐이다. 다른 stamina 설정·LocomotionConfig·UnawareRoutines·InitialAbilityGrants·InitialEffects를 수정 전후 및 새 별도 Main commandlet 재로드에서 동일하게 확인했다. Source/런타임 클래스/몽타주/모듈 선택은 편집하지 않았다. metadata 증거는 `Metadata/MonsterBrutalDamage50_20261008/Authoring.json`, `FreshSavedReadback.json`이며 원본6파일은 같은 경로 Before에 보존했다. 두 commandlet은 별도 프로세스로 성공 종료했고 사용자 에디터를 제어하지 않았다.\n\n'
body+='이번 검증은 저장된 값50과 다른 필드 보존의 읽기 검사다. 기존 양수 피해/중복 방지/양쪽 완료 native 검사와 VFX transient6.25 검사는 과거 결과이며50으로 PIE를 새 실행한 것으로 기록하지 않는다. 기존 확정 적중을 읽는 VFX 정책은 이제 실제 양수50 피해에 적용될 수 있으며 VFX가 추가 피해를 만들지 않는다. 조정은 같은 DA의 BrutalHPDamage에서 수행하고, 과거0인 author receipt/asset payload를 현재 설정 위에 다시 전달하지 않는다.\n'
for relative in ['Docs/Engineering/MONSTER_STAMINA_EXHAUSTION_20261008.md',
    'Docs/Engineering/ENGINEERING_PROJECT_STATE.md','Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md',
    'Docs/Engineering/PLAYER_ATTACK_VFX_RUNTIME_20261008.md']:
    path=MAIN/relative; assert marker not in path.read_text(encoding='utf-8')
    with path.open('a',encoding='utf-8',newline='') as stream:stream.write(body)
print('Recorded user temporary total HP damage50 and fresh saved verification')
