"""Append Contact55 completion records only after successful final verification."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

ROOT = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT = ROOT / 'Saved/ImportReports/HeinMachSnow_20261006/Contact55_20261007'
MARKER = '<!-- HeinMachSnow_Contact55_20261007_complete -->'


def main():
    proof = OUT / 'FinalVerification.json'
    assert proof.is_file(), 'Run Contact55 finalize successfully before appending completion records'
    result = json.loads(proof.read_text(encoding='utf-8'))
    assert result['success'] is True and result['main']['native_pie_passed'] is True
    assert result.get('canonical_map_pending', False) is False, 'Canonical map handoff must finish before completion records'
    pid = result['main']['pid']
    delivery = json.loads((OUT / 'Delivery.json').read_text(encoding='utf-8'))
    module_name = Path(delivery['module']).name
    foot, weapon = result['foot_depth_cm'], result['weapon_depth_cm']
    perf = result['performance']
    stamp = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M KST')
    heading = f'\n\n{MARKER}\n## {stamp} — 눈 최대55cm·발35cm·무기50cm와 발 범위 축소 메인 완료\n\n'
    evidence = 'Saved/ImportReports/HeinMachSnow_20261006/Contact55_20261007'
    verified_map = result.get('native_verified_map_asset', result['main'].get('map_asset', '/Game/Maps/L_HeinMach_Environment'))
    map_scope = f'실제 fresh main native PIE 검증 맵은 {verified_map}다. '
    if result.get('canonical_apply_evidence'):
        map_scope += 'Preview 맵을 실제 검사했고 원본 /Game/Maps/L_HeinMach_Environment는 사용자 에디터 종료 후 baseline SHA가 같을 때만 known Stage authored copy를 atomic 교체·후속 SHA 확인했다. 원본 canonical 맵의 새 Main PIE를 다시 실행한 증거는 아니다.'
    else:
        map_scope += '원본 canonical 적용과 native PIE 범위는 FinalVerification의 native_verified_map_asset을 따른다.'
    measured = f'fresh main PID{pid} native Khazan.Snow.PIE Success(맵 {verified_map}), Nanite 변위 법선 방향 GPU 실측 발(고립 brush의 2D 최대 파임){foot:.3f}cm/무기{weapon:.3f}cm'
    art = f'''사용자가 직접 지정한 눈 최대55cm·발35cm·무기50cm로 조정했다. 이 숫자는 원작 metadata 직접값이나 assistant 임시값이 아니라 이번 사용자 결정이다. DeepSnow는60→55cm이며 기존 DeepSnow2 36cm/기타 눈18cm·rim12cm는 앞선 assistant 임시 tuning을 유지했다. 얕은 눈에서는 requested depth를 실제 weighted 눈층 높이로 제한해 물리 substrate 아래를 파지 않는다. 기존 D/N/S·원작 layer weight·UV와 terrain mesh/collision을 보존했다.

발 주변 요청5~8cm는 기존1.4rim 지원배율을 포함한 타원 semiaxes8×5cm로 적용했다. 실제 FootRadiusCm는8/1.4×5/1.4=(5.714286×3.571429)cm, FootContactHeightCm는20→8cm다. 정확한0 접촉보다 작은 허용범위를 남기면서 큰 brush와 높은 reach의 접촉 오인을 줄인다. 무기 반경100cm와 둥근 크레이터 형상은 유지한다. WeaponContactHeightCm는55+기존24=79cm의 최대 눈층 기반 계산값이며 실제 GPU top collision이 아니다.

새 전용 material은 M_HM_Deformable_Landscape1_Contact55_20261007와 M_HM_Deformable_Landscape2_Contact55_20261007다. HM_DepthReferenceCm_User=55를 기존 R 압축fraction과 곱하고 min(weightedSnowHeight,requestedDepth)로 cm 파임을 제한한다. field Custom의 float4 W에는 cap×valid를 반환해 얕은 layer가 바닥까지 눌린 곳의 source-height normal slope만 억제한다. 이것은 shader 내부 값이며 field texture 채널 추가가 아니다. 중앙 normal의4추가 field sample도 동일한 clamped depth를 사용한다.

{measured}. Nanite MP_Displacement는 source vertex normal 방향으로 움직이므로 QA 카메라는 가까운 실제 mesh LOD0 삼각형의 정점 법선을 barycentric 보간한 smooth normal 방향으로 정렬한다. collision face normal과 interpolated normal을 로그로 구분하며 경사면의 수직 Z 깊이 직접 측정과 구분한다. 앞선 수직 카메라와 단일 ray는 솟은 눈의 XY 이동 때문에 tiny foot brush를 놓쳤고 foot0cm 실패로 기록됐다. 발은 무파임 baseline과 고립 direct foot stamp 이후128×128 SceneDepth를 같은 pixel끼리 비교한 2D 최대 파임을 측정한다. 단일 중앙 ray를 발 전체 깊이로 가정하지 않으며 brush나 제품 접촉 범위를 검사를 위해 확대하지 않는다. 작은 발의 고립 direct stamp는 전체 envelope 바깥 압축0을 검사했고 부분 깊이·잔여 눈·동일무기50회/이동창 이력·별도 full-clear 지면일치와 actual Player run/Dodge/4 Monster 발·몸·gear/공중무기/EndPlay를 검사했다. 실제 발을8cm 바로 위에 고립시킨 airborne negative는 수행하지 않았다. 원작 pixel parity·모든 실제 공격/넘어짐 montage·GPU/shipping 성능은 미검증이다.

선택 전달은 현재 Source3/새 Preview map/새 material2와 unique alias {module_name}, 후속 canonical map handoff다. {map_scope} 기존 Deep material2/일반 DLL/다른 작업 Source·사용자 editor를 보존했다. 사용자 save/reload/PIE/camera/close를 실행하지 않았고 새 WeaponCompression layout을 사용하려면 사용자 작업 저장·에디터 재시작이 필요하다. 정확한 hash·검증은 {evidence}/{{RequestedContract,SavedSettings,Delivery,FinalVerification,PendingApplyStatus}}.json과 MainPIE.log/MainPreview를 따른다. runtime 계약·CPU 증거는 ../Engineering/HEINMACH_SNOW_IMPLEMENTATION_20261006.md의 이번 절에 분리했다.
'''
    engineering = f'''기존 presentation owner AKZSnowDeformation h/cpp만 보완했고 새 runtime 파일/class/component/manager0, KZComboActionAbility.cpp 변경0이다. WeaponCompression을 조정 가능한 기존 contact 설정에 추가해 실제 부착/merged 장비 stamp가50/55를 소비한다. FootCompression=35/55, body=1이다. 기존 R[0,1]은55cm reference에 대한 normalized requested depth로 해석하며 material이 actual layer로 clip한다. field RGBA16F 채널·CPU cache/texture 저장·sampling/window/tile upload/GT PostUpdateWork/weak contact 및 EndPlay ownership은 유지했다. 머테리얼 세부는 Art 정본의 이번 절을 따른다.

dev-only 기존 Snow PIE test는 작은 brush의 셀중심·FOV4 QA optics, 가까운 실제LOD0 triangle의 barycentric vertex-normal camera 정렬을 사용한다. collision face/smooth normal을 로그로 비교하며128×128 무파임/고립 foot SceneDepth의 pixel별 차이 중 최대값으로35cm 목표를 검사한다. partial cm depth와 residual, isolated foot envelope 외 압축0, 같은 weapon fraction50회/cache scroll, 별도 full-clear substrate agreement를 검사한다. 깊이값은 Nanite 법선 변위 방향 두께이며 경사면 vertical Z 깊이와 구분한다. 앞선 수직·단일ray probe의 tiny foot0cm 실패는 자료로 보존하며 작은 파임을 벗어난 ray를 발 깊이로 가정하지 않는다. Monster3종의 이전 실패는 contacts54/112/34가 있으나 이동거리0/10.38/0cm로 gait fixture가 멈춘 것이었다. SpawnMonster가 early auto-possession 직후 StopLogic해도 controller 다음Tick이 늦은 bootstrap을 시작할 수 있으므로 test-owned 새 actor에만 StopMovement/AI tick disable/ASC CancelAllAbilities·ClearComboCommands를 적용했다. 첫 Preview Main에서는 foot34cm/weapon50cm·4종 gait가 통과했으나 Halberd 누운 torso fixture가 animation을 계속 재생해 배치 후 pelvis가 움직였다. case15에서 pose를 배치하기 전에 bPauseAnims=true로 고정했다. 같은 고정은 기존 merged weapon case17에서도 사용하며 제품 body contact 코드는 변경하지 않았다. 제품 runtime AI/Controller를 변경하지 않았고 fixture는 종료 때 파괴한다. actual Player run/Dodge 및4 Monster feet/body/merged gear와 weapon airborne negative·EndPlay 회귀를 유지했고 {measured}. 실제 foot8cm 바로 위의 고립 airborne negative는 미수행이며 이 증거를 그 검사로 확대하지 않는다.

메인 CPU CSV {Path(perf['csv']).name}: SnowTick active{perf['active_samples']}samples 평균{perf['mean_ms']:.6f}/P95 {perf['p95_ms']:.6f}/max{perf['max_ms']:.6f}ms. Development Editor의 실제 게임스레드 값이며 cold cache/동시 editor 영향을 포함한다. 이전 결과와 조건이 달라 성능 개선율로 계산하지 않는다. CPU field 약48MiB/GPU field32MiB·2cm/2048² 예산은 유지했다. GPU 전체 비용/shipping FPS/모든 gameplay montage·원작 동일성은 미검증이다.

현재 Source3/Preview map/후속 canonical map/material2/module({module_name}) 및 보호 대상 hash는 {evidence}/Delivery.json/FinalVerification.json/PendingApplyStatus.json을 따른다. {map_scope} unique alias와 새 material paths로 loaded 이전 material/일반 DLL을 보존했다. 사용자 editor는 조작하지 않았고 새 native property 사용에 사용자 저장·재시작이 필요하다. 이전 broad/deep helper의 old SHA를 현재 baseline으로 재사용하지 않는다.
'''
    continuity = f'''이번55/35/50cm·발 범위 축소의 선택 반영과 native 검증·canonical handoff는 완료됐다. {map_scope} 현재 정본은 해당 도메인 Snow 문서의 이번 절과 {evidence}/FinalVerification.json/Delivery.json/PendingApplyStatus.json이다. 이전60cm/.7 foot/full weapon 설정은 역사 기록으로 남기며 현재값으로 재사용하지 않는다. 사용자 editor는 그대로이며 새 WeaponCompression 사용에는 사용자 저장·재시작이 필요하다.

후속 조정은 Router→해당 도메인 Snow 정본 최신 절→{evidence}/RequestedContract/SavedSettings/Delivery/FinalVerification.json→current main 실제 Source/map/Contact55 material에서 시작한다. 최신 Source intake 시 own Snow3 수정은 별도 보존하고 private cold build→fresh real-RHI author/readback→native PIE→latest main target/protected SHA·dirty 확인→선택 전달→fresh main saved readback/PIE 순서다. initial/broad/deep full authoring 또는 오래된 delivery를 재실행하지 않는다. GPU/shipping 및 isolated actual foot8cm airborne 검사는 미검증 후속이다.
'''
    sections = {
        'Docs/Art/HEINMACH_SNOW_DEFORMATION_2026-10-06.md': art,
        'Docs/Art/ART_PROJECT_STATE.md': f'사용자 결정 pile55cm/foot35cm/weapon50cm, full foot envelope8×5cm/reach8cm를 메인 반영했다. {measured}. Contact55 material2/selected map/alias, Deep material·일반 DLL·사용자 editor 보존. 재시작과 범위·자료는 Art Snow 정본 이번 절/{evidence}/FinalVerification.json을 따른다.\n',
        'Docs/Art/ART_WORK_CONTINUITY.md': continuity,
        'Docs/Art/ART_KNOWLEDGE_INDEX.md': f'현재 HeinMach snow 수치·material·saved/reload/이미지는 Art Snow 정본 이번55/35/50cm 절과 {evidence}/RequestedContract/SavedSettings/Delivery/FinalVerification.json 및 MainPreview를 재사용한다. 이전60cm 높이·40×32cm 발 brush는 현재 설정이 아니다. 원작 metadata 출처는 OriginalSnowContracts.json을 보존하며 이번 수치는 사용자 결정으로 구분한다.\n',
        'Docs/Engineering/HEINMACH_SNOW_IMPLEMENTATION_20261006.md': engineering,
        'Docs/Engineering/ENGINEERING_PROJECT_STATE.md': f'기존 Snow owner에 WeaponCompression 추가, field reference55/foot35/55/weapon50/55/body1과 reduced foot envelope8×5/reach8cm. 새 runtime 타입0. {measured}. CPU 평균{perf["mean_ms"]:.4f}/P95 {perf["p95_ms"]:.4f}ms(Development Editor), GPU/shipping未. selected delivery와 재시작·현재 proof는 Snow Engineering 정본 이번 절/{evidence}/FinalVerification.json이다.\n',
        'Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md': continuity,
    }
    paths = [(ROOT / name, body) for name, body in sections.items()]
    assert all(path.is_file() for path, _ in paths)
    appended = []
    for path, body in paths:
        if MARKER in path.read_text(encoding='utf-8'):
            continue
        with path.open('a', encoding='utf-8', newline='\n') as file:
            file.write(heading + body)
        appended.append(str(path.relative_to(ROOT)))
    print('CONTACT55_DOCS_APPENDED', json.dumps(appended, ensure_ascii=False))


if __name__ == '__main__':
    main()
