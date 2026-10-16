# Combat UI 원작 자료와 임포트 — 2026-10-11

## 원본과 범위

사용자의 FModel active provider 설정을 기존 `Scripts/Enemies/EnemyExtractor`가 재사용했다. AES 키는 보고서/콘솔에 기록하지 않았다. provider decoder는 UE4_27이며 원본 package prefix는 `BBQ/Content/_Kazan_/UserInterface/`다. 대상 UI의 cooked metadata와 텍스처/스트리밍 FontFace를 추출했으며, cooked Widget BP를 UE5 BP로 직접 복사하지 않았다.

증거는 `Metadata/CombatUI_20261011/{SourceWidgetAudit,ImportEditor05/ImportReport,FontData01/FontDataReport}.json`과 `SourceWidgets01`, `SourceResources01`, `SourceParents01`, `SourceInputs01`의 package별 JSON이다. 표적 widget13, 직접 참조 resource41, parent7, input4, fontface1를 조사했다. 전체 asset decode는 수행하지 않았다. 숫자는 아래 위젯의 serialized field이며 default와 사용 instance override를 구분한다.

| 원본 package / export | field / 원시 값 | 적용 조건·단위 |
|---|---|---|
| `UIWidget/GameHud/W_Hud_LockOn` / `Szb_LockOn` | WidthOverride60 / HeightOverride60 | 일반 록온 wrapper, Slate logical px |
| 같은 package / `FinishKeyWrap` | WidthOverride38 / HeightOverride38 | 실행 가능 wrapper, logical px |
| 같은 package / `AnimatedSwitcher_Groggy` | TransitionDuration .15 / TransitionType Zoom | CommonUI 전환, 초. 프로젝트는 fade adapter |
| 같은 package / `Img_Excution` | Resource `T_Hud_LockOn_Excution`, Tint(.887923,.066626,.066626,1) | 원본은 붓 X 모양 표식. B glyph라고 부르지 않음 |
| `UITexture/Material/Simple_Additive/Instance/MI_UI_SimpleAdd_Target` | Texture=`UITexture/Fx/T_Fx_TargetLock` | parent MD_UI / BLEND_Additive |
| `UITexture/Icons/Key_Xbox/T_Icon_XB_B` | 실제 B glyph 이미지 | 프로젝트의 실제 B 입력 안내 |
| `Contents/GameSystemSetting/GamepadPresetA_Table` / NewRow_15 | DevKey=Interaction; MainKey=Gamepad_FaceButton_Right | 원작 preset A의 Interaction. 브루탈 전용 native binding 직접 확인은 아님 |
| `UIWidget/GameHud/WBP_BattleHUD` / PlayerGaugePack | HP360×8; Stamina240×6; HP padding80/6; ST padding72/4 | CDO256×8/0×6 대신 실제 HUD instance override 사용 |
| 같은 package / CanvasPanelSlot_6 | Anchor(.5,1), OffsetTop=-100, Alignment(.5,1) | 플레이어 게이지 하단 중앙 |
| `UIWidget/GameHud/StatusGauge/W_GaugePackage_Monster` / CDO | HP100×6; Stamina100×4; VerticalSpace2 | 일반 몬스터 기본 게이지 |
| `UIWidget/GameHud/OverheadGauge/W_OverheadGauge` | Elite BG180×32 / opacity .8 | 엘리트 backdrop; fill은 일반 monster gauge |
| `UIWidget/GameHud/Boss/W_Boss` / BossGaugePack | HP720×10; Stamina720×6; HP padding132/6; ST padding104/4 | 실제 보스 instance override |
| 같은 export | Stamina CurBarStyle_Boss(.364706,.156863,.729412,1); Bg(.311007,.12,.65,1) | linear color 원시 값 |
| `WBP_BattleHUD` / CanvasPanelSlot_38 | Anchor(.5,0); OffsetTop52; Alignment(.5,0) | 보스 HUD 상단 중앙 |
| `W_Boss` / BossName | AK_Font Medium, font size16, outline1/alpha.35, shadow(0,1)/alpha.65 | 원작 폰트 face와 표시 설정 |
| `StatusGauge/W_Hp_Monster` CurBar / `W_Stamina` CurBar | InterpolationTimeMultiply=.35 | 직접 기록값. native 공식과 단위는 미확인; .35초라고 단정하지 않음 |
| `StatusGauge/W_GaugePackage_PC` / Img_Hp_Bg/Img_Hp_Bg_1 | T_Hud_Hp_Bg03; ImageSize80×20; Horizontal tile; alpha.8 | 중앙 배경. 옆 BGSide/Center size는 각 HUD instance override 적용 |

