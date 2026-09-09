# HeinMach Enemy 외형 라이브러리

프로젝트 사용 경로: `/Game/_Art/Enemies/HeinMach`.

- 확인용 맵: `Preview/L_HeinMach_EnemyCatalogue`.
- 검병 40종: `Empire/Assemblies/Sword/BP_EN_Empire_Sword_*`.
- 검·방패병 4종: `Empire/Assemblies/SwordShield/BP_EN_Empire_SwordShield_*`.
- 별도 할버드 정예: `HalberdElite/Assemblies/BP_EN_Empire_HalberdElite`.
- 전신 조합 메시 44개는 `Empire/CombinedMeshes`, 원본 파츠는 `Empire/Parts`, 장비는 `Equipment`에 있다.
- `H/F/U/L`은 원작 recipe의 머리/얼굴/상의/하의 선택 번호이며 1부터 시작한다.

이 Blueprint는 외형 Actor다. 공격·AI·피격 기능은 구현하지 않았다.

`EnemyImportManifest.json`은 source package와 UE 에셋의 대응표,
`CombinedMeshManifest.json`은 조합의 파츠/정점/머티리얼 근거,
`EnemyAssemblyCatalog.json`은 완성 Blueprint 목록이다.
`Source`는 원본 metadata이고 `Reports`는 실행/검증 보고서다.

원본 추출 파일: `C:/Users/user/Desktop/카잔/EnemyExtracts/HeinMach_20260908`.

원작 전용 shader는 DefaultLit/Unlit 표시용 그래프로 대체했다.
랜덤 색상·체형 적용, UE MorphTarget/LOD 체인·cloth/physics 전체 복원은 미완료다.
관련 원본 데이터는 보존했으며 이 결과를 원작 완전 복원으로 표현하지 않는다.

정확한 범위·수치 출처·재개 절차:
`Docs/Art/HEINMACH_ENEMY_EXTRACTION_2026-09-08.md`.
