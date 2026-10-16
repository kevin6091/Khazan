# 2026-10-13 — 몬스터 PhysicsAsset 형상 복원

사용자 요청의 천/Hair 보조 물리 활성화를 위해 기존 적 SK35의 비어 있는 PA 연결을 작업본에 준비했다. runtime/품질 정본은 `../Engineering/MONSTER_SECONDARY_PHYSICS_20261013.md`다. metadata 조사부터 시작했고 원본 전수 추출/메시 재임포트는 하지 않았다.

`Metadata/MonsterSecondaryPhysics_20261013/OriginalAnatomyShapes.json`은 stored Human Adult17/Elite17/Halberd16 capsule의 source package·export field·원시 Center/Rotation/Radius/Length 및 SHA를 보존한다. 실제 해당 메시 reference skeleton에 존재하는 anatomy bone만 재사용한다. 원본 shape의 NoCollision flag는 보조 물리의 몸 접촉을 위한 활성 collision으로 바꾸며 원작 전체 policy 일치로 기록하지 않는다.

그 외 몸체/무기 형상은 imported LOD0 largest-weight dominant vertex bounds를 bone-local cm에서 계산한 capsule이다. cloth/Hair 접촉 capsule 반경·질량-per-length/감쇠/drive/각도는 실제 현재 player PA에서 복사/계산했다. mesh root scale은 native35개 모두1이며 player의 wrapper100/.01 보정값을 enemy에 적용하지 않는다. 현재378 simulated bone 설정, post-process20, PA35, CopyPose1과 gameplay BP6의 총97 package 후보다. Skin/Skeleton/기존 animation/material/texture/LOD는 재저작하지 않았다.

Author01/HeavyCollision01 저장 성공과 actual physics 품질 성공을 구분한다. PhysicsPIE01에서 큰 각도 실패가 확인되어 Main 전달은 미완료다. 원작 강체/cloth 전체 동일성, 전체 skin 삼각형의 관통0을 확인한 것은 아니다. 정확한 현재 상태/실패/재개는 Engineering continuity와 해당 ResumeState.json을 따른다.


## 2026-10-13T05:17:23.148600+09:00 — 몬스터 PhysicsAsset 형상 Main 전달 완료

SK35/PA35/post-process20/shared CopyPose1/기존 gameplay BP6의97 package를 Main에 전달했다. 원본 vertex/skeleton/animation/texture/material/LOD 재임포트0이다. source metadata anatomy17/17/16 capsule의 package/field/raw/SHA는 OriginalAnatomyShapes.json, 그 외 dominant LOD0 skin bounds와 Yetuga actual skin tip sphere/질량·관성 계산은 final evidence의 source reports다. Feel은 current Player TEMP 재사용과 명시된 virtual-inertia TEMP2/기술적 adaption이며 원작 physics 전체 복원으로 표현하지 않는다. 최종 explicit simulated317이며 초기378/미완료 기록을 대체한다. Runtime 품질/검증/cleanup은 ../Engineering/MONSTER_SECONDARY_PHYSICS_20261013.md 및 Metadata/MonsterSecondaryPhysics_20261013/FinalVerification.json을 따른다. 필수 잔여0; full 원본 추출/재임포트/기존 shader·VFX·animation 변경을 반복하지 않는다.
<!-- MonsterSecondaryPhysics_20261013_main_complete -->
