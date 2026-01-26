"""
네이버 금융 기반 투자자별 매매동향 수집
- 외국인/기관 순매수 상위 종목
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Optional
import re
import time


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
        if today.hour < 9:
            today -= timedelta(days=1)
        while today.weekday() >= 5:
            today -= timedelta(days=1)
        return today.strftime("%Y%m%d")

    def _safe_int(self, val, default=0):
        """안전한 int 변환"""
        if val is None:
            return default
        try:
            clean = str(val).replace(",", "").replace(" ", "").strip()
            clean = clean.replace("+", "").replace("−", "-").replace("▲", "").replace("▼", "-")
            if not clean or clean == '-':
                return default
            return int(float(clean))
        except (ValueError, TypeError):
            return default

    def _parse_change_rate(self, text: str) -> float:
        """등락률 파싱"""
        text = text.strip()
        if '상한' in text:
            return 30.0
        if '하한' in text:
            return -30.0

        match = re.search(r'[-+]?\d+\.?\d*', text.replace(',', ''))
        if match:
            val = float(match.group())
            if '하락' in text or '▼' in text or '−' in text:
                return -abs(val)
            return val
        return 0.0

    def _get_market_cap_stocks(self, market: str = "KOSPI", top_n: int = 50) -> list[dict]:
        """시가총액 상위 종목 조회"""
        results = []
        sosok = 0 if market == "KOSPI" else 1

        try:
            for page in range(1, 4):  # 3페이지까지
                url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}"
                resp = self.session.get(url, timeout=10)
                resp.encoding = 'euc-kr'
                soup = BeautifulSoup(resp.text, 'html.parser')

                table = soup.find('table', class_='type_2')
                if not table:
                    continue

                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) < 7:
                        continue

                    name_tag = cols[1].find('a')
                    if not name_tag or 'code=' not in name_tag.get('href', ''):
                        continue

                    name = name_tag.get_text(strip=True)
                    code_match = re.search(r'code=(\d{6})', name_tag.get('href', ''))
                    code = code_match.group(1) if code_match else ''

                    if not name or not code:
                        continue

                    price = self._safe_int(cols[2].get_text(strip=True))
                    change_rate = self._parse_change_rate(cols[3].get_text(strip=True))

                    results.append({
                        "stock_code": code,
                        "stock_name": name,
                        "close_price": price,
                        "change_rate": change_rate,
                        "market": market,
                    })

                    if len(results) >= top_n:
                        return results

        except Exception as e:
            print(f"    [ERROR] 시가총액 데이터 조회 실패: {e}")

        return results[:top_n]

    def _get_stock_investor_data(self, code: str) -> dict:
        """
        개별 종목의 외국인/기관 순매매 데이터 조회

        Returns:
            {
                "foreign_net": 외국인 순매매량,
                "institution_net": 기관 순매매량,
                "foreign_holding_pct": 외국인 보유율
            }
        """
        try:
            url = f"https://finance.naver.com/item/frgn.naver?code={code}"
            resp = self.session.get(url, timeout=5)
            resp.encoding = 'euc-kr'
            soup = BeautifulSoup(resp.text, 'html.parser')

            # type2 테이블에서 최근 데이터 찾기
            tables = soup.find_all('table', class_='type2')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    # 날짜, 종가, 전일비, 등락률, 거래량, 기관, 외국인, 보유주수, 보유율
                    if len(cols) >= 8:
                        date_text = cols[0].get_text(strip=True)
                        if re.match(r'\d{4}\.\d{2}\.\d{2}', date_text):
                            inst_net = self._safe_int(cols[5].get_text(strip=True))
                            foreign_net = self._safe_int(cols[6].get_text(strip=True))
                            foreign_pct_text = cols[8].get_text(strip=True) if len(cols) > 8 else "0"
                            foreign_pct = self._parse_change_rate(foreign_pct_text)

                            return {
                                "foreign_net": foreign_net,
                                "institution_net": inst_net,
                                "foreign_holding_pct": foreign_pct
                            }

        except Exception as e:
            pass  # 개별 종목 실패는 무시

        return {"foreign_net": 0, "institution_net": 0, "foreign_holding_pct": 0}

    def get_top_foreign_net_buy(self, date: Optional[str] = None, top_n: int = 20) -> list[dict]:
        """
        외국인 순매수 상위 종목 조회

        Returns:
            외국인 순매수 상위 종목 리스트
        """
        if not date:
            date = self._get_recent_trading_date()

        results = []

        try:
            # KOSPI + KOSDAQ 시가총액 상위 종목 가져오기
            kospi_stocks = self._get_market_cap_stocks("KOSPI", 40)
            kosdaq_stocks = self._get_market_cap_stocks("KOSDAQ", 20)
            all_stocks = kospi_stocks + kosdaq_stocks

            print(f"    - 시가총액 상위 {len(all_stocks)}개 종목 외국인 매매 조회 중...")

            for i, stock in enumerate(all_stocks):
                # API 부하 방지를 위한 딜레이
                if i > 0 and i % 10 == 0:
                    time.sleep(0.5)

                investor_data = self._get_stock_investor_data(stock["stock_code"])
                foreign_net = investor_data["foreign_net"]

                if foreign_net > 0:  # 순매수만
                    net_buy_amount = foreign_net * stock["close_price"]

                    results.append({
                        "type": "foreigner_net_buy",
                        "date": date,
                        "stock_code": stock["stock_code"],
                        "stock_name": stock["stock_name"],
                        "net_buy_amount": net_buy_amount,
                        "net_buy_volume": foreign_net,
                        "close_price": str(stock["close_price"]),
                        "change_rate": str(round(stock["change_rate"], 2)),
                        "market": stock["market"],
                        "foreign_holding_pct": investor_data["foreign_holding_pct"],
                    })

        except Exception as e:
            print(f"    [ERROR] 외국인 데이터 조회 실패: {e}")
            import traceback
            traceback.print_exc()

        # 순매수금액 기준 정렬
        results.sort(key=lambda x: x["net_buy_amount"], reverse=True)
        return results[:top_n]

    def get_top_institution_net_buy(self, date: Optional[str] = None, top_n: int = 20) -> list[dict]:
        """
        기관 순매수 상위 종목 조회

        Returns:
            기관 순매수 상위 종목 리스트
        """
        if not date:
            date = self._get_recent_trading_date()

        results = []

        try:
            # KOSPI + KOSDAQ 시가총액 상위 종목
            kospi_stocks = self._get_market_cap_stocks("KOSPI", 40)
            kosdaq_stocks = self._get_market_cap_stocks("KOSDAQ", 20)
            all_stocks = kospi_stocks + kosdaq_stocks

            print(f"    - 시가총액 상위 {len(all_stocks)}개 종목 기관 매매 조회 중...")

            for i, stock in enumerate(all_stocks):
                if i > 0 and i % 10 == 0:
                    time.sleep(0.5)

                investor_data = self._get_stock_investor_data(stock["stock_code"])
                inst_net = investor_data["institution_net"]

                if inst_net > 0:  # 순매수만
                    net_buy_amount = inst_net * stock["close_price"]

                    results.append({
                        "type": "institution_net_buy",
                        "date": date,
                        "stock_code": stock["stock_code"],
                        "stock_name": stock["stock_name"],
                        "net_buy_amount": net_buy_amount,
                        "net_buy_volume": inst_net,
                        "close_price": str(stock["close_price"]),
                        "change_rate": str(round(stock["change_rate"], 2)),
                        "market": stock["market"],
                    })

        except Exception as e:
            print(f"    [ERROR] 기관 데이터 조회 실패: {e}")
            import traceback
            traceback.print_exc()

        results.sort(key=lambda x: x["net_buy_amount"], reverse=True)
        return results[:top_n]

    def get_all_investor_rankings(self, date: Optional[str] = None) -> dict:
        """
        외국인/기관 순매수 상위 종목 모두 조회 (최적화 버전)

        한 번의 종목 조회로 외국인/기관 데이터를 모두 수집
        """
        if not date:
            date = self._get_recent_trading_date()

        foreigner_results = []
        institution_results = []

        try:
            # KOSPI + KOSDAQ 시가총액 상위 종목
            kospi_stocks = self._get_market_cap_stocks("KOSPI", 40)
            kosdaq_stocks = self._get_market_cap_stocks("KOSDAQ", 20)
            all_stocks = kospi_stocks + kosdaq_stocks

            print(f"    - 시가총액 상위 {len(all_stocks)}개 종목 투자자별 매매 조회 중...")

            for i, stock in enumerate(all_stocks):
                if i > 0 and i % 10 == 0:
                    time.sleep(0.3)

                investor_data = self._get_stock_investor_data(stock["stock_code"])

                # 외국인 순매수
                foreign_net = investor_data["foreign_net"]
                if foreign_net > 0:
                    foreigner_results.append({
                        "type": "foreigner_net_buy",
                        "date": date,
                        "stock_code": stock["stock_code"],
                        "stock_name": stock["stock_name"],
                        "net_buy_amount": foreign_net * stock["close_price"],
                        "net_buy_volume": foreign_net,
                        "close_price": str(stock["close_price"]),
                        "change_rate": str(round(stock["change_rate"], 2)),
                        "market": stock["market"],
                        "foreign_holding_pct": investor_data["foreign_holding_pct"],
                    })

                # 기관 순매수
                inst_net = investor_data["institution_net"]
                if inst_net > 0:
                    institution_results.append({
                        "type": "institution_net_buy",
                        "date": date,
                        "stock_code": stock["stock_code"],
                        "stock_name": stock["stock_name"],
                        "net_buy_amount": inst_net * stock["close_price"],
                        "net_buy_volume": inst_net,
                        "close_price": str(stock["close_price"]),
                        "change_rate": str(round(stock["change_rate"], 2)),
                        "market": stock["market"],
                    })

        except Exception as e:
            print(f"    [ERROR] 투자자 데이터 조회 실패: {e}")

        # 정렬
        foreigner_results.sort(key=lambda x: x["net_buy_amount"], reverse=True)
        institution_results.sort(key=lambda x: x["net_buy_amount"], reverse=True)

        return {
            "foreigner": foreigner_results[:20],
            "institution": institution_results[:20]
        }


if __name__ == "__main__":
    collector = KrxCollector()

    print("=== 외국인/기관 순매수 TOP 10 ===\n")
    data = collector.get_all_investor_rankings()

    print("\n📈 외국인 순매수 TOP 10:")
    for i, item in enumerate(data["foreigner"][:10], 1):
        amount_billion = item["net_buy_amount"] / 100_000_000
        print(f"  {i}. {item['stock_name']} ({item['stock_code']}): {amount_billion:,.1f}억원 ({item['change_rate']}%)")

    print("\n🏦 기관 순매수 TOP 10:")
    for i, item in enumerate(data["institution"][:10], 1):
        amount_billion = item["net_buy_amount"] / 100_000_000
        print(f"  {i}. {item['stock_name']} ({item['stock_code']}): {amount_billion:,.1f}억원 ({item['change_rate']}%)")
