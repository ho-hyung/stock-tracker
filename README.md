# Stock Tracker - 주식 고수 추적 알림 시스템

국내 주식 시장의 외국인/기관 매매동향과 DART 공시를 추적하여 Slack으로 알림을 보내는 시스템입니다.

## 기능

- **외국인/기관 매매동향**: 시가총액 상위 종목의 거래 동향 추적
- **대량보유 공시**: 5% 이상 지분 보유/변동 공시 알림
- **임원/주요주주 거래**: 내부자 주식 거래 공시 알림
- **평일 자동 실행**: 장중 10회 스케줄링 (09:10 ~ 17:00)
- **중복 알림 방지**: 동일 공시 재발송 방지

## 스케줄

| 시간 | 내용 |
|------|------|
| 09:10 | 장 시작 직후 |
| 09:40 | 초반 방향성 확인 |
| 10:30 | 오전 중반 (외국인/기관 본격 매매) |
| 11:30 | 오전장 마무리 |
| 13:00 | 오후장 시작 |
| 14:00 | 오후장 본격화 |
| 14:30 | 장 마감 1시간 전 |
| 15:10 | 장 마감 직전 (포지션 정리) |
| 15:40 | 장 마감 직후 (확정 데이터) |
| 17:00 | 일일 요약 |

## 설치

```bash
git clone https://github.com/ho-hyung/stock-tracker.git
cd stock-tracker

# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

## 설정

```bash
# 환경변수 파일 생성
cp .env.example .env
```

`.env` 파일 편집:
```
DART_API_KEY=your_dart_api_key_here
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/xxx/xxx
```

### API 키 발급

- **DART API**: https://opendart.fss.or.kr (무료)
- **Slack Webhook**: Slack 앱 설정 > Incoming Webhooks

## 사용법

```bash
# 1회 실행
python src/main.py --mode once

# 일일 요약 포함 실행
python src/main.py --mode summary

# 테스트 (Slack 발송 안함)
python src/main.py --dry-run

# 스케줄러 실행 (평일 자동)
python src/main.py --mode scheduler

# 백그라운드 실행 (터미널 종료 후에도 유지)
nohup python -u src/main.py --mode scheduler > scheduler.log 2>&1 &
```

## 프로젝트 구조

```
stock-tracker/
├── config.py                 # 설정 (알림 조건, 관심종목)
├── requirements.txt
├── .env.example
├── src/
│   ├── collectors/
│   │   ├── dart_collector.py    # DART 공시 수집
│   │   └── krx_collector.py     # 투자자별 매매동향
│   ├── analyzers/
│   │   └── signal_analyzer.py   # 알림 조건 분석
│   ├── notifiers/
│   │   └── slack_notifier.py    # Slack 발송
│   └── main.py
└── data/                     # 상태 저장 (자동 생성)
```

## 알림 조건 설정

`config.py`에서 알림 조건을 수정할 수 있습니다:

```python
ALERT_CONFIG = {
    "consecutive_days": 3,        # 연속 매수일 기준
    "min_net_buy_amount": 100,    # 순매수 금액 기준 (억원)
    "min_stake_change": 1.0,      # 지분 변동 기준 (%)
}

# 관심 종목 (빈 리스트면 전체 대상)
WATCHLIST = [
    # "005930",  # 삼성전자
    # "000660",  # SK하이닉스
]
```

## 라이선스

MIT
