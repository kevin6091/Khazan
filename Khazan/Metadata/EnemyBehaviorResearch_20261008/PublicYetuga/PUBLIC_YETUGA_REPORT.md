# Yetuga 공개 자료 대조 — 2026-10-08

조사 범위는 공개 전투 자료 분석이다. 게임 Source/BP/asset 및 기존 Docs는 수정하지 않았다. Inven 11개와 DCinside 16개 원본 animated WebP를 내려받아 접촉시트로 표적 확인했다. YouTube 전체 영상과 무편집 전투는 재생 관측하지 못했다. 아래의 `inven_XX`/`dc_XX`는 `manifest.json`의 동일 ID와 대응한다. 접촉시트 시각은 편집된 클립 내부 위치이며 원작 공격 시간이나 전체 영상 타임스탬프가 아니다. 동작 수와 피해 판정 수를 구분한다.

## 출처

| ID | 출처·작성일 | 종류·조건 | 정확한 URL |
|---|---|---|---|
| S1 | Nirr, 2025-01-17 02:32 | Inven 자가 촬영 WebP 11개·공략. 데모 시기, 난이도/빌드 미표기 | https://www.inven.co.kr/board/party/6187/21 |
| S2 | ㅇㅇ(61.76), 2025-04-14 12:46:27 | DCinside 자가 촬영 WebP 16개·공략. 정식 발매 후, 난이도/빌드 미표기 | https://gall.dcinside.com/mgallery/board/view/?id=berserkerkhazan&no=19069 |
| S3 | Irfan Ansari, 2025-01-21 | Prima Games, 데모라고 명시한 공략 | https://primagames.com/tips/the-first-berserker-khazan-how-to-beat-yetuga-boss |
| S4 | Faviyan Mustafiz, 2025-03-30 | NoobFeed, 독립 서술 공략. 빌드 미표기 | https://www.noobfeed.com/articles/the-first-berserker-khazan-guide-how-to-beat-yetuga-first-boss |
| S5 | Jake Su, 2025-03-24 갱신 | The Escapist, 공략 | https://www.escapistmagazine.com/the-first-berserker-khazan-how-to-beat-the-yetuga/ |
| S6 | Asmir Kovacevic, 2025-03-27 01:33 | AltChar, Normal 표기 영상 공략. 본문만 확인 | https://www.altchar.com/guides/the-first-berserker-khazanyetuga-boss-fight-tips-and-video-guide-aOy0L6W2GJTg |
| S7 | 개발사, 2025-06-26 | 공식 패치 노트. Steam 518753 / PS5 01.013.021 / Xbox 1.1.13.21 | https://steamcommunity.com/games/2680010/announcements/detail/543361383085900259 |
| S8 | Junho Lee, 2025-06-24 UTC | 공식 개발자 노트, 고갈과 난이도 개편 설명 | https://steamcommunity.com/games/2680010/announcements/detail/543360749096928013 |
| S9 | 팬 위키, 최근 수정 2026-05-28 | Namu mirror. 제작/촬영 원본과 독립 여부 미확인 | https://d.namu.moe/w/%EC%98%88%ED%88%AC%EA%B0%80 |
| S10 | 팬 위키, 작성일 미확인 | Fandom. 본문 열기 제한으로 검색 인덱스 infobox만 확인 | https://khazan.fandom.com/wiki/Yetuga |

S1/S2는 서로 다른 시기의 촬영 자료로 대조했다. Prima를 번역·복제한 여러 사이트는 독립 근거로 세지 않았다. S9/S10도 공식 원본으로 취급하지 않는다.

## 동작 식별표

좌/우는 예투가 자신의 손 기준이다. `관측`은 클립 프레임에서 확인한 외형적 동작, `서술`은 작성자 설명, `미확인`은 원본 데이터/통제된 실험이 필요한 계약이다. 아래 근접 동작명은 연구용 식별명이며 원작 내부 스킬명을 확정하지 않는다.

