"""
KRX 투자자별 매매동향 수집 (pykrx 사용)
- 외국인/기관 순매수/순매도 실제 데이터
"""

from datetime import datetime, timedelta
from typing import Optional
import math

try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False
    print("[WARNING] pykrx 라이브러리가 설치되지 않았습니다. pip install pykrx")

import FinanceDataReader as fdr


class KrxCollector:
    """KRX 투자자별 매매동향 수집"""

    def __init__(self):
        pass

    def _get_recent_trading_date(self) -> str:
        """최근 거래일 반환 (주말/공휴일 제외)"""
        today = datetime.now()

        # 오전 9시 이전이면 전일 데이터
        if today.hour < 9:
            today -= timedelta(days=1)

        # 주말 제외
        while today.weekday() >= 5:
            today -= timedelta(days=1)

        return today.strftime("%Y%m%d")

    def _safe_int(self, val, default=0):
        """안전한 int 변환"""
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return default
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    def _safe_float(self, val, default=0.0):
        """안전한 float 변환"""
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    def get_top_foreign_net_buy(self, date: Optional[str] = None, top_n: int = 20) -> list[dict]:
        """
        외국인 순매수 상위 종목 조회 (실제 KRX 데이터)

        Returns:
            외국인 순매수 상위 종목 리스트
        """
        if not date:
            date = self._get_recent_trading_date()

        if not PYKRX_AVAILABLE:
            print("    [ERROR] pykrx 라이브러리 필요. pip install pykrx")
            return []

        try:
            # KOSPI 외국인 순매수 상위
            df_kospi = stock.get_market_net_purchases_of_equities_by_ticker(
                date, date, market="KOSPI", investor="외국인"
            )

            # KOSDAQ 외국인 순매수 상위
            df_kosdaq = stock.get_market_net_purchases_of_equities_by_ticker(
                date, date, market="KOSDAQ", investor="외국인"
            )

            results = []

            # KOSPI 처리
            if df_kospi is not None and not df_kospi.empty:
                # 순매수금액 기준 정렬
                if "순매수" in df_kospi.columns:
                    df_kospi = df_kospi.sort_values("순매수", ascending=False)

                for idx, (ticker, row) in enumerate(df_kospi.head(top_n).iterrows()):
                    net_buy = self._safe_int(row.get("순매수", 0))
                    if net_buy <= 0:  # 순매수만
                        continue

                    # 종목명 조회
                    try:
                        stock_name = stock.get_market_ticker_name(ticker)
                    except:
                        stock_name = ticker

                    # 현재가/등락률 조회
                    try:
                        ohlcv = stock.get_market_ohlcv_by_date(date, date, ticker)
                        if ohlcv is not None and not ohlcv.empty:
                            close_price = self._safe_int(ohlcv.iloc[-1].get("종가", 0))
                            change_rate = self._safe_float(ohlcv.iloc[-1].get("등락률", 0))
                        else:
                            close_price = 0
                            change_rate = 0.0
                    except:
                        close_price = 0
                        change_rate = 0.0

                    results.append({
                        "type": "foreigner_net_buy",
                        "date": date,
                        "stock_code": ticker,
                        "stock_name": stock_name,
                        "net_buy_amount": net_buy,  # 원 단위
                        "close_price": str(close_price),
                        "change_rate": str(round(change_rate, 2)),
                        "market": "KOSPI",
                    })

            # KOSDAQ 처리
            if df_kosdaq is not None and not df_kosdaq.empty:
                if "순매수" in df_kosdaq.columns:
                    df_kosdaq = df_kosdaq.sort_values("순매수", ascending=False)

                for idx, (ticker, row) in enumerate(df_kosdaq.head(top_n // 2).iterrows()):
                    net_buy = self._safe_int(row.get("순매수", 0))
                    if net_buy <= 0:
                        continue

                    try:
                        stock_name = stock.get_market_ticker_name(ticker)
                    except:
                        stock_name = ticker

                    try:
                        ohlcv = stock.get_market_ohlcv_by_date(date, date, ticker)
                        if ohlcv is not None and not ohlcv.empty:
                            close_price = self._safe_int(ohlcv.iloc[-1].get("종가", 0))
                            change_rate = self._safe_float(ohlcv.iloc[-1].get("등락률", 0))
                        else:
                            close_price = 0
                            change_rate = 0.0
                    except:
                        close_price = 0
                        change_rate = 0.0

                    results.append({
                        "type": "foreigner_net_buy",
                        "date": date,
                        "stock_code": ticker,
                        "stock_name": stock_name,
                        "net_buy_amount": net_buy,
                        "close_price": str(close_price),
                        "change_rate": str(round(change_rate, 2)),
                        "market": "KOSDAQ",
                    })

            # 순매수금액 기준 정렬
            results.sort(key=lambda x: x["net_buy_amount"], reverse=True)
            return results[:top_n]

        except Exception as e:
            print(f"    [ERROR] 외국인 데이터 조회 실패: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_top_institution_net_buy(self, date: Optional[str] = None, top_n: int = 20) -> list[dict]:
        """
        기관 순매수 상위 종목 조회 (실제 KRX 데이터)

        Returns:
            기관 순매수 상위 종목 리스트
        """
        if not date:
            date = self._get_recent_trading_date()

        if not PYKRX_AVAILABLE:
            print("    [ERROR] pykrx 라이브러리 필요. pip install pykrx")
            return []

        try:
            # KOSPI 기관 순매수 상위
            df_kospi = stock.get_market_net_purchases_of_equities_by_ticker(
                date, date, market="KOSPI", investor="기관합계"
            )

            # KOSDAQ 기관 순매수 상위
            df_kosdaq = stock.get_market_net_purchases_of_equities_by_ticker(
                date, date, market="KOSDAQ", investor="기관합계"
            )

            results = []

            # KOSPI 처리
            if df_kospi is not None and not df_kospi.empty:
                if "순매수" in df_kospi.columns:
                    df_kospi = df_kospi.sort_values("순매수", ascending=False)

                for idx, (ticker, row) in enumerate(df_kospi.head(top_n).iterrows()):
                    net_buy = self._safe_int(row.get("순매수", 0))
                    if net_buy <= 0:
                        continue

                    try:
                        stock_name = stock.get_market_ticker_name(ticker)
                    except:
                        stock_name = ticker

                    try:
                        ohlcv = stock.get_market_ohlcv_by_date(date, date, ticker)
                        if ohlcv is not None and not ohlcv.empty:
                            close_price = self._safe_int(ohlcv.iloc[-1].get("종가", 0))
                            change_rate = self._safe_float(ohlcv.iloc[-1].get("등락률", 0))
                        else:
                            close_price = 0
                            change_rate = 0.0
                    except:
                        close_price = 0
                        change_rate = 0.0

                    results.append({
                        "type": "institution_net_buy",
                        "date": date,
                        "stock_code": ticker,
                        "stock_name": stock_name,
                        "net_buy_amount": net_buy,
                        "close_price": str(close_price),
                        "change_rate": str(round(change_rate, 2)),
                        "market": "KOSPI",
                    })

            # KOSDAQ 처리
            if df_kosdaq is not None and not df_kosdaq.empty:
                if "순매수" in df_kosdaq.columns:
                    df_kosdaq = df_kosdaq.sort_values("순매수", ascending=False)

                for idx, (ticker, row) in enumerate(df_kosdaq.head(top_n // 2).iterrows()):
                    net_buy = self._safe_int(row.get("순매수", 0))
                    if net_buy <= 0:
                        continue

                    try:
                        stock_name = stock.get_market_ticker_name(ticker)
                    except:
                        stock_name = ticker

                    try:
                        ohlcv = stock.get_market_ohlcv_by_date(date, date, ticker)
                        if ohlcv is not None and not ohlcv.empty:
                            close_price = self._safe_int(ohlcv.iloc[-1].get("종가", 0))
                            change_rate = self._safe_float(ohlcv.iloc[-1].get("등락률", 0))
                        else:
                            close_price = 0
                            change_rate = 0.0
                    except:
                        close_price = 0
                        change_rate = 0.0

                    results.append({
                        "type": "institution_net_buy",
                        "date": date,
                        "stock_code": ticker,
                        "stock_name": stock_name,
                        "net_buy_amount": net_buy,
                        "close_price": str(close_price),
                        "change_rate": str(round(change_rate, 2)),
                        "market": "KOSDAQ",
                    })

            # 순매수금액 기준 정렬
            results.sort(key=lambda x: x["net_buy_amount"], reverse=True)
            return results[:top_n]

        except Exception as e:
            print(f"    [ERROR] 기관 데이터 조회 실패: {e}")
            import traceback
            traceback.print_exc()
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

    print("=== 외국인 순매수 TOP 10 ===")
    foreign_top = collector.get_top_foreign_net_buy(top_n=10)
    for item in foreign_top:
        amount_billion = item["net_buy_amount"] / 100_000_000
        print(f"{item['stock_name']} ({item['stock_code']}): {amount_billion:,.1f}억원")

    print("\n=== 기관 순매수 TOP 10 ===")
    inst_top = collector.get_top_institution_net_buy(top_n=10)
    for item in inst_top:
        amount_billion = item["net_buy_amount"] / 100_000_000
        print(f"{item['stock_name']} ({item['stock_code']}): {amount_billion:,.1f}억원")
