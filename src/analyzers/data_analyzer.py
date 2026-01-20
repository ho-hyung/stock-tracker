"""
데이터 분석 강화 모듈
- 연속 매수일 추적
- 가격 변동 연동 분석
- 섹터별 자금 흐름 분석
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, asdict
import FinanceDataReader as fdr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# 데이터 저장 경로
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


@dataclass
class ConsecutiveBuyStock:
    """연속 매수 종목 정보"""
    stock_code: str
    stock_name: str
    consecutive_days: int
    investor_type: str  # "foreigner" or "institution"
    total_net_buy: int  # 연속 기간 총 순매수
    avg_daily_buy: int  # 일평균 순매수
    price_change_pct: float  # 연속 기간 주가 변동률


@dataclass
class MomentumStock:
    """순매수 + 주가 상승 종목"""
    stock_code: str
    stock_name: str
    net_buy_amount: int
    price_change_pct: float
    volume_ratio: float  # 평균 대비 거래량 비율
    investor_type: str


@dataclass
class SectorFlow:
    """섹터별 자금 흐름"""
    sector: str
    net_buy_amount: int
    stock_count: int
    top_stocks: list  # 상위 종목들
    flow_direction: str  # "inflow" or "outflow"


class DataAnalyzer:
    """데이터 분석 강화"""

    # 섹터 분류 (종목코드 기반 간이 분류)
    SECTOR_MAPPING = {
        # 반도체
        "005930": "반도체", "000660": "반도체", "402340": "반도체",
        # 자동차
        "005380": "자동차", "000270": "자동차", "012330": "자동차",
        # 바이오
        "207940": "바이오", "068270": "바이오", "035720": "바이오",
        # 2차전지
        "373220": "2차전지", "006400": "2차전지", "051910": "2차전지",
        # IT/인터넷
        "035420": "IT/인터넷", "035720": "IT/인터넷", "263750": "IT/인터넷",
        # 금융
        "105560": "금융", "055550": "금융", "086790": "금융",
        # 철강/화학
        "005490": "철강/화학", "010130": "철강/화학", "051910": "철강/화학",
    }

    def __init__(self):
        self.history_file = os.path.join(DATA_DIR, "trading_history.json")
        self._ensure_data_dir()
        self.history = self._load_history()

    def _ensure_data_dir(self):
        """데이터 디렉토리 생성"""
        os.makedirs(DATA_DIR, exist_ok=True)

    def _load_history(self) -> dict:
        """히스토리 데이터 로드"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {"foreigner": {}, "institution": {}}
        return {"foreigner": {}, "institution": {}}

    def _save_history(self):
        """히스토리 데이터 저장"""
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def update_history(self, foreigner_data: list, institution_data: list):
        """오늘 데이터로 히스토리 업데이트"""
        today = datetime.now().strftime("%Y-%m-%d")

        # 외국인 데이터 업데이트
        for item in foreigner_data:
            code = item["stock_code"]
            if code not in self.history["foreigner"]:
                self.history["foreigner"][code] = {
                    "stock_name": item["stock_name"],
                    "daily_data": {}
                }
            self.history["foreigner"][code]["daily_data"][today] = {
                "net_buy_amount": item["net_buy_amount"],
                "close_price": item.get("close_price", 0),
                "change_rate": item.get("change_rate", 0),
            }

        # 기관 데이터 업데이트
        for item in institution_data:
            code = item["stock_code"]
            if code not in self.history["institution"]:
                self.history["institution"][code] = {
                    "stock_name": item["stock_name"],
                    "daily_data": {}
                }
            self.history["institution"][code]["daily_data"][today] = {
                "net_buy_amount": item["net_buy_amount"],
                "close_price": item.get("close_price", 0),
                "change_rate": item.get("change_rate", 0),
            }

        # 오래된 데이터 정리 (30일 이상)
        self._cleanup_old_data(days=30)
        self._save_history()

    def _cleanup_old_data(self, days: int = 30):
        """오래된 데이터 정리"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        for investor_type in ["foreigner", "institution"]:
            for code in list(self.history[investor_type].keys()):
                daily_data = self.history[investor_type][code]["daily_data"]
                # 오래된 날짜 제거
                old_dates = [d for d in daily_data.keys() if d < cutoff]
                for d in old_dates:
                    del daily_data[d]
                # 데이터가 없으면 종목 자체 제거
                if not daily_data:
                    del self.history[investor_type][code]

    def get_consecutive_buy_stocks(
        self,
        investor_type: str = "foreigner",
        min_days: int = 3,
        top_n: int = 10
    ) -> list[ConsecutiveBuyStock]:
        """
        연속 순매수 종목 조회

        Args:
            investor_type: "foreigner" or "institution"
            min_days: 최소 연속일
            top_n: 상위 N개

        Returns:
            연속 매수 종목 리스트
        """
        results = []

        for code, data in self.history.get(investor_type, {}).items():
            daily_data = data["daily_data"]
            if not daily_data:
                continue

            # 날짜순 정렬
            sorted_dates = sorted(daily_data.keys(), reverse=True)

            # 연속 매수일 계산
            consecutive_days = 0
            total_net_buy = 0
            first_price = None
            last_price = None

            for date in sorted_dates:
                day_data = daily_data[date]
                net_buy = day_data.get("net_buy_amount", 0)

                if net_buy > 0:
                    consecutive_days += 1
                    total_net_buy += net_buy
                    if first_price is None:
                        try:
                            first_price = float(str(day_data.get("close_price", 0)).replace(",", ""))
                        except:
                            first_price = 0
                    try:
                        last_price = float(str(day_data.get("close_price", 0)).replace(",", ""))
                    except:
                        last_price = 0
                else:
                    break

            if consecutive_days >= min_days:
                # 주가 변동률 계산
                price_change = 0
                if first_price and last_price and last_price > 0:
                    price_change = ((first_price - last_price) / last_price) * 100

                results.append(ConsecutiveBuyStock(
                    stock_code=code,
                    stock_name=data["stock_name"],
                    consecutive_days=consecutive_days,
                    investor_type=investor_type,
                    total_net_buy=total_net_buy,
                    avg_daily_buy=total_net_buy // consecutive_days,
                    price_change_pct=round(price_change, 2)
                ))

        # 연속일 기준 정렬
        results.sort(key=lambda x: (x.consecutive_days, x.total_net_buy), reverse=True)
        return results[:top_n]

    def get_momentum_stocks(
        self,
        foreigner_data: list,
        institution_data: list,
        min_price_change: float = 0.0,
        top_n: int = 10
    ) -> list[MomentumStock]:
        """
        순매수 + 주가 상승 종목 필터링

        Args:
            foreigner_data: 외국인 데이터
            institution_data: 기관 데이터
            min_price_change: 최소 주가 변동률 (%)
            top_n: 상위 N개

        Returns:
            모멘텀 종목 리스트
        """
        results = []

        # 외국인 데이터 분석
        for item in foreigner_data:
            try:
                change_rate = float(str(item.get("change_rate", 0)).replace("%", ""))
            except:
                change_rate = 0

            if item["net_buy_amount"] > 0 and change_rate >= min_price_change:
                results.append(MomentumStock(
                    stock_code=item["stock_code"],
                    stock_name=item["stock_name"],
                    net_buy_amount=item["net_buy_amount"],
                    price_change_pct=change_rate,
                    volume_ratio=1.0,  # TODO: 평균 거래량 대비 비율
                    investor_type="foreigner"
                ))

        # 기관 데이터 분석
        for item in institution_data:
            try:
                change_rate = float(str(item.get("change_rate", 0)).replace("%", ""))
            except:
                change_rate = 0

            if item["net_buy_amount"] > 0 and change_rate >= min_price_change:
                # 이미 외국인에서 추가된 종목인지 확인
                existing = [r for r in results if r.stock_code == item["stock_code"]]
                if not existing:
                    results.append(MomentumStock(
                        stock_code=item["stock_code"],
                        stock_name=item["stock_name"],
                        net_buy_amount=item["net_buy_amount"],
                        price_change_pct=change_rate,
                        volume_ratio=1.0,
                        investor_type="institution"
                    ))

        # 순매수 + 상승률 복합 점수로 정렬
        results.sort(
            key=lambda x: (x.price_change_pct * 0.4 + (x.net_buy_amount / 100_000_000) * 0.6),
            reverse=True
        )
        return results[:top_n]

    def get_sector_flow(
        self,
        foreigner_data: list,
        institution_data: list,
        top_n: int = 5
    ) -> list[SectorFlow]:
        """
        섹터별 자금 흐름 분석

        Args:
            foreigner_data: 외국인 데이터
            institution_data: 기관 데이터
            top_n: 상위 N개 섹터

        Returns:
            섹터별 자금 흐름 리스트
        """
        sector_data = {}

        # 모든 데이터 합산
        all_data = foreigner_data + institution_data

        for item in all_data:
            code = item["stock_code"]
            sector = self.SECTOR_MAPPING.get(code, "기타")

            if sector not in sector_data:
                sector_data[sector] = {
                    "net_buy_amount": 0,
                    "stocks": []
                }

            sector_data[sector]["net_buy_amount"] += item["net_buy_amount"]
            sector_data[sector]["stocks"].append({
                "stock_name": item["stock_name"],
                "net_buy_amount": item["net_buy_amount"]
            })

        # SectorFlow 객체 생성
        results = []
        for sector, data in sector_data.items():
            if sector == "기타":
                continue

            # 상위 종목 정렬
            top_stocks = sorted(
                data["stocks"],
                key=lambda x: x["net_buy_amount"],
                reverse=True
            )[:3]

            results.append(SectorFlow(
                sector=sector,
                net_buy_amount=data["net_buy_amount"],
                stock_count=len(data["stocks"]),
                top_stocks=[s["stock_name"] for s in top_stocks],
                flow_direction="inflow" if data["net_buy_amount"] > 0 else "outflow"
            ))

        # 순매수 금액 기준 정렬
        results.sort(key=lambda x: abs(x.net_buy_amount), reverse=True)
        return results[:top_n]

    def get_all_analysis(
        self,
        foreigner_data: list,
        institution_data: list
    ) -> dict:
        """모든 분석 결과 반환"""
        # 히스토리 업데이트
        self.update_history(foreigner_data, institution_data)

        return {
            "consecutive_foreigner": self.get_consecutive_buy_stocks("foreigner", min_days=2, top_n=5),
            "consecutive_institution": self.get_consecutive_buy_stocks("institution", min_days=2, top_n=5),
            "momentum_stocks": self.get_momentum_stocks(foreigner_data, institution_data, min_price_change=1.0, top_n=5),
            "sector_flow": self.get_sector_flow(foreigner_data, institution_data, top_n=5)
        }


if __name__ == "__main__":
    # 테스트
    analyzer = DataAnalyzer()

    # 테스트 데이터
    test_foreigner = [
        {"stock_code": "005930", "stock_name": "삼성전자", "net_buy_amount": 500_000_000_000, "change_rate": "2.5"},
        {"stock_code": "000660", "stock_name": "SK하이닉스", "net_buy_amount": 300_000_000_000, "change_rate": "1.8"},
    ]
    test_institution = [
        {"stock_code": "005930", "stock_name": "삼성전자", "net_buy_amount": 200_000_000_000, "change_rate": "2.5"},
        {"stock_code": "373220", "stock_name": "LG에너지솔루션", "net_buy_amount": 150_000_000_000, "change_rate": "3.2"},
    ]

    results = analyzer.get_all_analysis(test_foreigner, test_institution)

    print("=== 모멘텀 종목 ===")
    for stock in results["momentum_stocks"]:
        print(f"  {stock.stock_name}: +{stock.price_change_pct}%, {stock.net_buy_amount/100_000_000:.0f}억원")

    print("\n=== 섹터별 자금 흐름 ===")
    for sector in results["sector_flow"]:
        print(f"  {sector.sector}: {sector.net_buy_amount/100_000_000:.0f}억원 ({sector.flow_direction})")