| 패턴 | 관측·대조 결과 | 근거 클립 / claim 출처 | 남은 계약 |
|---|---|---|---|
| 기본 2동작 | 왼 주먹 하강 후 오른 어퍼컷. 거리 이탈 시 두 번째 생략은 S1 서술 | inven_01; dc_01; S1, S3, S4 | 정확한 연계 거리·평가 시점 |
| 단발 횡타 | 교차 방향 팔 휘두르기 하나 | dc_02; S2, S3, S4 | 기본 2타 중단과 별도 선택 구분 |
| 양팔 내려찍기 | 양팔을 높이 올린 뒤 지면 타격 | dc_03; inven_08; S2, S3, S5 | 단발 선택/포효 연계 조건 |
| 기본 4동작 | 오른손 시작, 교대 횡타 후 큰 회전 마무리·회복 | dc_04; inven_02; S2, S3, S4 | 마지막 동작의 실제 hit event 수 |
| 강화 5동작 | 왼손 시작 연속타. 마지막 직전가드 뒤 정지 회복 사례 | dc_05; S2 | 전 단계 직전가드가 필수인지, 고정 경직 계약 |
| 바닥 쓸기 | 낮은 자세의 팔 휩쓸기 | dc_06; S2, S4 | 사전 동작/거리 조건 |
| 짧은 바닥 치기 | 근거리에서 짧게 한 손으로 지면 타격 | dc_07; inven_03; S2, S1 | 방향·범위 |
| 도약 찍기 | 도약→주먹 매몰→빼내기. 빼낼 때 피격도 관측 | dc_08; inven_04; S2, S1, S3 | 각각의 피해 판정/추적 중단 시점 |
| 후방 쓰러짐 | 등으로 낙하→기상→앞쪽 찍기. 후방 잔류/정면 추적 사례 대비 | dc_09, dc_10; inven_05; S2, S1 | 후방 판정 각·거리·체류 조건 |
| 돌진 | 몸을 낮춰 접근·통과. 벽 충돌 경직은 복수 서술 | dc_11; inven_06; S1, S2, S5 | 벽 사례 직접 관측·조향/중단 |
| 돌 투척 | 거리 확보 후 전방 투사체 | dc_12; inven_07; S2, S3, S4 | 선택 거리·예측 조준 |
| 브레스 | 전면 훑기→얼음 열 형성→지면 타격/파쇄 | dc_13; inven_11; S2, S3, S4 | 각 구간 guard/frost/피해 계약 |
| 대형 얼음 공격 | 지면 얼음 덩어리→도약→착지 폭발. 이어 돌진 잡기 사례 | dc_14; inven_10; S2, S1 | 정확한 개방 조건·후속 확정 여부 |
| 돌진 잡기 | 양팔 벌림→전방 몸 던지기→실패 시 구르며 이탈 | dc_15, dc_14; inven_09; S2, S1 | 재시도·사거리·개방 조건 |
| 근접 잡기 | 왼팔 밝은 발광→잡아 올림→공중 이동/내던지기 | dc_16; S2 | 콤보 실패 연계인지·별도 선택인지 |

위 표의 4/5는 시각적 큰 공격 동작 수다. 4동작 마지막 피해가 2번(S9)인지 약 3번(S4)인지는 이 자료로 확정하지 못했다. 마지막 구간 추가 접촉시트 `dc_04_detail.jpg`에서도 개별 피해 판정 수를 자신 있게 분리할 수 없다.

## 상태·방어·추격 claim 대조

| Claim | 근거와 판단 |
|---|---|
| 단계 변화 | S1은 대략 HP 절반, S3은 HP 40–50%, S4는 첫 Brutal 이후 자주 관측된다고 서술. 상관관계를 단일 HP 또는 Brutal 트리거로 확정하지 않는다. S2는 강화 후 잡기/브레스 추가를 설명한다. |
| 잡기 방어 | S4/S5는 잡기를 패링 불가로 설명한다. WebP에는 피하는 돌진 잡기와 의도적으로 붙잡힌 근접 잡기가 있으나 모든 guard 성공/실패를 통제 비교하지 않았다. 원본 collision/guard flag 확인이 최종 근거다. |
| 대형 얼음 회피 | S6의 패링만 가능·항상 잡기 연계 주장은 S1/S3/S5의 회피 설명과 충돌한다. `dc_14` 후속은 근접 잡기가 아니라 양팔을 벌리는 돌진 잡기다. 사례 한 번을 고정 연계로 일반화하지 않는다. |
| 브레스 패링 | S5는 패링 가능이라고 쓰고 S9는 guard 불가라고 쓴다. 브레스/생성 결정/마지막 파쇄를 분리하지 않은 서술일 수 있다. 각 구간 flag 미확인이다. |
| 투척 후 냉기 | S4는 직전가드해도 피해/냉기 위험이 있다고 서술한다. 피해와 상태 이상 누적을 분리해야 한다. `dc_12`의 방어 이펙트만으로 무피해나 누적 면역을 증명할 수 없다. |
| boss 고갈 | S7의 공식 변경은 Yetuga Exhausted 5초→8초다. S8은 고갈 중 싸울 수 없고 추가 피해를 받는다고 설명한다. 콤보 종료 후 잠깐 웅크림, 벽 충돌, 마지막 직전가드 경직과 고갈을 같은 상태로 묶지 않는다. |
| 스태미너 회복 | S10 infobox는 Non-Replenishing 타입을 표기하지만 전체 회복 수명/회복 액션을 직접 확인한 근거가 아니다. 전투 후 회복·Brutal 후 회복 조건은 미확인이다. |
| 기회 포착 | S1/S3/S4는 큰 콤보·도약·돌진 실패 뒤 공격 창을 설명한다. 영상에서 보이는 회복 자세와 원작 timer는 다르다. S4는 Brutal 표시 직후 즉시 실행하지 않고 추가 공격을 넣을 수 있다고 서술한다. |
| 플레이어 회복 반응 | 회복 아이템 입력을 감지해 특정 기술로 응징하는지는 공개 클립만으로 미확인. 거리와 플레이어 행동의 인과를 분리한 전투 실험이 필요하다. |
| 후방/원거리 추격 | 후방 쓰러짐·정면 기상타·도약·돌진·투척은 관측/복수 서술. 상대 위치, 선택 확률, cooldown, 재평가 시점은 공개 영상의 단발 사례로 결정할 수 없다. |

