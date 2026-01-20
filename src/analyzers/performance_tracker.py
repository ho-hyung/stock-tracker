"""
추천 성과 추적 모듈
- 추천 저장 및 수익률 계산
- 성과 리포트 생성
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
class RecommendationRecord:
    """추천 기록"""
    stock_code: str
    stock_name: str
    recommended_date: str
    recommended_price: float
    recommendation_type: str  # "rule_based", "score_based", "ai"
    action: str  # "BUY", "HOLD"
    score: float
    reasons: list


@dataclass
class PerformanceResult:
    """성과 결과"""
    stock_code: str
    stock_name: str
    recommended_date: str
    recommended_price: float
    current_price: float
    return_pct: float  # 수익률 (%)
    days_held: int
    recommendation_type: str
    action: str


class PerformanceTracker:
    """추천 성과 추적"""

    def __init__(self):
        self.recommendations_file = os.path.join(DATA_DIR, "recommendations.json")
        self._ensure_data_dir()
        self.recommendations = self._load_recommendations()

    def _ensure_data_dir(self):
        """데이터 디렉토리 생성"""
        os.makedirs(DATA_DIR, exist_ok=True)

    def _load_recommendations(self) -> list:
        """추천 기록 로드"""
        if os.path.exists(self.recommendations_file):
            try:
                with open(self.recommendations_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_recommendations(self):
        """추천 기록 저장"""
        with open(self.recommendations_file, "w", encoding="utf-8") as f:
            json.dump(self.recommendations, f, ensure_ascii=False, indent=2)

    def _get_current_price(self, stock_code: str) -> Optional[float]:
        """현재 주가 조회"""
        try:
            # 최근 5일 데이터 조회
            end_date = datetime.now()
            start_date = end_date - timedelta(days=10)

            df = fdr.DataReader(stock_code, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            if not df.empty:
                return float(df['Close'].iloc[-1])
        except Exception as e:
            print(f"    [WARNING] {stock_code} 현재가 조회 실패: {e}")
        return None

    def _get_price_on_date(self, stock_code: str, date_str: str) -> Optional[float]:
        """특정 날짜의 주가 조회"""
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            start_date = target_date - timedelta(days=5)
            end_date = target_date + timedelta(days=5)

            df = fdr.DataReader(stock_code, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            if not df.empty:
                # 해당 날짜 또는 가장 가까운 날짜의 종가
                df.index = df.index.strftime("%Y-%m-%d")
                if date_str in df.index:
                    return float(df.loc[date_str, 'Close'])
                else:
                    return float(df['Close'].iloc[0])
        except Exception as e:
            print(f"    [WARNING] {stock_code} {date_str} 가격 조회 실패: {e}")
        return None

    def save_recommendations(self, rule_based: list, score_based: list, ai_recommendations: str = None):
        """
        오늘의 추천 저장

        Args:
            rule_based: 규칙 기반 추천 리스트
            score_based: 점수 기반 추천 리스트
            ai_recommendations: AI 추천 텍스트 (파싱하지 않음)
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # 오늘 이미 저장된 추천이 있는지 확인
        today_records = [r for r in self.recommendations if r.get("recommended_date") == today]
        if today_records:
            print(f"  - 오늘({today}) 추천은 이미 저장됨 ({len(today_records)}건)")
            return

        new_records = []

        # 규칙 기반 추천 저장
        for rec in rule_based:
            price = self._get_current_price(rec.stock_code)
            if price:
                new_records.append({
                    "stock_code": rec.stock_code,
                    "stock_name": rec.stock_name,
                    "recommended_date": today,
                    "recommended_price": price,
                    "recommendation_type": "rule_based",
                    "action": rec.action,
                    "score": rec.score,
                    "reasons": rec.reasons
                })

        # 점수 기반 추천 저장
        for rec in score_based:
            # 중복 체크 (이미 rule_based에서 저장된 종목)
            existing = [r for r in new_records if r["stock_code"] == rec.stock_code]
            if existing:
                continue

            price = self._get_current_price(rec.stock_code)
            if price:
                new_records.append({
                    "stock_code": rec.stock_code,
                    "stock_name": rec.stock_name,
                    "recommended_date": today,
                    "recommended_price": price,
                    "recommendation_type": "score_based",
                    "action": rec.action,
                    "score": rec.score,
                    "reasons": rec.reasons
                })

        self.recommendations.extend(new_records)

        # 오래된 기록 정리 (90일 이상)
        self._cleanup_old_records(days=90)

        self._save_recommendations()
        print(f"  - 추천 기록 저장 완료: {len(new_records)}건")

    def _cleanup_old_records(self, days: int = 90):
        """오래된 기록 정리"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        self.recommendations = [
            r for r in self.recommendations
            if r.get("recommended_date", "") >= cutoff
        ]

    def get_performance_report(self, days: int = 7) -> dict:
        """
        최근 N일간의 추천 성과 리포트

        Args:
            days: 성과 측정 기간 (기본 7일)

        Returns:
            성과 리포트 딕셔너리
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")

        # 해당 기간의 추천 필터링
        target_recommendations = [
            r for r in self.recommendations
            if cutoff_date <= r.get("recommended_date", "") < today
        ]

        if not target_recommendations:
            return {
                "period_days": days,
                "total_recommendations": 0,
                "avg_return": 0,
                "win_rate": 0,
                "best_performer": None,
                "worst_performer": None,
                "results": []
            }

        results = []
        for rec in target_recommendations:
            current_price = self._get_current_price(rec["stock_code"])
            if current_price and rec.get("recommended_price"):
                return_pct = ((current_price - rec["recommended_price"]) / rec["recommended_price"]) * 100
                rec_date = datetime.strptime(rec["recommended_date"], "%Y-%m-%d")
                days_held = (datetime.now() - rec_date).days

                results.append(PerformanceResult(
                    stock_code=rec["stock_code"],
                    stock_name=rec["stock_name"],
                    recommended_date=rec["recommended_date"],
                    recommended_price=rec["recommended_price"],
                    current_price=current_price,
                    return_pct=round(return_pct, 2),
                    days_held=days_held,
                    recommendation_type=rec["recommendation_type"],
                    action=rec["action"]
                ))

        if not results:
            return {
                "period_days": days,
                "total_recommendations": len(target_recommendations),
                "avg_return": 0,
                "win_rate": 0,
                "best_performer": None,
                "worst_performer": None,
                "results": []
            }

        # 통계 계산
        returns = [r.return_pct for r in results]
        avg_return = sum(returns) / len(returns)
        win_count = sum(1 for r in returns if r > 0)
        win_rate = (win_count / len(returns)) * 100

        # 최고/최저 성과
        results_sorted = sorted(results, key=lambda x: x.return_pct, reverse=True)
        best_performer = results_sorted[0] if results_sorted else None
        worst_performer = results_sorted[-1] if results_sorted else None

        return {
            "period_days": days,
            "total_recommendations": len(results),
            "avg_return": round(avg_return, 2),
            "win_rate": round(win_rate, 1),
            "best_performer": best_performer,
            "worst_performer": worst_performer,
            "results": results_sorted
        }

    def get_recommendation_history(self, stock_code: str) -> list:
        """특정 종목의 추천 히스토리"""
        return [
            r for r in self.recommendations
            if r.get("stock_code") == stock_code
        ]

    def get_summary_stats(self) -> dict:
        """전체 추천 통계 요약"""
        if not self.recommendations:
            return {
                "total_recommendations": 0,
                "unique_stocks": 0,
                "date_range": "-",
                "by_type": {}
            }

        dates = [r["recommended_date"] for r in self.recommendations]
        stocks = set(r["stock_code"] for r in self.recommendations)

        by_type = {}
        for rec in self.recommendations:
            rec_type = rec.get("recommendation_type", "unknown")
            if rec_type not in by_type:
                by_type[rec_type] = 0
            by_type[rec_type] += 1

        return {
            "total_recommendations": len(self.recommendations),
            "unique_stocks": len(stocks),
            "date_range": f"{min(dates)} ~ {max(dates)}",
            "by_type": by_type
        }


if __name__ == "__main__":
    # 테스트
    tracker = PerformanceTracker()

    print("=== 추천 통계 ===")
    stats = tracker.get_summary_stats()
    print(f"총 추천: {stats['total_recommendations']}건")
    print(f"고유 종목: {stats['unique_stocks']}개")
    print(f"기간: {stats['date_range']}")

    print("\n=== 7일 성과 리포트 ===")
    report = tracker.get_performance_report(days=7)
    print(f"추천 수: {report['total_recommendations']}건")
    print(f"평균 수익률: {report['avg_return']}%")
    print(f"승률: {report['win_rate']}%")

    if report['best_performer']:
        best = report['best_performer']
        print(f"최고 성과: {best.stock_name} +{best.return_pct}%")
    if report['worst_performer']:
        worst = report['worst_performer']
        print(f"최저 성과: {worst.stock_name} {worst.return_pct}%")
