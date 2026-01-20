"""
리스크 관리 모듈
- ATR 기반 동적 손절/익절 계산
- 변동성 분석
- 포지션 사이징 제안
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
import FinanceDataReader as fdr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


@dataclass
class RiskLevel:
    """손절/익절 기준"""
    stock_code: str
    stock_name: str
    current_price: float

    # 손절 기준
    stop_loss_price: float
    stop_loss_pct: float

    # 익절 기준 (1차, 2차)
    take_profit_1_price: float
    take_profit_1_pct: float
    take_profit_2_price: float
    take_profit_2_pct: float

    # 변동성 정보
    atr: float  # Average True Range
    atr_pct: float  # ATR 비율 (%)
    volatility_grade: str  # "낮음", "보통", "높음", "매우높음"

    # 리스크/리워드 비율
    risk_reward_ratio: float


class RiskManager:
    """리스크 관리자"""

    # 변동성 등급 기준 (ATR %)
    VOLATILITY_THRESHOLDS = {
        "낮음": 2.0,
        "보통": 3.5,
        "높음": 5.0,
        # 5% 초과: "매우높음"
    }

    # 손절/익절 배수 (ATR 기준)
    STOP_LOSS_ATR_MULTIPLIER = 1.5  # 손절: 1.5 ATR
    TAKE_PROFIT_1_ATR_MULTIPLIER = 2.0  # 1차 익절: 2 ATR
    TAKE_PROFIT_2_ATR_MULTIPLIER = 3.5  # 2차 익절: 3.5 ATR

    def __init__(self):
        self.price_cache = {}

    def _get_price_data(self, stock_code: str, days: int = 20) -> Optional[list]:
        """
        주가 데이터 조회 (OHLC)

        Returns:
            [(date, open, high, low, close), ...] 또는 None
        """
        cache_key = f"{stock_code}_{days}"
        if cache_key in self.price_cache:
            return self.price_cache[cache_key]

        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days + 10)

            df = fdr.DataReader(
                stock_code,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )

            if df.empty or len(df) < 5:
                return None

            data = []
            for idx, row in df.iterrows():
                data.append({
                    "date": idx.strftime("%Y-%m-%d"),
                    "open": float(row['Open']),
                    "high": float(row['High']),
                    "low": float(row['Low']),
                    "close": float(row['Close'])
                })

            self.price_cache[cache_key] = data
            return data

        except Exception as e:
            print(f"    [WARNING] {stock_code} 가격 조회 실패: {e}")
            return None

    def _calculate_atr(self, price_data: list, period: int = 14) -> float:
        """
        ATR (Average True Range) 계산

        ATR = 최근 N일간 True Range의 평균
        True Range = max(고가-저가, |고가-전일종가|, |저가-전일종가|)
        """
        if len(price_data) < period + 1:
            period = len(price_data) - 1

        true_ranges = []

        for i in range(1, len(price_data)):
            high = price_data[i]['high']
            low = price_data[i]['low']
            prev_close = price_data[i-1]['close']

            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)

        # 최근 N일 평균
        recent_trs = true_ranges[-period:]
        return sum(recent_trs) / len(recent_trs) if recent_trs else 0

    def _get_volatility_grade(self, atr_pct: float) -> str:
        """변동성 등급 결정"""
        if atr_pct <= self.VOLATILITY_THRESHOLDS["낮음"]:
            return "낮음"
        elif atr_pct <= self.VOLATILITY_THRESHOLDS["보통"]:
            return "보통"
        elif atr_pct <= self.VOLATILITY_THRESHOLDS["높음"]:
            return "높음"
        else:
            return "매우높음"

    def calculate_risk_levels(self, stock_code: str, stock_name: str,
                             current_price: float = None) -> Optional[RiskLevel]:
        """
        손절/익절 기준 계산

        Args:
            stock_code: 종목코드
            stock_name: 종목명
            current_price: 현재가 (없으면 조회)

        Returns:
            RiskLevel 객체 또는 None
        """
        # 가격 데이터 조회
        price_data = self._get_price_data(stock_code, days=30)
        if not price_data:
            return None

        # 현재가
        if current_price is None:
            current_price = price_data[-1]['close']

        # ATR 계산
        atr = self._calculate_atr(price_data, period=14)
        atr_pct = (atr / current_price) * 100

        # 변동성 등급
        volatility_grade = self._get_volatility_grade(atr_pct)

        # 손절/익절 가격 계산
        stop_loss_amount = atr * self.STOP_LOSS_ATR_MULTIPLIER
        take_profit_1_amount = atr * self.TAKE_PROFIT_1_ATR_MULTIPLIER
        take_profit_2_amount = atr * self.TAKE_PROFIT_2_ATR_MULTIPLIER

        stop_loss_price = current_price - stop_loss_amount
        take_profit_1_price = current_price + take_profit_1_amount
        take_profit_2_price = current_price + take_profit_2_amount

        # 비율 계산
        stop_loss_pct = (stop_loss_amount / current_price) * 100
        take_profit_1_pct = (take_profit_1_amount / current_price) * 100
        take_profit_2_pct = (take_profit_2_amount / current_price) * 100

        # 리스크/리워드 비율 (1차 익절 기준)
        risk_reward_ratio = take_profit_1_pct / stop_loss_pct if stop_loss_pct > 0 else 0

        return RiskLevel(
            stock_code=stock_code,
            stock_name=stock_name,
            current_price=current_price,
            stop_loss_price=round(stop_loss_price, 0),
            stop_loss_pct=round(stop_loss_pct, 2),
            take_profit_1_price=round(take_profit_1_price, 0),
            take_profit_1_pct=round(take_profit_1_pct, 2),
            take_profit_2_price=round(take_profit_2_price, 0),
            take_profit_2_pct=round(take_profit_2_pct, 2),
            atr=round(atr, 0),
            atr_pct=round(atr_pct, 2),
            volatility_grade=volatility_grade,
            risk_reward_ratio=round(risk_reward_ratio, 2)
        )

    def get_position_size(self, account_size: float, risk_pct: float,
                         stop_loss_pct: float) -> dict:
        """
        포지션 사이징 계산

        Args:
            account_size: 총 투자금
            risk_pct: 1회 거래 최대 손실 비율 (예: 2%)
            stop_loss_pct: 손절 비율

        Returns:
            {"position_size": 포지션 크기, "max_loss": 최대 손실액}
        """
        max_loss = account_size * (risk_pct / 100)
        position_size = max_loss / (stop_loss_pct / 100) if stop_loss_pct > 0 else 0

        return {
            "position_size": round(position_size, 0),
            "max_loss": round(max_loss, 0),
            "position_pct": round((position_size / account_size) * 100, 1) if account_size > 0 else 0
        }

    def format_risk_text(self, risk: RiskLevel) -> str:
        """리스크 정보를 텍스트로 포맷"""
        lines = [
            f"📍 *{risk.stock_name}* (`{risk.stock_code}`)",
            f"현재가: {risk.current_price:,.0f}원 | 변동성: {risk.volatility_grade} (ATR {risk.atr_pct}%)",
            "",
            f"🛑 *손절*: {risk.stop_loss_price:,.0f}원 (-{risk.stop_loss_pct}%)",
            f"✅ *1차 익절*: {risk.take_profit_1_price:,.0f}원 (+{risk.take_profit_1_pct}%)",
            f"🎯 *2차 익절*: {risk.take_profit_2_price:,.0f}원 (+{risk.take_profit_2_pct}%)",
            f"📊 리스크/리워드: 1:{risk.risk_reward_ratio}",
        ]
        return "\n".join(lines)


if __name__ == "__main__":
    # 테스트
    manager = RiskManager()

    test_stocks = [
        ("005930", "삼성전자"),
        ("000660", "SK하이닉스"),
        ("373220", "LG에너지솔루션"),
    ]

    print("=" * 50)
    print("손절/익절 기준 테스트")
    print("=" * 50)

    for code, name in test_stocks:
        print(f"\n{name} 분석 중...")
        risk = manager.calculate_risk_levels(code, name)

        if risk:
            print(manager.format_risk_text(risk))
            print()

            # 포지션 사이징 예시 (1000만원 계좌, 2% 리스크)
            sizing = manager.get_position_size(10_000_000, 2, risk.stop_loss_pct)
            print(f"💰 포지션 사이징 (1000만원 계좌, 2% 리스크)")
            print(f"   적정 투자금: {sizing['position_size']:,.0f}원 ({sizing['position_pct']}%)")
            print(f"   최대 손실: {sizing['max_loss']:,.0f}원")
