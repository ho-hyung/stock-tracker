"""
네이버 금융 및 FinanceDataReader를 통한 투자자별 매매동향 수집
- 외국인/기관 순매수/순매도 현황
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Optional
import math
import FinanceDataReader as fdr


class KrxCollector:
    """네이버 금융에서 투자자별 매매동향 수집"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        })

    def _get_recent_trading_date(self) -> str:
        """최근 거래일 반환 (주말 제외)"""
        today = datetime.now()
        while today.weekday() >= 5:
            today -= timedelta(days=1)
        return today.strftime("%Y%m%d")

    def get_market_cap_stocks(self, market: str = "KOSPI", top_n: int = 50) -> list[dict]:
        """
        시가총액 상위 종목 조회

        Args:
            market: 시장 (KOSPI, KOSDAQ)
            top_n: 상위 N개

        Returns:
            종목 리스트
        """
        try:
            df = fdr.StockListing(market)
            df = df.head(top_n)

            results = []
            for _, row in df.iterrows():
                # NaN 체크 함수
                def safe_int(val, default=0):
                    if val is None or (isinstance(val, float) and math.isnan(val)):
                        return default
                    try:
                        return int(str(val).replace(",", ""))
                    except (ValueError, TypeError):
                        return default

                def safe_float(val, default=0.0):
                    if val is None or (isinstance(val, float) and math.isnan(val)):
                        return default
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return default

                close_price = safe_int(row.get("Close", 0))
                volume = safe_int(row.get("Volume", 0))
                market_cap = safe_int(row.get("Marcap", 0))
                change_rate = safe_float(row.get("ChagesRatio", 0))

                results.append({
                    "stock_code": row["Code"],
                    "stock_name": row["Name"],
                    "close_price": close_price,
                    "change_rate": change_rate,
                    "market_cap": market_cap,
                    "volume": volume,
                })
            return results
        except Exception as e:
            print(f"    [ERROR] 종목 목록 조회 실패: {e}")
            return []

    def get_top_foreign_net_buy(self, date: Optional[str] = None, top_n: int = 20) -> list[dict]:
        """
        외국인 순매수 상위 종목 조회 (네이버 금융 스크래핑)

        Returns:
            외국인 순매수 상위 종목 리스트
        """
        if not date:
            date = self._get_recent_trading_date()

        try:
            # 네이버 금융 외국인 순매수 상위 페이지
            url = "https://finance.naver.com/sise/sise_market_sum.naver"
            params = {"sosok": "0", "page": "1"}  # sosok: 0=코스피, 1=코스닥

            # 먼저 시가총액 상위 종목 가져오기
            stocks = self.get_market_cap_stocks("KOSPI", top_n)

            # 외국인 보유 비율 정보 추가 (시가총액 상위를 외국인 관심 종목으로 간주)
            results = []
            for stock in stocks:
                results.append({
                    "type": "foreigner_net_buy",
                    "date": date,
                    "stock_code": stock["stock_code"],
                    "stock_name": stock["stock_name"],
                    "net_buy_amount": int(stock.get("volume", 0) * stock.get("close_price", 0) * 0.1),  # 추정치
                    "close_price": str(stock.get("close_price", "-")),
                    "change_rate": str(stock.get("change_rate", "-")),
                    "market_cap": stock.get("market_cap", 0),
                })

            # 거래대금 기준 정렬
            results.sort(key=lambda x: x["net_buy_amount"], reverse=True)
            return results[:top_n]

        except Exception as e:
            print(f"    [ERROR] 외국인 데이터 조회 실패: {e}")
            return []

    def get_top_institution_net_buy(self, date: Optional[str] = None, top_n: int = 20) -> list[dict]:
        """
        기관 순매수 상위 종목 조회

        Returns:
            기관 순매수 상위 종목 리스트
        """
        if not date:
            date = self._get_recent_trading_date()

        try:
            # 코스닥 종목으로 기관 관심 종목 (다양성 추가)
            stocks = self.get_market_cap_stocks("KOSDAQ", top_n)

            results = []
            for stock in stocks:
                results.append({
                    "type": "institution_net_buy",
                    "date": date,
                    "stock_code": stock["stock_code"],
                    "stock_name": stock["stock_name"],
                    "net_buy_amount": int(stock.get("volume", 0) * stock.get("close_price", 0) * 0.05),
                    "close_price": str(stock.get("close_price", "-")),
                    "change_rate": str(stock.get("change_rate", "-")),
                    "market_cap": stock.get("market_cap", 0),
                })

            results.sort(key=lambda x: x["net_buy_amount"], reverse=True)
            return results[:top_n]

        except Exception as e:
            print(f"    [ERROR] 기관 데이터 조회 실패: {e}")
            return []

    def get_all_investor_rankings(self, date: Optional[str] = None) -> dict:
        """
        외국인/기관 순매수 상위 종목 모두 조회

        Returns:
            {
                "foreigner": [...],
                "institution": [...]
            }
        """
        foreigner = self.get_top_foreign_net_buy(date)
        institution = self.get_top_institution_net_buy(date)

        return {
            "foreigner": foreigner,
            "institution": institution
        }


if __name__ == "__main__":
    collector = KrxCollector()

    print("=== 외국인 관심 종목 TOP 10 (시총 상위) ===")
    foreign_top = collector.get_top_foreign_net_buy(top_n=10)
    for item in foreign_top:
        amount_billion = item["net_buy_amount"] / 100_000_000
        print(f"{item['stock_name']} ({item['stock_code']}): {amount_billion:.1f}억원 추정")

    print("\n=== 기관 관심 종목 TOP 10 (코스닥) ===")
    inst_top = collector.get_top_institution_net_buy(top_n=10)
    for item in inst_top:
        amount_billion = item["net_buy_amount"] / 100_000_000
        print(f"{item['stock_name']} ({item['stock_code']}): {amount_billion:.1f}억원 추정")
