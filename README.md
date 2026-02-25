# HT HomeService (Hi-oT) for Home Assistant

[HT HomeService](https://www2.hthomeservice.com) (힐스테이트 하이오티) 클라우드 API를 이용한 Home Assistant 사용자 지정 통합구성요소입니다.

## Features

- Cloud API 기반 연동 (세션 쿠키 인증)
- 기기 제어/상태
  - Light, Climate(난방/에어컨), Fan, Switch(가스/대기전력)
- 에너지 센서
  - 전기/수도/가스 사용량, 요금, 목표 (총 9개 센서)
- Options Flow
  - 기기 상태 갱신 간격
  - 에너지 갱신 간격

## Installation (HACS)

1. HACS > 메뉴(우상단 ...) > Custom repositories
2. Repository URL에 이 저장소 URL 입력 (https://github.com/ddarkr/ha-hiot)
3. Category: Integration
4. HT HomeService 설치 후 Home Assistant 재시작

## Configuration

1. 설정 > 기기 및 서비스 > 통합구성요소 추가 (우측 하단)
2. `HT HomeService` 검색
3. 하이오티 계정 로그인
4. 단지 선택

### Scan interval

해당 익스텐션은 HT HomeService의 API를 주기적으로 호출하여 정보를 가져옵니다.

환경에 따라 적절한 호출 주기를 설정할 수 있도록 옵션을 제공합니다.

- 기기 상태 갱신 간격(`device_scan_interval`): 5초 ~ 10분 (기본 값 20초)
- 에너지 갱신 간격(`energy_scan_interval`): 5분 ~ 24시간 (기본 값 30분)

설정 방법:

1. 설정 > 기기 및 서비스 > 통합구성요소 > HT HomeService
2. `허브`에서 설정하려는 동호수 선택
3. `device_scan_interval`과 `energy_scan_interval`을 설정

> [!WARNING]  
> 힐스테이트 기준으로, 각 단지마다 월패드와 연계되는 IoT 서버가 존재하는 것으로 알고 있습니다.
>
> 너무 짧은 간격으로 API를 호출하실 경우 단지 서버에 부하를 주실 수 있으므로, 같은 단지 주민에게 민폐가 되지 않도록 적절한 주기를 사용해주시기 바랍니다.

## Notes

- 에너지 `period=DAY`는 저희 단지 서버에서 500/604 에러가 발생하므로 비활성화해두었습니다.
- 가스밸브 `turn_on`은 서버에서 지원하지 않습니다.

## Development

테스트:

```bash
.venv/bin/pytest tests/ -v
```

## Disclaimer

본 통합구성요소는 개발자 거주 단지에서만 테스트되었으며, 모든 단지에서 정상적으로 동작함을 보장하지 않습니다.

또한, 본 프로젝트는 현대건설(HT)와 연관되어 있지 않습니다. 사용으로 인해 발생하는 모든 책임은 사용자에게 있습니다.
