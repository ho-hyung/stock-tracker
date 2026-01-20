"""
백테스트 모듈
- 과거 추천 종목의 실제 수익률 검증
- 다양한 보유 기간별 성과 분석
- KOSPI 벤치마크 대비 초과수익률 계산
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
class BacktestResult:
    """개별 추천 백테스트 결과"""
    stock_code: str
    stock_name: str
    recommended_date: str
    recommended_price: float
    recommendation_type: str
    returns: dict  # {1: 수익률, 3: 수익률, 5: 수익률, ...}
    benchmark_returns: dict  # KOSPI 동기간 수익률
    excess_returns: dict  # 초과수익률


@dataclass
class BacktestSummary:
    """백테스트 요약 통계"""
    period: str  # 분석 기간
    total_recommendations: int
    holding_periods: list  # [1, 3, 5, 10, 20]

    # 각 보유기간별 통계
    avg_returns: dict  # {1: 평균수익률, 3: ..., }
    win_rates: dict  # {1: 승률, 3: ..., }
    max_returns: dict  # {1: 최대수익률, ...}
    min_returns: dict  # {1: 최소수익률, ...}

    # 벤치마크 대비
    avg_benchmark_returns: dict
    avg_excess_returns: dict

    # 추천 유형별 성과
    by_recommendation_type: dict

    # 최고/최저 성과 종목
    best_performers: dict  # {5: BacktestResult, ...}
    worst_performers: dict


class Backtester:
    """추천 종목 백테스트"""

    HOLDING_PERIODS = [1, 3, 5, 10, 20]  # 보유 기간 (거래일)

    def __init__(self):
        self.recommendations_file = os.path.join(DATA_DIR, "recommendations.json")
        self.backtest_cache_file = os.path.join(DATA_DIR, "backtest_cache.json")
        self.recommendations = self._load_recommendations()
        self.price_cache = {}
        self._load_cache()

    def _load_recommendations(self) -> list:
        """추천 기록 로드"""
        if os.path.exists(self.recommendations_file):
            try:
                with open(self.recommendations_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        return []

    def _load_cache(self):
        """가격 캐시 로드"""
        if os.path.exists(self.backtest_cache_file):
            try:
                with open(self.backtest_cache_file, "r", encoding="utf-8") as f:
                    self.price_cache = json.load(f)
            except:
                self.price_cache = {}

    def _save_cache(self):
        """가격 캐시 저장"""
        with open(self.backtest_cache_file, "w", encoding="utf-8") as f:
            json.dump(self.price_cache, f, ensure_ascii=False, indent=2)

    def _get_price_series(self, stock_code: str, start_date: str, end_date: str) -> dict:
        """
        주가 시계열 데이터 조회 (캐시 활용)

        Returns:
            {날짜: 종가} 딕셔너리
        """
        cache_key = f"{stock_code}_{start_date}_{end_date}"

        if cache_key in self.price_cache:
            return self.price_cache[cache_key]

        try:
            df = fdr.DataReader(stock_code, start_date, end_date)
            if df.empty:
                return {}

            prices = {}
            for idx, row in df.iterrows():
                date_str = idx.strftime("%Y-%m-%d")
                prices[date_str] = float(row['Close'])

            # 캐시 저장
            self.price_cache[cache_key] = prices
            return prices

        except Exception as e:
            print(f"    [WARNING] {stock_code} 가격 조회 실패: {e}")
            return {}

    def _get_kospi_returns(self, start_date: str, days: int) -> Optional[float]:
        """KOSPI 수익률 계산"""
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = start + timedelta(days=days + 10)  # 여유 있게 조회

            df = fdr.DataReader("KS11", start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
            if len(df) < 2:
                return None

            start_price = df['Close'].iloc[0]

            # days 거래일 후 가격 (거래일 기준)
            if len(df) > days:
                end_price = df['Close'].iloc[days]
            else:
                end_price = df['Close'].iloc[-1]

            return ((end_price - start_price) / start_price) * 100

        except Exception as e:
            return None

    def _calculate_returns(self, stock_code: str, recommended_date: str,
                          recommended_price: float) -> dict:
        """
        추천일 대비 N일 후 수익률 계산

        Returns:
            {1: 수익률, 3: 수익률, 5: 수익률, 10: 수익률, 20: 수익률}
        """
        returns = {}

        try:
            start = datetime.strptime(recommended_date, "%Y-%m-%d")
            end = start + timedelta(days=35)  # 20거래일 + 여유

            prices = self._get_price_series(
                stock_code,
                start.strftime("%Y-%m-%d"),
                end.strftime("%Y-%m-%d")
            )

            if not prices:
                return {p: None for p in self.HOLDING_PERIODS}

            # 날짜순 정렬
            sorted_dates = sorted(prices.keys())

            for period in self.HOLDING_PERIODS:
                if len(sorted_dates) > period:
                    end_price = prices[sorted_dates[period]]
                    returns[period] = round(
                        ((end_price - recommended_price) / recommended_price) * 100,
                        2
                    )
                else:
                    returns[period] = None

        except Exception as e:
            returns = {p: None for p in self.HOLDING_PERIODS}

        return returns

    def backtest_single(self, recommendation: dict) -> Optional[BacktestResult]:
        """단일 추천 백테스트"""
        stock_code = recommendation.get("stock_code")
        stock_name = recommendation.get("stock_name")
        recommended_date = recommendation.get("recommended_date")
        recommended_price = recommendation.get("recommended_price")
        recommendation_type = recommendation.get("recommendation_type", "unknown")

        if not all([stock_code, recommended_date, recommended_price]):
            return None

        # 수익률 계산
        returns = self._calculate_returns(stock_code, recommended_date, recommended_price)

        # 벤치마크 수익률
        benchmark_returns = {}
        for period in self.HOLDING_PERIODS:
            benchmark_returns[period] = self._get_kospi_returns(recommended_date, period)

        # 초과수익률
        excess_returns = {}
        for period in self.HOLDING_PERIODS:
            if returns.get(period) is not None and benchmark_returns.get(period) is not None:
                excess_returns[period] = round(returns[period] - benchmark_returns[period], 2)
            else:
                excess_returns[period] = None

        return BacktestResult(
            stock_code=stock_code,
            stock_name=stock_name,
            recommended_date=recommended_date,
            recommended_price=recommended_price,
            recommendation_type=recommendation_type,
            returns=returns,
            benchmark_returns=benchmark_returns,
            excess_returns=excess_returns
        )

    def run_backtest(self, days: int = 90) -> BacktestSummary:
        """
        전체 백테스트 실행

        Args:
            days: 최근 N일간의 추천 분석

        Returns:
            BacktestSummary 객체
        """
        print(f"\n{'='*50}")
        print(f"백테스트 시작 (최근 {days}일)")
        print(f"{'='*50}")

        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")

        # 20거래일 전까지만 분석 (수익률 계산을 위해)
        analysis_cutoff = (datetime.now() - timedelta(days=25)).strftime("%Y-%m-%d")

        # 대상 추천 필터링
        target_recs = [
            r for r in self.recommendations
            if cutoff_date <= r.get("recommended_date", "") <= analysis_cutoff
        ]

        if not target_recs:
            print("  분석 대상 추천 기록이 없습니다.")
            return self._empty_summary(cutoff_date, today)

        print(f"  분석 대상: {len(target_recs)}건")

        # 백테스트 실행
        results = []
        for i, rec in enumerate(target_recs, 1):
            print(f"  [{i}/{len(target_recs)}] {rec.get('stock_name', 'Unknown')} 분석 중...")
            result = self.backtest_single(rec)
            if result:
                results.append(result)

        # 캐시 저장
        self._save_cache()

        if not results:
            return self._empty_summary(cutoff_date, today)

        # 통계 계산
        return self._calculate_summary(results, cutoff_date, today)

    def _empty_summary(self, start_date: str, end_date: str) -> BacktestSummary:
        """빈 요약 생성"""
        empty_dict = {p: 0 for p in self.HOLDING_PERIODS}
        return BacktestSummary(
            period=f"{start_date} ~ {end_date}",
            total_recommendations=0,
            holding_periods=self.HOLDING_PERIODS,
            avg_returns=empty_dict,
            win_rates=empty_dict,
            max_returns=empty_dict,
            min_returns=empty_dict,
            avg_benchmark_returns=empty_dict,
            avg_excess_returns=empty_dict,
            by_recommendation_type={},
            best_performers={},
            worst_performers={}
        )

    def _calculate_summary(self, results: list[BacktestResult],
                          start_date: str, end_date: str) -> BacktestSummary:
        """통계 요약 계산"""

        # 각 보유기간별 통계
        avg_returns = {}
        win_rates = {}
        max_returns = {}
        min_returns = {}
        avg_benchmark_returns = {}
        avg_excess_returns = {}
        best_performers = {}
        worst_performers = {}

        for period in self.HOLDING_PERIODS:
            # 유효한 수익률만 필터링
            valid_returns = [
                r.returns[period] for r in results
                if r.returns.get(period) is not None
            ]
            valid_benchmark = [
                r.benchmark_returns[period] for r in results
                if r.benchmark_returns.get(period) is not None
            ]
            valid_excess = [
                r.excess_returns[period] for r in results
                if r.excess_returns.get(period) is not None
            ]

            if valid_returns:
                avg_returns[period] = round(sum(valid_returns) / len(valid_returns), 2)
                win_rates[period] = round(
                    (sum(1 for r in valid_returns if r > 0) / len(valid_returns)) * 100,
                    1
                )
                max_returns[period] = max(valid_returns)
                min_returns[period] = min(valid_returns)

                # 최고/최저 성과 종목
                sorted_by_return = sorted(
                    [r for r in results if r.returns.get(period) is not None],
                    key=lambda x: x.returns[period],
                    reverse=True
                )
                if sorted_by_return:
                    best_performers[period] = sorted_by_return[0]
                    worst_performers[period] = sorted_by_return[-1]
            else:
                avg_returns[period] = 0
                win_rates[period] = 0
                max_returns[period] = 0
                min_returns[period] = 0

            if valid_benchmark:
                avg_benchmark_returns[period] = round(
                    sum(valid_benchmark) / len(valid_benchmark), 2
                )
            else:
                avg_benchmark_returns[period] = 0

            if valid_excess:
                avg_excess_returns[period] = round(
                    sum(valid_excess) / len(valid_excess), 2
                )
            else:
                avg_excess_returns[period] = 0

        # 추천 유형별 성과 (5일 기준)
        by_type = {}
        for rec_type in set(r.recommendation_type for r in results):
            type_results = [r for r in results if r.recommendation_type == rec_type]
            valid_5d = [r.returns[5] for r in type_results if r.returns.get(5) is not None]

            if valid_5d:
                by_type[rec_type] = {
                    "count": len(type_results),
                    "avg_return_5d": round(sum(valid_5d) / len(valid_5d), 2),
                    "win_rate_5d": round(
                        (sum(1 for r in valid_5d if r > 0) / len(valid_5d)) * 100, 1
                    )
                }

        return BacktestSummary(
            period=f"{start_date} ~ {end_date}",
            total_recommendations=len(results),
            holding_periods=self.HOLDING_PERIODS,
            avg_returns=avg_returns,
            win_rates=win_rates,
            max_returns=max_returns,
            min_returns=min_returns,
            avg_benchmark_returns=avg_benchmark_returns,
            avg_excess_returns=avg_excess_returns,
            by_recommendation_type=by_type,
            best_performers=best_performers,
            worst_performers=worst_performers
        )

    def get_report_text(self, summary: BacktestSummary) -> str:
        """텍스트 리포트 생성"""
        lines = [
            "=" * 50,
            "📊 백테스트 결과 리포트",
            "=" * 50,
            f"분석 기간: {summary.period}",
            f"총 추천 수: {summary.total_recommendations}건",
            "",
            "[ 보유기간별 성과 ]",
        ]

        for period in summary.holding_periods:
            lines.append(
                f"  {period:2d}일: 평균 {summary.avg_returns[period]:+.2f}% | "
                f"승률 {summary.win_rates[period]:.1f}% | "
                f"KOSPI {summary.avg_benchmark_returns[period]:+.2f}% | "
                f"초과수익 {summary.avg_excess_returns[period]:+.2f}%"
            )

        lines.append("")
        lines.append("[ 추천 유형별 성과 (5일 기준) ]")
        for rec_type, stats in summary.by_recommendation_type.items():
            lines.append(
                f"  {rec_type}: {stats['count']}건 | "
                f"평균 {stats['avg_return_5d']:+.2f}% | "
                f"승률 {stats['win_rate_5d']:.1f}%"
            )

        if summary.best_performers.get(5):
            best = summary.best_performers[5]
            lines.append("")
            lines.append(f"🏆 최고 성과 (5일): {best.stock_name} +{best.returns[5]:.2f}%")

        if summary.worst_performers.get(5):
            worst = summary.worst_performers[5]
            lines.append(f"📉 최저 성과 (5일): {worst.stock_name} {worst.returns[5]:.2f}%")

        lines.append("=" * 50)

        return "\n".join(lines)


if __name__ == "__main__":
    backtester = Backtester()
    summary = backtester.run_backtest(days=90)
    print(backtester.get_report_text(summary))
