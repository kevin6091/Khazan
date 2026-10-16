# Public Apes 조사 보존 보고서 — 2026-10-08

대상은 공개 명칭 **Granite Jocko / 바위 원인**이다. 로컬 분석 대상 ApesStoneHandElite의 공개 자료를 조사했으며 공개 자료만으로 ApesStoneHand_E와 ApesStoneHand_E_Early를 각각 특정하지 않았다. 영상의 “Yeti”는 제작자 통칭이다. Yetuga 보스와 구분한다.

분석·관측 보존 자료이며 Source/BP/게임 에셋 및 기존 Docs를 수정하지 않았다. 다운로드 프로그램·패키지, 서명된 미디어 URL, 다운로드 로그는 제외했다.

## 출처와 실제 관측

| 출처 | 게시일 | 직접 검사 |
| --- | --- | --- |
| [TurboAchiever — How to defeat Granite Jocko (Yeti)](https://www.youtube.com/watch?v=fjZsbwldgTw) | 2025-03-28 | 전체 360p 영상의 2초 표본. 00:10–00:50은 0.5초 표본. 제작자 description 별도 확인 |
| [TurboAchiever — Granite Yocko Training Challenge](https://www.youtube.com/watch?v=XkAaFFcRdBY) | 2025-04-04 | 전투·화면 설명·훈련 완료·도감. 02:07–02:31 일부는 HD. 원본 02:26과 HD 상대 00:19의 화면 직접 대조 |

완전한 두 영상은 videos의 full360pAV.mp4 파일이다. 640×268/30fps 화면과 오디오를 보존했다. 관측한 video-only 파일과 보존 AV의 압축 video packet SHA가 동일함을 검증했다. 후속 보존 때 확보한 오디오는 독립 분석하지 않았다. 컨테이너 실측 길이는 첫 영상 00:01:50.33, 둘째 00:02:54.87이며 YouTube metadata의 110/175초와 구분한다. 정확한 게임 patch/build 및 로컬 원본과의 버전 동일성은 미확인이다.

## 공격 패턴 — 관측과 설명 분리

| 패턴 | 직접 관측 | 설명·조건·한계 | 원본 시각 |
| --- | --- | --- | --- |
| 돌진·잡기 시도 | 빠른 접근 후 팔 훑기, 플레이어 회피 | 제작자는 잡기 시도라고 설명. 성공한 잡기·피해 수명 미확인 | [00:10–00:14](https://www.youtube.com/watch?v=fjZsbwldgTw&t=10s) |
| 머리 위 내려찍기 | 팔 올리기→전방 바닥 타격 | 제작자는 근접 시 약한 후속 가능성을 설명. 거리·분기 임계값 미확인 | [00:27–00:29](https://www.youtube.com/watch?v=fjZsbwldgTw&t=27s) |
| 점프 내려찍기 | 도약→착지→팔 고정→빼며 훑기. 고정 중 플레이어 타격 | 회수 공격의 hit 조건·고정 시간 미확인 | [00:20–00:25](https://www.youtube.com/watch?v=fjZsbwldgTw&t=20s) |
| 투석 | 간격을 둔 준비와 비행 물체 | 제작자는 원거리 선택이라고 설명. 거리·궤도·추적 수치 미확인 | [00:17–00:19](https://www.youtube.com/watch?v=fjZsbwldgTw&t=17s) |
| 회전 연속 공격 | 전진·팔 휘두르기·몸 회전의 연속 동작 | 제작자 설명은 5타이며 마지막 겉보기 한 동작에 두 공격. 독립 적중 타수는 표본으로 확정하지 않음 | [00:31–00:39](https://www.youtube.com/watch?v=fjZsbwldgTw&t=31s) |
| Brutal 기회 | 붉은 표시와 처형성 공격 | 자연 회복·고갈 지속·회복 이후 동작 미확인 | [01:38–01:42](https://www.youtube.com/watch?v=fjZsbwldgTw&t=98s) |

5타는 제작자 설명이며 원작 notify/판정 event를 직접 확인한 수치가 아니다. 표의 시간은 재확인용 영상 좌표이며 gameplay tuning 수치가 아니다.

## 등 파괴·stagger

두 번째 영상 00:47 이후 제작자 화면 설명은 등 갑옷 파괴 뒤 어깨를 쥐고 등을 대고 넘어지는 반응을 설명한다. 설명을 직접 읽은 근거와 완전한 반응 수명 관측을 구분한다.

[02:12–02:14](https://www.youtube.com/watch?v=XkAaFFcRdBY&t=132s)의 강한 타격 후 상체 반응, 02:14.4의 훈련 완료·처치를 확인했다. 곧바로 죽어 **살아 있는 상태의 완전한 넘어짐→대기→기상→회복**은 검증하지 못했다. Reaction 프레임을 완전한 등 파괴 루틴 증거로 확대하지 않는다.

[02:28](https://www.youtube.com/watch?v=XkAaFFcRdBY&t=148s) 실제 도감은 Beast, Granite Jocko 이름·외형과 staggered 상태 처치 과제 1/1 완료를 보여 준다. 목록에 Granite Jocko 항목이 두 개 있어 공개 이름만으로 subtype을 단정하지 않는다.

[Righteous13 — Daphrona’s Codex](https://steamcommunity.com/sharedfiles/filedetails/?id=3452706584)는 2025-03-26 작성/2025-04-08 갱신이다. 본문은 등을 대고 넘어진 동안 처치를 설명한다. 2025-04-20 댓글은 등 파괴, 2025-04-16 댓글은 충전 공격으로 넘어뜨린 경험이다. 공략·체험이며 원본 threshold가 아니다. 다음 Pincer Spider 문단의 “계속 parry해서 Brutal” 지시를 Granite Jocko challenge 지시로 잘못 인용하지 않는다.

## 미확인·혼동 방지

- 뒤쪽 전용 반격, 분노·HP 단계, 체력 회복, 살아 있는 기상 공격은 두 영상으로 확정하지 못했다. Yetuga의 frost/뒤쪽 발구르기/단계 설명을 가져오지 않는다.
- [커뮤니티 위키](https://khazan.fandom.com/wiki/Granite_Jocko)의 Stamina Type = Non-Replenishing은 2차 주장이다. 게이지 종류·자연 회복 직접 계측이나 로컬 field 대조 결과가 아니다.
- 도감의 통나무를 던질 힘이라는 설정 문구를 별도 runtime 통나무 투척 패턴으로 승격하지 않는다.
- Netherworld Jocko/Charon’s Chains와 일반 Wild Jocko/야생 성성이를 Early 정예의 규칙으로 옮기지 않는다.
- [Narru의 한국어 Inven 위치 공략](https://www.inven.co.kr/board/party/6187/161), 2025-03-27 게시, 바위 원인 지칭. 상세 전투 조건 근거는 아니다.
- [Mesjaf Steam 100% Guide](https://steamcommunity.com/sharedfiles/filedetails/?id=3454314089), 2025-03-29 작성/2025-09-24 갱신, embedded YouTube ID로 영상 두 개를 찾은 탐색 근거다.

## 시각·파일 검증과 재개

TimestampVerification.json이 타임라인 정본이다. 첫 stream-copy 47–171초 clip와 TrainingSheet의 절대 시각은 keyframe 경계로 어긋나 보존하지 않았다. 후속 HD는 127–151초 재인코딩 정확 컷이며 원본 146초와 HD 상대 19초의 같은 Fang Spider 도감 화면을 대조했다. 직접 프레임 133.4/134.4/148.0초와 sheet의 nominal label을 구분한다.

Main coarse는 2초 표본(시각 표본 불확실성 최대 1초), fine와 Training은 0.5초 표본(최대 0.25초)이다. 이는 분석 sampling 불확실성이고 원작 허용오차·전이 시간·hit timing이 아니다. 직접 HD 프레임 시간 양자화는 최대 1/60초다.

명시된 조사 파일만 복사하고 원본/목적지 SHA-256을 대조했다. ArtifactSha256Manifest.json은 자기 자신을 제외한 보존 산출물의 존재·크기·SHA를, CopyVerification.json은 TEMP 원본→목적지 복사 SHA와 video packet 동일성을 기록한다.

후속은 PublicSources.json→TimestampVerification.json→원본 영상/HD 프레임 순서다. subtype, AI 조건·실제 타수·게이지·recovery는 로컬 원작 metadata와 대조한다. 제작자 설명을 원작 직접값으로 승격하지 않는다.