브러시의 linear color를 Hex의 바이트 값으로 다시 해석하지 않았다. 원작 layout/color/texture의 보존과 native shader/VM/condition 완전 재현은 다른 검증이다.

## 실제 에셋

`/Game/UI/Combat/Textures`에 원작 이미지16, `/Materials`에 UI material2, `/Fonts/FF_DNFForgedBlade_Medium`에 원작 FontFace1을 저장했다. texture는 UI compression/LOD, NoMipmaps, sRGB, NeverStream으로 사용한다. source PNG/package/sha256/크기는 ImportReport가 연결한다. 원본 X 표식도 보존하며 현재 실행 안내에는 실제 B glyph를 사용한다.

FontFace의 `.ufont` 파일은 `.uexp`에 포함되지 않은 별도 스트리밍 데이터였다. 추가한 표적 `font-data` 모드로 원본3,737,948bytes를 추출했다. SHA256=`1b3f2426919753cb80f1b3b917672626bb8ce13534ce86eac30b7aec81ea6231`. OTTO header의 OpenType/CFF이며 `.otf`로 임포트했다. Native Widget은 이 face를 `Medium` 이름의 FCompositeFont로 사용한다. 원작 AK_Font의 다른 언어 fallback/Bold/Light 전체를 복원한 것은 아니다.

`M_UI_LockOn`은 원작 texture RGB/alpha를 MD_UI/Additive로 연결했다. 원작 parent의 AutoRotateSpeed=.2는 남아 있지만 cooked UV/function graph를 확보하지 못해 회전 공식까지 복원했다고 주장하지 않는다. `M_UI_BrutalRing`은 원작 OuterSizePercent98 / InnerSizePercent76에서 정규화 반지름.49/.38을 계산했고 원작 GaugeColor(.859375,.02238,.02238)을 사용했다. fwidth AA/full availability ring/fade는 프로젝트 adapter다. 원작 원형 progress의 시간/진행 공식과 shader 완전 일치는 미확인이다.

## 검증과 실패 보존

첫 Main RHI PIE01은 기능 검사와 스크린샷을 통과했다. 화면 검토 후 중앙 배경/원작 폰트와 lethal 감소 처리를 보완했다. 최신 실행 검증은 [Engineering 정본](../Engineering/COMBAT_UI_RUNTIME_20261011.md)을 따른다. UI 전용 에셋 외 기존 VFX/Animation/Level은 이 작업에서 재임포트하지 않았다.

ImportEditor02의 commandlet FontFactory는 SlateApplication 부재 assert였다. ImportEditor03의 자동 UFont composite struct 접근은 비노출 field로 실패했고, 원작 FontFace 저장은 유지했다. ImportEditor04는 기존 material expression 삭제가 rooted object assert를 일으켰다. 재사용 material의 graph를 변경할 이유가 없어 해당 변경을 제거하고 FontFace를 직접 native composite로 사용했다. ImportEditor05 exit0/ImportReport는 texture16/font1/material2 저장 완료 증거다. 실패 로그는 그대로 보존한다.
## 2026-10-11 — 최종 RHI shader·표시 검증

최종 UI 증거는 `Metadata/CombatUI_20261011/FinalVerification.json`과 `PIEEditor05_FinalShader`다. native 실제 전체 UI 검사/Exit0/material fallback0을 확인했다. 원작 texture16/Medium FontFace1 및 현재 WBP/BP 설정은 Main에 저장되어 있다. `M_UI_BrutalRing`은 원작 기반 radius98/76·색(.859375,.02238,.02238)을 유지하면서 누락됐던 RGBA→ComponentMask 두 default-pin 연결만 수정했다. shader 자체는 계속 명시된 analytic adapter다. 최초 기능 검사 통과를 shader 품질 통과로 확대하지 않으며, 최종 cold RHI와 원본/수치 구분은 위 receipt를 따른다.

## 2026-10-11 — B 표시의 사각형 알파와 딱딱한 원형 경계 교정

사용자가 B 표시의 테두리를 부드럽게 처리하도록 요청했다. `BrutalAlphaInspect01/AlphaInspection.json`에서 실제 저장 `M_UI_BrutalRing`의 opacity ComponentMask가 R=true/G=true/B=false/A=true인 것을 확인했다. 색과 알파를 함께 출력해 opacity가 상수 색 성분을 소비했고, 기존 캡처에 붉은 사각형이 보였다. 이전 fallback0은 컴파일 성공 근거이며 이 채널 의미가 올바르다는 근거는 아니었다.

