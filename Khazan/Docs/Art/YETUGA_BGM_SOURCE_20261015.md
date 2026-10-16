# 2026-10-15 — HeinMach Yetuga 원작 전투 BGM

사용자 요청으로 FModel이 참조하는 원작 archive에서 Yetuga 전투곡을 표적 추출해 Main에 임포트했다. GUI로 임의 음원을 고른 것이 아니라 기존 EnemyExtractor(CUE4Parse)가 FModel의 현행 archive 설정을 사용했다. AES 값은 문서/로그에 출력하지 않았다. 기존 audio index/wwiser report를 재사용했으며 전체 추출·전체 SFX 재작성은 하지 않았다.

## 원본 식별

- archive: `pakchunk0-WindowsNoEditor.pak`.
- 원작 event package: `BBQ/Content/_Kazan_/Sound/Music/HeinMach/bgm_boss_heinmach_start`, `EventId=2887386748`.
- 실제 재생 graph를 보유한 선행 event: 같은 폴더의 `bgm_boss_heinmach_pre_01`, `EventId=3379818559`. start event 자체에 Media가 없으므로 start 이름의 파일만 디코딩하는 접근은 사용하지 않았다.
- Media: `BBQ/Content/WwiseAudio/Media/446487212.wem`; 원본 DebugName: `Music\boss\bgm_boss_yetuga_82_4on4.wav`.
- fresh WEM SHA256: `c203c7a50bc6bc4387ae676ed1aa62c6fbc7e4df92808d5a8b41a8f3da0b31f4`; 10,357,994 bytes.
- cinematic `_cn`/종료 `_cadence`는 이번 전투곡에 섞지 않았다. 원본 pre_01/pre_02/start/end JSON4개와 bank3개/WEM1개의 정확한 경로·hash는 `Metadata/YetugaBGM_20261015/{Original/MetadataExtractionReport.json,Raw/AudioFileExtractionReport.json}`에 있다.

## 음악 구성과 수치 출처

원본 start의 RequiredGroupValueSet을 unsigned로 해석한 battle branch는 `3245971795=3911558329`(boss on), `3710226845=3814669119`(cinematic off), `4033804471=4005322201`(cadence off)다. `Saved/ImportReports/GameplayAudio_20261011/BankRecipes08/txtp/`의 해당 pre_01 branch를 사용했다. Music playlist node302673256의 ContinuousSequence는 첫 segment750444780을 한 번, loop segment1069894324를 반복한다.

원작 bank field `CAkMusicSegment750444780.fDuration=218742.57688152354ms`, markers `693.796393718467/218742.576881523ms`; loop segment1069894324의 duration `219512.1951219514ms`, markers `1463.41463414634/219512.195121951ms`다. clip의 source446487212 및 trim/layer/automation을 기존 wwiser가 해석한 TXTP를 그대로 렌더했다. TXTP group의 `#v -3.5dB`는 원작 bank 해석 gain이며 WAV에 한 번만 적용했다. native SoundClass/Cue/Wave의 gain/pitch는 unity라 추가 gain이나 정규화가 없다. segment의 fTempo82는 bank 값이며 상위 container의120/default MIDI 필드로 대체하지 않았다.

원본 recipe3개는 `{f1}/{f2}/{f3}` 강제 group 선택본이다. f1만 전투곡으로 임포트하면 짧은 pre-entry만 재생되는 오류가 된다. 작업 recipe는 f1의 마지막 `group=-S3>1`에서 강제 선택 `>1`만 제거해 전체 sequence를 복원했고, WEM 경로만 fresh archive export로 바꿨다. decoder `-i`로 기본 다회 반복/fadeout 없이 최초 구간+loop 한 주기만 PCM16 stereo48kHz로 렌더했다.

아래는 원작 field의 밀리초와 구분하는 **디코더 해석/샘플 양자화 결과**다. `seconds=frames/48000`, 구간은 `[start,end)`이며 임의 길이 튜닝이 아니다.

| native asset | sample 범위 | frames | 계산 길이 |
| --- | --- | --- | --- |
| SW_YetugaBattle_Intro | 0–10499648 | 10499648 | 218.7426666667s |
| SW_YetugaBattle_Loop | 10499648–20965990 | 10466342 | 218.0487916667s |

## Main 결과

`/Game/Audio/Original/Music/Yetuga/`에 새 asset4개를 저장했다: `SC_YetugaMusic`(SoundClass), `SW_YetugaBattle_Intro`, `SW_YetugaBattle_Loop`, `SC_YetugaBattle`(SoundCue). Cue는 Intro→Loop WavePlayer(looping=true)의 Concatenator다. PCM/LoadOnDemand로 추가 손실 압축 없이 stream cache를 사용하며 music class/always-play와 PlayWhenSilent를 설정했다. 기존 SFX용 SC_Original의 .5 headroom은 이 음악에 적용하지 않는다.

실제 임포트/저장과 기존 `KZ.Audio.FinalizeCues`의 persistent wave reference/graph 생성은 `Metadata/YetugaBGM_20261015/Import01/Import.json` 및 Editor.log에 있다. Main4 asset의 SHA도 이 보고서에 기록했다. map 저장0/기존 sound asset 변경0이다. 첫 렌더/임포트 명령은 `Scripts/Art/{prepare_yetuga_music_20261015.py,import_yetuga_music_20261015.py}`다. importer는 기존 경로 발견 시 덮어쓰지 않고 중단하므로 완료된 Import01을 무조건 재실행하지 않는다.

사용자 최신 요청은 전장 진입 후 사망/처치/이탈에도 계속 재생이다. 실행 연결은 Engineering의 `HEINMACH_YETUGA_PORTAL_20261015.md` 최신 절을 따른다. 이 요청에서 원본 음원·layer/trim/gain을 보존했으나 원작 Wwise 전체 DSP/RTPC·native cue 전환의 sample parity나 실제 전투 청취 검증을 주장하지 않는다. 게임 플레이 테스트/실기 청취0이며 delivery/build의 정확한 상태는 `Metadata/YetugaBGM_20261015/Implementation.json`에 있다.
