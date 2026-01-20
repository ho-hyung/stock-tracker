"""
실시간 주가 조회 모듈
- 네이버 금융에서 현재가 조회
- 장중 거의 실시간 데이터 제공
"""

import requests
import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class StockPrice:
    """주가 정보"""
    stock_code: str
    stock_name: str
    current_price: int
    change_price: int  # 전일 대비
    change_rate: float  # 등락률 (%)
    high_price: int  # 고가
    low_price: int  # 저가
    open_price: int  # 시가
    volume: int  # 거래량
    market_cap: str  # 시가총액


class NaverPriceFetcher:
    """네이버 금융 실시간 주가 조회"""

    BASE_URL = "https://finance.naver.com/item/main.naver"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.cache = {}

    def _parse_number(self, text: str) -> int:
        """숫자 문자열 파싱 (콤마, 공백 제거)"""
        if not text:
            return 0
        cleaned = re.sub(r'[^\d\-]', '', text.strip())
        return int(cleaned) if cleaned and cleaned != '-' else 0

    def _parse_rate(self, text: str) -> float:
        """등락률 파싱"""
        if not text:
            return 0.0
        cleaned = re.sub(r'[^\d\.\-]', '', text.strip())
        return float(cleaned) if cleaned else 0.0

    def get_current_price(self, stock_code: str) -> Optional[StockPrice]:
        """
        네이버 금융에서 실시간 현재가 조회

        Args:
            stock_code: 종목코드 (예: "005930")

        Returns:
            StockPrice 객체 또는 None
        """
        try:
            url = f"{self.BASE_URL}?code={stock_code}"
            response = self.session.get(url, timeout=5)
            response.raise_for_status()

            html = response.text

            # 종목명 추출
            name_match = re.search(r'<title>([^:]+):', html)
            stock_name = name_match.group(1).strip() if name_match else stock_code

            # 현재가 추출 (blind 클래스 내 숫자)
            price_match = re.search(
                r'<p class="no_today">\s*<em[^>]*>\s*<span class="blind">([0-9,]+)</span>',
                html
            )
            if not price_match:
                # 대체 패턴
                price_match = re.search(r'"now_price"[^>]*>([0-9,]+)<', html)

            current_price = self._parse_number(price_match.group(1)) if price_match else 0

            if current_price == 0:
                return None

            # 전일 대비 추출
            change_match = re.search(
                r'<span class="blind">전일대비</span>\s*<span class="blind">([^<]+)</span>\s*<em[^>]*>\s*<span class="blind">([0-9,]+)</span>',
                html
            )
            if change_match:
                direction = change_match.group(1).strip()
                change_price = self._parse_number(change_match.group(2))
                if "하락" in direction or "마이너스" in direction:
                    change_price = -change_price
            else:
                change_price = 0

            # 등락률 추출
            rate_match = re.search(
                r'<span class="blind">등락률</span>\s*<em[^>]*>\s*<span class="blind">([^<]+)</span>',
                html
            )
            if rate_match:
                rate_text = rate_match.group(1)
                change_rate = self._parse_rate(rate_text)
                if change_price < 0:
                    change_rate = -abs(change_rate)
            else:
                change_rate = 0.0

            # 고가/저가/시가 추출
            high_match = re.search(r'<th>고가</th>\s*<td[^>]*><span[^>]*>([0-9,]+)', html)
            low_match = re.search(r'<th>저가</th>\s*<td[^>]*><span[^>]*>([0-9,]+)', html)
            open_match = re.search(r'<th>시가</th>\s*<td[^>]*><span[^>]*>([0-9,]+)', html)
            volume_match = re.search(r'<th>거래량</th>\s*<td[^>]*><span[^>]*>([0-9,]+)', html)

            high_price = self._parse_number(high_match.group(1)) if high_match else current_price
            low_price = self._parse_number(low_match.group(1)) if low_match else current_price
            open_price = self._parse_number(open_match.group(1)) if open_match else current_price
            volume = self._parse_number(volume_match.group(1)) if volume_match else 0

            # 시가총액 추출
            market_cap_match = re.search(r'<th>시가총액</th>\s*<td>([^<]+)', html)
            market_cap = market_cap_match.group(1).strip() if market_cap_match else "-"

            return StockPrice(
                stock_code=stock_code,
                stock_name=stock_name,
                current_price=current_price,
                change_price=change_price,
                change_rate=change_rate,
                high_price=high_price,
                low_price=low_price,
                open_price=open_price,
                volume=volume,
                market_cap=market_cap
            )

        except Exception as e:
            print(f"    [WARNING] {stock_code} 네이버 조회 실패: {e}")
            return None

    def get_multiple_prices(self, stock_codes: list) -> dict:
        """
        여러 종목 현재가 조회

        Args:
            stock_codes: 종목코드 리스트

        Returns:
            {stock_code: StockPrice} 딕셔너리
        """
        results = {}
        for code in stock_codes:
            price = self.get_current_price(code)
            if price:
                results[code] = price
        return results


# 싱글톤 인스턴스
_fetcher = None


def get_realtime_price(stock_code: str) -> Optional[StockPrice]:
    """실시간 현재가 조회 (편의 함수)"""
    global _fetcher
    if _fetcher is None:
        _fetcher = NaverPriceFetcher()
    return _fetcher.get_current_price(stock_code)


def get_realtime_prices(stock_codes: list) -> dict:
    """여러 종목 실시간 현재가 조회 (편의 함수)"""
    global _fetcher
    if _fetcher is None:
        _fetcher = NaverPriceFetcher()
    return _fetcher.get_multiple_prices(stock_codes)


if __name__ == "__main__":
    # 테스트
    print("=" * 50)
    print("네이버 금융 실시간 주가 조회 테스트")
    print("=" * 50)

    test_codes = ["005930", "000660", "373220", "035420"]

    for code in test_codes:
        price = get_realtime_price(code)
        if price:
            print(f"\n{price.stock_name} ({price.stock_code})")
            print(f"  현재가: {price.current_price:,}원")
            print(f"  전일대비: {price.change_price:+,}원 ({price.change_rate:+.2f}%)")
            print(f"  고가/저가: {price.high_price:,} / {price.low_price:,}")
            print(f"  거래량: {price.volume:,}")
        else:
            print(f"\n{code}: 조회 실패")