수정은 기존 `/Game/UI/Combat/Materials/M_UI_BrutalRing` 한 개다. RGB 출력은 RGB-only, 투명도는 A-only로 명시했다. 원형 바깥 경계가 이미지 사각형 끝에서 잘리지 않도록 바깥쪽은 `1-smoothstep(.49-edge,.49,d)`, 안쪽은 `smoothstep(.38,.38+edge,d)`로 부드럽게 연결했다. 원작 `MI_UI_CircleProgress_Finish.OuterSizePercent98/InnerSizePercent76`에서 계산한 UV 반지름 `.49/.38` 및 `GaugeColor(.859375,.02238,.02238)`는 유지한다. `d=length(UV-.5)`, `edge=max(fwidth(d)*EdgeSoftnessPixels, .00001)`이며 epsilon은 기술적 안전값이다.

`EdgeSoftnessPixels=1.25`는 **어시스턴트 임시 표시 튜닝값**이다. 원작 셰이더 근거가 없는 화면 미분 기반 feather 폭 배율이며, 작은 B 표시의 경계를 부드럽게 하면서 글자 식별을 유지하려는 사용자 요청에 따른다. 기존 머터리얼의 ScalarParameter 기본값에서 조정한다. fwidth는 화면의 X/Y 미분 합이므로 정확히 모든 방향에서 동일한 1.25픽셀 폭을 보장하는 값으로 해석하지 않는다. 원본 `T_Icon_XB_B` PNG는 RGBA64×64이고 네 모서리 alpha0이다. 텍스처 픽셀·임포트 설정·폰트·UI 크기·gameplay Source는 변경하지 않았다.

`BrutalAlphaStage01`은 수정된 단일 패키지를 별도 경로에 저장했다. `BrutalAlphaStageRHI01/SavedAlphaRHI.json`은 새 프로세스에서 저장본 A-only/parameter1.25를 읽고 실제 RHI shader46 instructions/compile error0/fallback0/save0/Exit0을 확인한 근거다. 해시 CAS와 원자적 교체로 Main에 반영한 기록은 `BrutalAlphaMainDelivery/DeliveryReceipt.json`이다. 전 SHA `4e039a608be9764cd0628a95ed179b34cf0f4ead96169ae5d9fb8c7715190450`, 수정 SHA `c4d6ff781af4bdf9955722e698aae2b382e359949b771df91ff54c30e4039100`이며 이전 원본 byte backup을 보존했다. 마지막 Main 실제 UI 검사는 `BrutalAlphaMainPIE01`에서 진행한다.

실패 로그는 삭제하지 않았다. Author01의 직접 저장은 사용자 editor의 Windows Error32 잠금으로 실패했고 원래 파일은 유지됐다. Preview01은 실제 native UI 검사는 Success였으나 graph 작성 중 입력 배열 재설정의 일시적 missing UV 경고2건을 observer가 실패로 판정했다. 최종 저장본 cold RHI는 이 경고가 없었다. StageReadback01의 exit1은 작은 검사 프로젝트에 GameFeatureData 설정이 없었기 때문이며, 해당 검사 프로젝트에만 설정을 추가해 StageRHI01 exit0을 확인했다. 사용자 editor PID13416/25612의 종료·저장·제어는 수행하지 않았다.

## 2026-10-11 — B 알파 경계 Main 실제 검증 완료

`Metadata/CombatUI_20261011/BrutalAlphaFinalVerification.json`은 `MainDeliveredAndFreshVerified`다. 새 Main `BrutalAlphaMainPIE01`에서 저장 A-only/parameter1.25/current SHA c4d6ff…를 확인하고 실제 Khazan.CombatUI.PIE Success/shader fallback0/Exit0을 완료했다. `04_BrutalAvailable_B.png`를 직접 검수해 이전 붉은 사각형이 사라진 원형 B 표시를 확인했다. 기존 록온/실제 B 활성화/HP·Stamina UI lifecycle 검사도 통과했다.

기존 UI FinalVerification의 제품37개 중 이 머터리얼 한 개만 달라졌고 나머지36개는 hash 일치다. 현재 DLL c908da…도 유지했다. 신규 C++ 빌드/런타임 파일 변경은 없으며 own editor는 종료됐다. 이 수정의 필수 잔여는 없다. 이전 receipt는 당시 증거로 보존하고, 현재 이 패키지의 SHA만 위 후속 receipt로 대체해서 읽는다.