## 자료 충돌과 버전 제한

S4의 2타가 항상 이어진다는 서술은 S1의 거리 이탈 분기와 다르다. S4의 강화 5타 오른손 시작은 S2의 왼손 시작 설명 및 해당 클립과 다르다. 피해 판정 수·팔 기준·번역·빌드 차이 가능성을 열어 두며 다수결로 숫자를 채우지 않는다. S3의 초 단위 딜레이/회복 추정과 S4의 추정 구간은 원작 직접 수치가 아니다.

S1은 돌진 잡기를 1페이즈 목록에 두지만 S2는 강화 후 잡기 등이 추가된다고 설명한다. 두 잡기의 개방 조건을 같은 것으로 묶거나 모든 잡기가 2페이즈 전용이라고 확정하지 않는다. S9의 대형 얼음 공격 이후 근접 잡기라는 서술도 `dc_14`에 관측된 돌진 잡기와 다르다.

S7은 2025-06-26 패치의 고갈 시간 변경으로 버전 차이가 실제 존재함을 증명한다. S8은 출시 당시 Easy/Normal 명칭이 이후 Normal/Challenge로 바뀌었다고 설명한다. 따라서 2025년 3월 Normal 영상과 6월 이후 Normal을 같은 조건으로 취급하지 않는다. 클립 빌드/난이도 미표기이므로 여기서는 최신 모든 난이도 일치를 주장하지 않는다.

## 전체 전투 참고 영상 — 미관측

| 영상 | 날짜/조건 확인 범위 | 정확한 URL |
|---|---|---|
| PlayStation 공식 첫 15분 | 2024-08-07, 개발 중 자료 | https://www.youtube.com/watch?v=98KBS73XTpM |
| IGN 첫 15분 | 2024-08-07, 공식 프리뷰 재배포 | https://www.youtube.com/watch?v=F0I4aETElC0 |
| Elbethium 데모 Yetuga | 2025-01-16, 데모 | https://www.youtube.com/watch?v=VW2LromauCU |
| ChazPlaysGames 공략 | 2025-03-22, 작성자 챕터 존재 | https://www.youtube.com/watch?v=uq26QEsDuxk |
| PowerPyx / ObsiEez | 페이지 2025-03-24, Normal·조력자 없음 표기 | https://www.youtube.com/watch?v=Vl4nrqhs7yo |
| AltChar 공략 내 영상 | 페이지 2025-03-27 | https://www.youtube.com/watch?v=efpR5pN1TE0 |

브라우저 재생 수단 부재 및 영상 fetch 제한으로 위 영상은 실제 시청하지 않았다. 작성자 챕터를 관측 타임스탬프로 제시하지 않는다. 전체 전투로 조건 분기를 검증하려면 난이도·버전을 고정하고 HP/스태미너/거리/각도/회복 입력별 독립 실험을 해야 한다.

## 보존 자료와 재현

`manifest.json`은 원문 페이지, 정확한 CDN URL, 로컬 원본, 프레임 수·컨테이너 길이, 접촉시트 경로를 저장한다. `*_sheet.jpg`는 약 400ms 간격 샘플이며 `dc_04_detail.jpg`, `dc_05_detail.jpg`, `dc_14_detail.jpg`, `dc_16_detail.jpg`는 필요한 구간을 더 촘촘히 확인한 자료다. 모든 프레임을 연속 재생했다고 표현하지 않는다. 컨테이너 길이는 편집/압축한 자료의 길이이며 gameplay 수치 출처로 사용하지 않는다.

`official_relevant_patch_records.json`은 공개 Steam News API의 공식 기록으로 원문을 보존한다. 조회 URI는 `https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid=2680010&count=100&maxlength=0&feeds=steam_community_announcements&enddate=1751155199`이며 해당 June 26 record gid는 `1803527891497745`, 원시 Unix date는 `1750917654`다. 공식 커뮤니티 링크와 API의 externalpost ID는 서로 다른 ID 체계다.

`fetch_frames.py`, `render_frames.py`, `detail_frames.py`는 다운로드/접촉시트 생성 재현 스크립트다. 실행 시 원본 temp 경로가 포함되어 있으므로 재사용자는 보존 경로로 바꿔야 한다. 원작 스킬 이름·조건·수치는 별도 native metadata 조사 결과와 합쳐야 한다.
