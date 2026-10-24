# Khazan

Unreal Engine 5와 C++로 제작한 ‘카잔’ 모작 개인 프로젝트입니다. 플레이어 전투, 몬스터 AI와 보스 패턴, 락온·회피, 눈 지형 변형을 구현하였습니다.

## 플레이 영상

전체 플레이 시연 영상입니다. 아래 플레이어에서 재생할 수 있습니다. **8분 48초 · 720p · 소리 포함**

https://github.com/user-attachments/assets/33a1e404-c66b-4ea5-931c-d14b2f36ae6b

[전체 영상 다운로드](https://github.com/kevin6091/Khazan/releases/download/gameplay-demo/Khazan-gameplay-720p.mp4) · [시연 영상 Release](https://github.com/kevin6091/Khazan/releases/tag/gameplay-demo)

## 프로젝트 개요

| 항목 | 내용 |
| --- | --- |
| 참여 인원 | 1명 · 개인 프로젝트 |
| 개발 기간 | 1개월 |
| 엔진·언어 | Unreal Engine 5, C++, Blueprint |
| 개발 도구 | Rider, Rider MCP |

## 주요 구현

- **GAS 기반 전투와 콤보**: Gameplay Ability와 Gameplay Tag로 행동을 관리하고, Data Asset과 애니메이션 Notify를 이용해 콤보 분기 및 선입력을 처리하였습니다.
- **가드·패링**: 공격 방향과 패링 허용 시간을 확인하고, 방어 결과에 따라 스태미나 소모와 반응·피드백을 적용하였습니다.
- **시간 기반 공격 판정**: 공격의 활성 구간과 충돌 데이터를 애니메이션에 맞춰 갱신하고, 공격 그룹별 중복 피해를 방지하였습니다.
- **StateTree 몬스터 AI**: 인지·추적·대치·공격을 나누고, 조건과 쿨다운을 확인해 공격 패턴을 선택하도록 구성하였습니다.
- **락온·회피**: 화면과 시야를 기준으로 대상을 선택하고, 카메라 보간 및 방향별 회피를 연결하였습니다.
- **눈 지형 변형**: 캐릭터와 무기 접촉에 따른 압축 데이터를 타일과 텍스처로 관리하여 이동·전투 흔적을 표현하였습니다.
