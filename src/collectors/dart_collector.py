"""
DART(전자공시시스템) API를 통한 공시 데이터 수집
- 대량보유 공시 (5% 이상 지분 보유/변동)
- 임원/주요주주 주식 거래 공시
"""

import requests
from datetime import datetime, timedelta
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import DART_API_KEY


class DartCollector:
    BASE_URL = "https://opendart.fss.or.kr/api"

    def __init__(self):
        self.api_key = DART_API_KEY
        if not self.api_key:
            raise ValueError("DART_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

    def _request(self, endpoint: str, params: dict) -> dict:
        """DART API 요청 공통 메서드"""
        params["crtfc_key"] = self.api_key
        response = requests.get(f"{self.BASE_URL}/{endpoint}", params=params)
        response.raise_for_status()
        return response.json()

    def get_major_shareholder_reports(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        corp_code: Optional[str] = None
    ) -> list[dict]:
        """
        대량보유 공시 조회 (5% 이상 지분 보유/변동)

        Args:
            start_date: 시작일 (YYYYMMDD), 기본값 7일 전
            end_date: 종료일 (YYYYMMDD), 기본값 오늘
            corp_code: 특정 기업 코드 (선택)

        Returns:
            대량보유 공시 리스트
        """
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")

        params = {
            "bgn_de": start_date,
            "end_de": end_date,
            "pblntf_ty": "D",  # D: 지분공시
            "page_count": "100",
        }
        if corp_code:
            params["corp_code"] = corp_code

        result = self._request("list.json", params)

        if result.get("status") != "000":
            if result.get("status") == "013":  # 조회된 데이터가 없음
                return []
            raise Exception(f"DART API 오류: {result.get('message')}")

        # 대량보유 관련 공시만 필터링
        reports = result.get("list", [])
        major_reports = [
            r for r in reports
            if "대량보유" in r.get("report_nm", "") or "주식등의대량보유" in r.get("report_nm", "")
        ]

        return self._parse_major_shareholder_reports(major_reports)

    def _parse_major_shareholder_reports(self, reports: list) -> list[dict]:
        """대량보유 공시 파싱"""
        parsed = []
        for r in reports:
            parsed.append({
                "type": "major_shareholder",
                "corp_name": r.get("corp_name"),
                "corp_code": r.get("corp_code"),
                "stock_code": r.get("stock_code"),
                "report_name": r.get("report_nm"),
                "rcept_no": r.get("rcept_no"),
                "rcept_date": r.get("rcept_dt"),
                "flr_nm": r.get("flr_nm"),  # 제출인 (보유자)
            })
        return parsed

    def get_executive_trading_reports(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        corp_code: Optional[str] = None
    ) -> list[dict]:
        """
        임원/주요주주 주식 거래 공시 조회

        Args:
            start_date: 시작일 (YYYYMMDD), 기본값 7일 전
            end_date: 종료일 (YYYYMMDD), 기본값 오늘
            corp_code: 특정 기업 코드 (선택)

        Returns:
            임원/주요주주 거래 공시 리스트
        """
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")

        params = {
            "bgn_de": start_date,
            "end_de": end_date,
            "pblntf_ty": "D",  # D: 지분공시
            "page_count": "100",
        }
        if corp_code:
            params["corp_code"] = corp_code

        result = self._request("list.json", params)

        if result.get("status") != "000":
            if result.get("status") == "013":
                return []
            raise Exception(f"DART API 오류: {result.get('message')}")

        # 임원/주요주주 관련 공시만 필터링
        reports = result.get("list", [])
        exec_reports = [
            r for r in reports
            if "임원" in r.get("report_nm", "") or "주요주주" in r.get("report_nm", "")
        ]

        return self._parse_executive_reports(exec_reports)

    def _parse_executive_reports(self, reports: list) -> list[dict]:
        """임원/주요주주 공시 파싱"""
        parsed = []
        for r in reports:
            parsed.append({
                "type": "executive_trading",
                "corp_name": r.get("corp_name"),
                "corp_code": r.get("corp_code"),
                "stock_code": r.get("stock_code"),
                "report_name": r.get("report_nm"),
                "rcept_no": r.get("rcept_no"),
                "rcept_date": r.get("rcept_dt"),
                "flr_nm": r.get("flr_nm"),
            })
        return parsed

    def get_all_disclosure_reports(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> dict:
        """
        모든 관련 공시 조회 (대량보유 + 임원/주요주주)

        Returns:
            {
                "major_shareholder": [...],
                "executive_trading": [...]
            }
        """
        major = self.get_major_shareholder_reports(start_date, end_date)
        executive = self.get_executive_trading_reports(start_date, end_date)

        return {
            "major_shareholder": major,
            "executive_trading": executive
        }


if __name__ == "__main__":
    # 테스트
    collector = DartCollector()
    reports = collector.get_all_disclosure_reports()

    print("=== 대량보유 공시 ===")
    for r in reports["major_shareholder"][:5]:
        print(f"[{r['rcept_date']}] {r['corp_name']} - {r['flr_nm']}")

    print("\n=== 임원/주요주주 거래 ===")
    for r in reports["executive_trading"][:5]:
        print(f"[{r['rcept_date']}] {r['corp_name']} - {r['report_name']}")
