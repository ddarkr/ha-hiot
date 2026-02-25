# HT HomeService (Hi-oT) for Home Assistant

HT HomeService (힐스테이트 하이오티) 클라우드 API를 이용한 Home Assistant 사용자 지정 통합구성요소입니다.

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

## Notes

- 에너지 `period=DAY`는 저희 단지 서버에서 500/604 에러가 발생하므로 비활성화해두었습니다.
- 가스밸브 `turn_on`은 서버에서 지원하지 않습니다.

## Development

```bash
.venv/bin/pytest tests/ -v
```

현재 테스트 상태: 54 passed
