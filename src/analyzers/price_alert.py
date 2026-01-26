"""
가격 알림 모듈
- 특정 종목이 목표가 도달 시 알림
- 매수/매도 가격 알림 설정
"""

import os
import sys
import json
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.price_fetcher import get_realtime_price

# 데이터 저장 경로
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


@dataclass
class PriceAlert:
    """가격 알림 설정"""
    stock_code: str
    stock_name: str
    alert_type: str  # "below" (이하), "above" (이상)
    target_price: int
    memo: str = ""  # 메모 (예: "분할매수 1차")
    created_at: str = ""
    triggered: bool = False
    triggered_at: str = ""


class PriceAlertManager:
    """가격 알림 관리자"""

    def __init__(self):
        self.alerts_file = os.path.join(DATA_DIR, "price_alerts.json")
        self._ensure_data_dir()
        self.alerts = self._load_alerts()

    def _ensure_data_dir(self):
        """데이터 디렉토리 생성"""
        os.makedirs(DATA_DIR, exist_ok=True)

    def _load_alerts(self) -> list[dict]:
        """알림 설정 로드"""
        if os.path.exists(self.alerts_file):
            try:
                with open(self.alerts_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_alerts(self):
        """알림 설정 저장"""
        with open(self.alerts_file, "w", encoding="utf-8") as f:
            json.dump(self.alerts, f, ensure_ascii=False, indent=2)

    def add_alert(self, stock_code: str, stock_name: str,
                  alert_type: str, target_price: int, memo: str = "") -> dict:
        """
        가격 알림 추가

        Args:
            stock_code: 종목코드
            stock_name: 종목명
            alert_type: "below" (이하) 또는 "above" (이상)
            target_price: 목표가
            memo: 메모

        Returns:
            추가된 알림 정보
        """
        alert = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "alert_type": alert_type,
            "target_price": target_price,
            "memo": memo,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "triggered": False,
            "triggered_at": ""
        }

        self.alerts.append(alert)
        self._save_alerts()

        return alert

    def remove_alert(self, stock_code: str, target_price: int = None) -> bool:
        """
        가격 알림 삭제

        Args:
            stock_code: 종목코드
            target_price: 목표가 (None이면 해당 종목 전체 삭제)

        Returns:
            삭제 성공 여부
        """
        before_count = len(self.alerts)

        if target_price:
            self.alerts = [
                a for a in self.alerts
                if not (a["stock_code"] == stock_code and a["target_price"] == target_price)
            ]
        else:
            self.alerts = [a for a in self.alerts if a["stock_code"] != stock_code]

        self._save_alerts()
        return len(self.alerts) < before_count

    def get_active_alerts(self) -> list[dict]:
        """발동되지 않은 활성 알림 목록"""
        return [a for a in self.alerts if not a.get("triggered", False)]

    def get_all_alerts(self) -> list[dict]:
        """전체 알림 목록"""
        return self.alerts

    def get_watchlist_stocks(self) -> list[str]:
        """
        관심종목(알림 등록된 종목) 코드 리스트 반환 (중복 제거)

        Returns:
            종목코드 리스트
        """
        return list({alert["stock_code"] for alert in self.alerts})

    def get_watchlist_with_prices(self) -> list[dict]:
        """
        관심종목의 현재가 정보 조회

        Returns:
            [{"stock_code", "stock_name", "current_price", "change_rate", "target_price", "memo"}, ...]
        """
        watchlist = []
        seen_codes = set()

        for alert in self.alerts:
            code = alert["stock_code"]
            if code in seen_codes:
                continue
            seen_codes.add(code)

            price_info = get_realtime_price(code)
            if price_info:
                watchlist.append({
                    "stock_code": code,
                    "stock_name": alert["stock_name"],
                    "current_price": price_info.current_price,
                    "change_price": price_info.change_price,
                    "change_rate": price_info.change_rate,
                    "target_price": alert["target_price"],
                    "alert_type": alert["alert_type"],
                    "memo": alert.get("memo", "")
                })

        return watchlist

    def check_alerts(self) -> list[dict]:
        """
        알림 조건 확인 및 발동된 알림 반환

        Returns:
            발동된 알림 리스트 (현재가 정보 포함)
        """
        triggered_alerts = []
        active_alerts = self.get_active_alerts()

        if not active_alerts:
            return []

        for alert in active_alerts:
            price_info = get_realtime_price(alert["stock_code"])

            if not price_info:
                continue

            current_price = price_info.current_price
            target_price = alert["target_price"]
            alert_type = alert["alert_type"]

            # 조건 확인
            condition_met = False
            if alert_type == "below" and current_price <= target_price:
                condition_met = True
            elif alert_type == "above" and current_price >= target_price:
                condition_met = True

            if condition_met:
                # 알림 발동 처리
                alert["triggered"] = True
                alert["triggered_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

                triggered_alerts.append({
                    **alert,
                    "current_price": current_price,
                    "change_rate": price_info.change_rate
                })

        # 변경사항 저장
        if triggered_alerts:
            self._save_alerts()

        return triggered_alerts

    def clear_triggered_alerts(self):
        """발동된 알림 삭제"""
        self.alerts = [a for a in self.alerts if not a.get("triggered", False)]
        self._save_alerts()

    def reset_alert(self, stock_code: str, target_price: int):
        """발동된 알림을 다시 활성화"""
        for alert in self.alerts:
            if alert["stock_code"] == stock_code and alert["target_price"] == target_price:
                alert["triggered"] = False
                alert["triggered_at"] = ""
                self._save_alerts()
                return True
        return False


def format_alert_list(alerts: list[dict]) -> str:
    """알림 목록을 텍스트로 포맷"""
    if not alerts:
        return "설정된 가격 알림이 없습니다."

    lines = ["📋 *가격 알림 목록*", ""]

    for i, alert in enumerate(alerts, 1):
        alert_type_text = "이하" if alert["alert_type"] == "below" else "이상"
        status = "✅" if alert.get("triggered") else "⏳"
        memo = f" ({alert['memo']})" if alert.get("memo") else ""

        lines.append(
            f"{status} {i}. *{alert['stock_name']}* `{alert['stock_code']}`\n"
            f"   {alert['target_price']:,}원 {alert_type_text}{memo}"
        )

    return "\n".join(lines)


if __name__ == "__main__":
    # 테스트
    manager = PriceAlertManager()

    print("=== 가격 알림 테스트 ===\n")

    # 알림 추가 테스트
    print("1. 알림 추가")
    manager.add_alert("005930", "삼성전자", "below", 70000, "분할매수 1차")
    manager.add_alert("005930", "삼성전자", "below", 65000, "분할매수 2차")
    manager.add_alert("000660", "SK하이닉스", "above", 200000, "익절 목표")

    # 알림 목록 출력
    print(format_alert_list(manager.get_all_alerts()))

    # 알림 체크
    print("\n2. 알림 조건 확인 중...")
    triggered = manager.check_alerts()
    if triggered:
        print(f"   발동된 알림: {len(triggered)}건")
        for t in triggered:
            print(f"   - {t['stock_name']}: 현재가 {t['current_price']:,}원")
    else:
        print("   발동된 알림 없음")
