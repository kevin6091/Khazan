# Dodge 입력과 특별 공격 코드 첨부

[단계별 코드와 함수 변수 설명](GUIDE.md)을 먼저 읽는다. 16개의 .h.txt/.cpp.txt는 현재 Source를 기준으로 만든 전체 파일 제안이다. 게임 파일에 적용하거나 build/PIE 완료한 결과가 아니다.

GUIDE의 파일 책임 표에서 각 실제 적용 경로를 확인한다. 기존 파일은 변경 부분을 비교해 적용하고, 신규 KZDodgeTypes.h는 Source/Khazan/Ability에 실제 .h로 만든다. .txt 파일을 그대로 Source build 대상으로 넣지 않는다.

SOURCE_BASELINE.json에는 읽었던 기존 Source의 SHA256이 있다. 사용자 변경을 과거 사본으로 덮어쓰지 않도록 적용 직전 비교한다.

소스 API 변경은 ASC/Controller/ComboAction 선언·정의·호출부를 함께 적용한다. 에디터에서는 기존 공유 ComboDefinition, 8 Dodge defaults/grant, 특별 공격 Entry/grant, 해금 GE를 안내 순서로 연결한다.

Notify 4/8/24 frame, Weak/Strong motion 대응 및 대각선 target은 GUIDE에 표시한 임시 authoring이다. 원작 확인값으로 취급하지 않는다. 해금 GE는 개발 검증용이며 영속 Save producer 구현은 아직 없다.
