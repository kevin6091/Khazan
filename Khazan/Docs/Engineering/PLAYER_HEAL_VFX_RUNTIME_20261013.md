# 플레이어 회복 VFX 실행 정본

## 2026-10-13 — 기존 Heal → Action feedback 연결

직접 구현 요청이다. Router → 현행 Architecture/Migration → HEAL_IMPLEMENTATION/HEAL_WEAPON_PRESENTATION과 실제 Source를 확인했다. 원본/표시 값은 `Docs/Art/PLAYER_HEAL_VFX_SOURCE_20261013.md`, 현재 적용/검증/정확 재개는 `Metadata/HealVFX_20261013/FinalVerification.json` 및 `ResumeState.json`이다.

기존 `UKZHealAbility::HandleMontageNotify`에 `UKZAnimNotify_CombatEffect` parent/배치 child start/stop 소비만 추가했다. writer는 Heal Montage의 source-derived effect 데이터, consumer는 자기 active Heal 실행이다. 현행 montage pointer와 instance ID를 먼저 확인한다. child end를 먼저 처리하고 start를 처리하며, 같은 marker의 원래 WeaponStow/WeaponDraw/HealStart/Heal callback도 이어서 실행한다. HP/회복량/사용 비용/입력/gait/무기 부착/마지막 instance stop 로직을 재작성하지 않는다.

Spawn/dedup/GT finalized-bone callback/receipt/정상 end·취소·피격·사망·UnPossess cleanup은 `UKZActionAbility`가 이미 소유한다. 실제 owner/avatar 검증은 기존 StartCombatEffect에 있다. 공유 notify에 mutable component를 저장하지 않는다. 새 runtime file/class/component/manager/delegate/GameplayTag0이다. 몬스터/AI 및 worker에서 ASC를 읽는 경로를 추가하지 않는다. Actor에 별도 회복 timer/표현 상태 사본을 만들지 않는다.

기존 DEV `KZHealAbilityPIETest.cpp`를 확장했다. 환경 `KZ_HEAL_VFX_OUT`이 있는 owned 테스트에서만 실제11 child의 particle count/parent bone/finite transform/소멸 및 shader·화면 값을 수집한다. camera45도와180/-150/60cm offset 및 capture1.35/1.95s는 **QA fixture**다. 플레이어/맵/에디터 세션은 저장하지 않는다. 기존 input/HP/MaxHP/걷는 pose/weapon/발도 취소/UnPossess 회귀가 함께 실행된다. 공격 판정 회귀 등록명은 `Khazan.Combat.PlayerAttackCollision.PIE`다.

검증 작업본은 `Khazan_HealVFXWork_20261013/Khazan`의 물리 Source/Config/Binaries/Plugins와 recovery-only private Content다. borrowed Content는 read-only junction이며 저장하지 않는다. `heal_vfx_task_20261013.py`는 별도 숨김/below-normal editor와 single-action/unique-log UBT를 실행한다. 사용자의 editor/다른 work를 종료·PIE·reload/강제 잠금 해제하지 않는다.

Rider debugger에는 기존 Khazan/UE5 C++ configuration만 있으며 supportsDynamicLaunchOverrides=false였다. recovery-owned project를 launch하려면 사용자 configuration 변경이 필요해 기존 설정을 유지했다. debugger session/breakpoint 생성0, user exception baseline8/enabled5 그대로다. 기존 native DEV test의 값 로그로 fallback했다. PostLoad가 UpdateModuleLists를 호출하는 engine source를 확인해 T3D의 transient SpawnModules 미출력을 실행 누락으로 해석하지 않았다. sizes/core RGBA/late alpha와 render flags를 실제로 확인했다. debugger로 pause/stack을 얻었다고 주장하지 않는다.

Author03와 fresh Saved03의 모든 기존 notify 문자열/GUID/시각 보존, 현재 골격의11 socket 존재/paired effect22 child를 확인했다. WorkBuild01/02/03/04/05 성공, PrivatePIE01/02 Heal+PlayerAttackCollision Success, NativeProbe01/02/PrivatePolished01 Heal Success다. 최초 Shader usage flags/low-visibility는 최종 품질 근거로 쓰지 않는다. source curves/role/clock/UV mask는 재구성이고 source-game native/pixel/network/shipping parity는 미확인이다.

실제 Main 반영은15행 `Delivery.json`과 fresh canonical Main build/saved/actual RHI로 확인한다. 기존128여 Source/Config/Heal 원본·Draw montage를 SHA 보호하고 새 FX12 및 기존 Heal Montage1, runtime1/DEV1만 전달한다. 더 오래된 private DLL/Build.cs/uproject/Config/기타 작업은 전달0이다. 새 Main 기능 검사에서도 실제 loaded module와 target SHA를 결속한다. 완료 후 재개는 final evidence → 대상 material/Cascade/Heal marker만 표적 확인하며 author/원본 전수 추출/Root/FPS/physics/공격 VFX를 다시 적용하지 않는다.


## 2026-10-13T09:39:54.076603+09:00 ? ???? ?? VFX Main ??

?? Recovery?5 effect role/core?burst???????light flash? ?? Heal/Stow ??? ????. source raw LinkValue+?? Stow offset/rate? ???? ?? HP/InputEnd/weapon/??/?? ??/FPS/root/audio? ????. runtime1/?? DEV1/asset13(??12+?? Heal Montage1)?15 ??? exact SHA/CAS? ????. ? runtime file/class/component/manager/tag0, private DLL/Config/Build ??0, ?? 133 ?? SHA ??0??. ? Source? Main?? canonical build??.

MainBuild01 exit0/22.04s, MainSaved01 save0??? notify/GUID/?? ?11bone/22pair, MainFinalPIE01 ?? Khazan.Heal.PIE/Khazan.Combat.PlayerAttackCollision.PIE Success?. ??11 child emit?parent bone?finite values/HP????????? ?????/???UnPossess cleanup? ???? actual loaded canonical DLL SHA? 39ab3b029cc36dd7c78213f55fc2e22446110268952cbd932571a6a96488a46d?. shader errors0/pixel instructions179?189?207, Main ?? Core1.3667s/hand burst1.9667s ??? energy/continuous edge? ????. missing ParticleSprites/MeshParticles usage ?? default fallback warning0??. ?? editor/???/??/??? owned process fixture, package/map ??0, ???/foreign editor ??0??.

Source mesh3/FT_Trail.G/ShaderLUT?source numeric? clock ??/TEMP? PLAYER_HEAL_VFX_SOURCE_20261013.md? ????. cooked Niagara/VM/material/WPO graph ???? ?? native Cascade? ??? ????? original skin sampling/light/full shader/pixel ????? camera/Shipping/network/??? ???? ???. ExposureCompensation1/EmissiveGain8/feather0.04???1.25px/DepthFade8cm ?? ????? TEMP?. Source Dilation1.3497161s? ?? raw Heal1.4666667s? ???? ??? retime?? ???. ?? ??/???? ???? ?? ?? ? Main ???? ????.

?? ??0. ?? evidence? Metadata/HealVFX_20261013/FinalVerification.json, ResumeState.json, Changes.patch?. ??? ?? ???current /Game/HealVFX/Materials?Particles ? Heal marker? ?? ????. ?? full author/?? ??/?? ????/?? VFX?physics/root/FPS ?? private DLL ??? ???? ???. ?? ??/???/?? ??? ? ??? ????.
