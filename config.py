import os
from dotenv import load_dotenv

load_dotenv()

# DART API 설정
DART_API_KEY = os.getenv("DART_API_KEY", "")

# Slack 설정
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# Gemini API 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Gemini 무료 한도 설정
GEMINI_FREE_TIER = {
    "daily_requests": 1500,  # 일일 요청 한도
    "warning_threshold": 0.8,  # 80% 도달 시 경고
}

# 알림 조건 설정
ALERT_CONFIG = {
    # 외국인/기관 연속 매수일 기준
    "consecutive_days": 3,
    # 외국인/기관 순매수 금액 기준 (억원)
    "min_net_buy_amount": 100,
    # 대량보유 지분 변동 기준 (%)
    "min_stake_change": 1.0,
}

# 관심 종목 리스트 (빈 리스트면 전체 대상)
WATCHLIST = [
    # "005930",  # 삼성전자
    # "000660",  # SK하이닉스
]
