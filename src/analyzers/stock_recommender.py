"""
주식 매수/매도 추천 시스템
- 규칙 기반 추천
- 점수 기반 랭킹
"""

import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


@dataclass
class Recommendation:
    """추천 정보"""
    stock_code: str
    stock_name: str
    action: str  # "BUY", "SELL", "HOLD"
    score: float  # 0~100
    reasons: list[str]
    risk_factors: list[str]


class StockRecommender:
    """주식 추천 시스템"""

    def __init__(self):
        pass

    def get_rule_based_recommendations(
        self,
        foreigner_data: list,
        institution_data: list,
        major_shareholder_data: list,
        executive_data: list,
        top_n: int = 5
    ) -> list[Recommendation]:
        """
        규칙 기반 추천
        - 외국인 + 기관 동시 순매수
        - 대량보유 지분 증가
        - 임원 직접 매수
        """
        recommendations = []

        # 외국인 순매수 종목 dict
        foreigner_dict = {
            item['stock_code']: item for item in foreigner_data
            if item.get('net_buy_amount', 0) > 0
        }

        # 기관 순매수 종목 dict
        institution_dict = {
            item['stock_code']: item for item in institution_data
            if item.get('net_buy_amount', 0) > 0
        }

        # 규칙 1: 외국인 + 기관 동시 순매수 (수급 일치)
        common_codes = set(foreigner_dict.keys()) & set(institution_dict.keys())

        for code in common_codes:
            f_item = foreigner_dict[code]
            i_item = institution_dict[code]

            f_amount = f_item['net_buy_amount'] / 100_000_000  # 억원
            i_amount = i_item['net_buy_amount'] / 100_000_000
            total_amount = f_amount + i_amount

            reasons = [
                f"외국인 순매수: {f_amount:,.0f}억원",
                f"기관 순매수: {i_amount:,.0f}억원",
                "외국인+기관 동시 매수 (수급 일치)"
            ]

            recommendations.append(Recommendation(
                stock_code=code,
                stock_name=f_item['stock_name'],
                action="BUY",
                score=min(100, total_amount / 10),  # 1000억 = 100점
                reasons=reasons,
                risk_factors=["단기 차익 실현 매물 출회 가능성"]
            ))

        # 규칙 2: 외국인만 대량 순매수 (500억 이상)
        for code, item in foreigner_dict.items():
            if code in common_codes:
                continue
            amount = item['net_buy_amount'] / 100_000_000
            if amount >= 500:
                recommendations.append(Recommendation(
                    stock_code=code,
                    stock_name=item['stock_name'],
                    action="BUY",
                    score=min(100, amount / 10),
                    reasons=[
                        f"외국인 대량 순매수: {amount:,.0f}억원",
                        "외국인 수급 강세"
                    ],
                    risk_factors=["기관 미동참으로 추가 상승 제한 가능"]
                ))

        # 규칙 3: 기관만 대량 순매수 (500억 이상)
        for code, item in institution_dict.items():
            if code in common_codes:
                continue
            amount = item['net_buy_amount'] / 100_000_000
            if amount >= 500:
                recommendations.append(Recommendation(
                    stock_code=code,
                    stock_name=item['stock_name'],
                    action="BUY",
                    score=min(100, amount / 10),
                    reasons=[
                        f"기관 대량 순매수: {amount:,.0f}억원",
                        "기관 수급 강세"
                    ],
                    risk_factors=["외국인 미동참으로 추가 상승 제한 가능"]
                ))

        # 점수순 정렬 후 상위 N개
        recommendations.sort(key=lambda x: x.score, reverse=True)
        return recommendations[:top_n]

    def get_score_based_recommendations(
        self,
        foreigner_data: list,
        institution_data: list,
        major_shareholder_data: list,
        executive_data: list,
        top_n: int = 5
    ) -> list[Recommendation]:
        """
        점수 기반 랭킹
        - 외국인 점수 (40점)
        - 기관 점수 (40점)
        - 내부자 매수 점수 (20점)
        """
        stock_scores = {}

        # 외국인 점수 (최대 40점)
        if foreigner_data:
            max_amount = max(item['net_buy_amount'] for item in foreigner_data)
            for item in foreigner_data:
                code = item['stock_code']
                if code not in stock_scores:
                    stock_scores[code] = {
                        'stock_name': item['stock_name'],
                        'foreigner_score': 0,
                        'institution_score': 0,
                        'insider_score': 0,
                        'reasons': []
                    }

                amount = item['net_buy_amount']
                if amount > 0 and max_amount > 0:
                    score = (amount / max_amount) * 40
                    stock_scores[code]['foreigner_score'] = score
                    stock_scores[code]['reasons'].append(
                        f"외국인: {amount/100_000_000:,.0f}억원"
                    )

        # 기관 점수 (최대 40점)
        if institution_data:
            max_amount = max(item['net_buy_amount'] for item in institution_data)
            for item in institution_data:
                code = item['stock_code']
                if code not in stock_scores:
                    stock_scores[code] = {
                        'stock_name': item['stock_name'],
                        'foreigner_score': 0,
                        'institution_score': 0,
                        'insider_score': 0,
                        'reasons': []
                    }

                amount = item['net_buy_amount']
                if amount > 0 and max_amount > 0:
                    score = (amount / max_amount) * 40
                    stock_scores[code]['institution_score'] = score
                    stock_scores[code]['reasons'].append(
                        f"기관: {amount/100_000_000:,.0f}억원"
                    )

        # 내부자 매수 점수 (최대 20점) - 임원 거래 공시 기반
        insider_corps = set()
        for item in executive_data:
            corp_name = item.get('corp_name', '')
            insider_corps.add(corp_name)

        for code, data in stock_scores.items():
            if data['stock_name'] in insider_corps:
                data['insider_score'] = 20
                data['reasons'].append("임원/주요주주 거래 공시 있음")

        # 총점 계산 및 추천 생성
        recommendations = []
        for code, data in stock_scores.items():
            total_score = (
                data['foreigner_score'] +
                data['institution_score'] +
                data['insider_score']
            )

            if total_score > 20:  # 최소 점수 기준
                risk_factors = []
                if data['foreigner_score'] == 0:
                    risk_factors.append("외국인 매수세 없음")
                if data['institution_score'] == 0:
                    risk_factors.append("기관 매수세 없음")

                recommendations.append(Recommendation(
                    stock_code=code,
                    stock_name=data['stock_name'],
                    action="BUY" if total_score >= 50 else "HOLD",
                    score=total_score,
                    reasons=data['reasons'],
                    risk_factors=risk_factors if risk_factors else ["특이사항 없음"]
                ))

        recommendations.sort(key=lambda x: x.score, reverse=True)
        return recommendations[:top_n]

    def get_all_recommendations(
        self,
        foreigner_data: list,
        institution_data: list,
        major_shareholder_data: list,
        executive_data: list,
        top_n: int = 5
    ) -> dict:
        """모든 추천 방식 결과 반환"""
        return {
            "rule_based": self.get_rule_based_recommendations(
                foreigner_data, institution_data,
                major_shareholder_data, executive_data, top_n
            ),
            "score_based": self.get_score_based_recommendations(
                foreigner_data, institution_data,
                major_shareholder_data, executive_data, top_n
            )
        }


if __name__ == "__main__":
    # 테스트
    recommender = StockRecommender()

    # 테스트 데이터
    test_foreigner = [
        {"stock_code": "005930", "stock_name": "삼성전자", "net_buy_amount": 500_000_000_000},
        {"stock_code": "000660", "stock_name": "SK하이닉스", "net_buy_amount": 300_000_000_000},
    ]
    test_institution = [
        {"stock_code": "005930", "stock_name": "삼성전자", "net_buy_amount": 200_000_000_000},
        {"stock_code": "035420", "stock_name": "NAVER", "net_buy_amount": 150_000_000_000},
    ]

    print("=== 규칙 기반 추천 ===")
    for rec in recommender.get_rule_based_recommendations(test_foreigner, test_institution, [], []):
        print(f"{rec.stock_name}: {rec.action} (점수: {rec.score:.1f})")
        print(f"  이유: {rec.reasons}")
