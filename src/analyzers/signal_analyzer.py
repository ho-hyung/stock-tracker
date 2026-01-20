"""
수집된 데이터를 분석하여 알림 발송 여부를 결정하는 모듈
"""

from dataclasses import dataclass
from typing import Optional
import json
import os
from datetime import datetime
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import ALERT_CONFIG, WATCHLIST


@dataclass
class Signal:
    """알림 신호"""
    signal_type: str  # "foreigner", "institution", "major_shareholder", "executive_trading"
    priority: str  # "high", "medium", "low"
    data: dict
    reason: str


class SignalAnalyzer:
    """수집된 데이터를 분석하여 알림 신호 생성"""

    def __init__(self, state_file: Optional[str] = None):
        self.config = ALERT_CONFIG
        self.watchlist = set(WATCHLIST) if WATCHLIST else None
        self.state_file = state_file or os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "state.json"
        )
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """이전 상태 로드 (중복 알림 방지용)"""
        if os.path.exists(self.state_file):
            with open(self.state_file, "r") as f:
                return json.load(f)
        return {
            "last_run": None,
            "sent_alerts": {},  # 발송된 알림 기록
            "consecutive_buys": {},  # 연속 매수 추적
        }

    def _save_state(self):
        """상태 저장"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        self.state["last_run"] = datetime.now().isoformat()
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def _is_in_watchlist(self, stock_code: str) -> bool:
        """관심종목 여부 확인"""
        if not self.watchlist:
            return True  # 관심종목이 없으면 전체 대상
        return stock_code in self.watchlist

    def _is_already_sent(self, alert_id: str) -> bool:
        """이미 발송된 알림인지 확인"""
        return alert_id in self.state.get("sent_alerts", {})

    def _mark_as_sent(self, alert_id: str):
        """알림 발송 기록"""
        if "sent_alerts" not in self.state:
            self.state["sent_alerts"] = {}
        self.state["sent_alerts"][alert_id] = datetime.now().isoformat()

    def analyze_foreigner_data(self, data_list: list[dict]) -> list[Signal]:
        """
        외국인 매매 데이터 분석

        조건:
        - 순매수 금액이 설정값(억원) 이상
        - 관심종목에 포함 (설정 시)
        """
        signals = []
        min_amount = self.config["min_net_buy_amount"] * 100_000_000  # 억원 -> 원

        for data in data_list:
            stock_code = data.get("stock_code", "")

            if not self._is_in_watchlist(stock_code):
                continue

            net_buy = data.get("net_buy_amount", 0)
            if abs(net_buy) < min_amount:
                continue

            alert_id = f"foreigner_{data['date']}_{stock_code}"
            if self._is_already_sent(alert_id):
                continue

            action = "순매수" if net_buy > 0 else "순매도"
            priority = "high" if abs(net_buy) >= min_amount * 2 else "medium"

            signals.append(Signal(
                signal_type="foreigner",
                priority=priority,
                data=data,
                reason=f"외국인 {action} {abs(net_buy)/100_000_000:.0f}억원 (기준: {self.config['min_net_buy_amount']}억원)"
            ))

            self._mark_as_sent(alert_id)

        return signals

    def analyze_institution_data(self, data_list: list[dict]) -> list[Signal]:
        """
        기관 매매 데이터 분석

        조건:
        - 순매수 금액이 설정값(억원) 이상
        - 관심종목에 포함 (설정 시)
        """
        signals = []
        min_amount = self.config["min_net_buy_amount"] * 100_000_000

        for data in data_list:
            stock_code = data.get("stock_code", "")

            if not self._is_in_watchlist(stock_code):
                continue

            net_buy = data.get("net_buy_amount", 0)
            if abs(net_buy) < min_amount:
                continue

            alert_id = f"institution_{data['date']}_{stock_code}"
            if self._is_already_sent(alert_id):
                continue

            action = "순매수" if net_buy > 0 else "순매도"
            priority = "high" if abs(net_buy) >= min_amount * 2 else "medium"

            signals.append(Signal(
                signal_type="institution",
                priority=priority,
                data=data,
                reason=f"기관 {action} {abs(net_buy)/100_000_000:.0f}억원 (기준: {self.config['min_net_buy_amount']}억원)"
            ))

            self._mark_as_sent(alert_id)

        return signals

    def analyze_major_shareholder_data(self, data_list: list[dict]) -> list[Signal]:
        """
        대량보유 공시 데이터 분석

        조건:
        - 모든 대량보유 공시 알림 (5% 이상 지분 변동)
        """
        signals = []

        for data in data_list:
            alert_id = f"major_{data['rcept_no']}"
            if self._is_already_sent(alert_id):
                continue

            signals.append(Signal(
                signal_type="major_shareholder",
                priority="high",
                data=data,
                reason="5% 이상 대량보유 공시 발생"
            ))

            self._mark_as_sent(alert_id)

        return signals

    def analyze_executive_trading_data(self, data_list: list[dict]) -> list[Signal]:
        """
        임원/주요주주 거래 공시 분석

        조건:
        - 모든 임원/주요주주 거래 공시 알림
        """
        signals = []

        for data in data_list:
            alert_id = f"executive_{data['rcept_no']}"
            if self._is_already_sent(alert_id):
                continue

            signals.append(Signal(
                signal_type="executive_trading",
                priority="medium",
                data=data,
                reason="임원/주요주주 주식 거래 공시"
            ))

            self._mark_as_sent(alert_id)

        return signals

    def analyze_all(
        self,
        foreigner_data: list[dict],
        institution_data: list[dict],
        major_shareholder_data: list[dict],
        executive_data: list[dict]
    ) -> list[Signal]:
        """
        모든 데이터 분석 및 신호 생성

        Returns:
            우선순위별로 정렬된 Signal 리스트
        """
        all_signals = []

        all_signals.extend(self.analyze_foreigner_data(foreigner_data))
        all_signals.extend(self.analyze_institution_data(institution_data))
        all_signals.extend(self.analyze_major_shareholder_data(major_shareholder_data))
        all_signals.extend(self.analyze_executive_trading_data(executive_data))

        # 상태 저장
        self._save_state()

        # 우선순위별 정렬 (high -> medium -> low)
        priority_order = {"high": 0, "medium": 1, "low": 2}
        all_signals.sort(key=lambda x: priority_order.get(x.priority, 99))

        return all_signals

    def get_daily_summary(
        self,
        foreigner_data: list[dict],
        institution_data: list[dict],
        major_shareholder_data: list[dict],
        executive_data: list[dict]
    ) -> dict:
        """일일 요약 데이터 생성"""
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "foreigner_top": foreigner_data[:5],
            "institution_top": institution_data[:5],
            "major_shareholder_count": len(major_shareholder_data),
            "executive_trading_count": len(executive_data),
        }

    def clear_old_alerts(self, days: int = 7):
        """오래된 알림 기록 정리"""
        if "sent_alerts" not in self.state:
            return

        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days)

        new_alerts = {}
        for alert_id, sent_time in self.state["sent_alerts"].items():
            try:
                sent_dt = datetime.fromisoformat(sent_time)
                if sent_dt > cutoff:
                    new_alerts[alert_id] = sent_time
            except (ValueError, TypeError):
                pass

        self.state["sent_alerts"] = new_alerts
        self._save_state()
