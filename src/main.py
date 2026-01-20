"""
주식 고수 추적 알림 시스템 - 메인 실행 파일
"""

import schedule
import time
import argparse
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.collectors.dart_collector import DartCollector
from src.collectors.krx_collector import KrxCollector
from src.analyzers.signal_analyzer import SignalAnalyzer
from src.analyzers.stock_recommender import StockRecommender
from src.analyzers.data_analyzer import DataAnalyzer
from src.analyzers.performance_tracker import PerformanceTracker
from src.analyzers.backtester import Backtester
from src.analyzers.risk_manager import RiskManager
from src.notifiers.slack_notifier import SlackNotifier


class StockTracker:
    """주식 고수 추적 메인 클래스"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.dart_collector = None
        self.krx_collector = None
        self.analyzer = None
        self.recommender = None
        self.data_analyzer = None
        self.performance_tracker = None
        self.risk_manager = None
        self.notifier = None

    def _init_components(self):
        """컴포넌트 초기화 (지연 로딩)"""
        if self.krx_collector is None:
            self.krx_collector = KrxCollector()

        if self.analyzer is None:
            self.analyzer = SignalAnalyzer()

        if self.recommender is None:
            self.recommender = StockRecommender()

        if self.data_analyzer is None:
            self.data_analyzer = DataAnalyzer()

        if self.performance_tracker is None:
            self.performance_tracker = PerformanceTracker()

        if self.risk_manager is None:
            self.risk_manager = RiskManager()

        # DART와 Slack은 API 키가 필요하므로 별도 처리
        try:
            if self.dart_collector is None:
                self.dart_collector = DartCollector()
        except ValueError as e:
            print(f"[WARNING] DART 수집기 초기화 실패: {e}")

        if not self.dry_run:
            try:
                if self.notifier is None:
                    self.notifier = SlackNotifier()
            except ValueError as e:
                print(f"[WARNING] Slack 알림기 초기화 실패: {e}")

    def run_once(self, send_summary: bool = False, send_recommendations: bool = True):
        """
        한 번 실행

        Args:
            send_summary: 일일 요약 발송 여부
            send_recommendations: 추천 발송 여부
        """
        print(f"\n{'='*50}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 주식 고수 추적 시작")
        print(f"{'='*50}")

        self._init_components()

        # 1. 데이터 수집
        print("\n[1/4] 데이터 수집 중...")

        # KRX 데이터
        print("  - KRX 외국인/기관 매매동향 수집...")
        krx_data = self.krx_collector.get_all_investor_rankings()
        foreigner_data = krx_data.get("foreigner", [])
        institution_data = krx_data.get("institution", [])
        print(f"    외국인 데이터: {len(foreigner_data)}건")
        print(f"    기관 데이터: {len(institution_data)}건")

        # DART 데이터
        major_shareholder_data = []
        executive_data = []
        if self.dart_collector:
            print("  - DART 공시 데이터 수집...")
            dart_data = self.dart_collector.get_all_disclosure_reports()
            major_shareholder_data = dart_data.get("major_shareholder", [])
            executive_data = dart_data.get("executive_trading", [])
            print(f"    대량보유 공시: {len(major_shareholder_data)}건")
            print(f"    임원 거래 공시: {len(executive_data)}건")
        else:
            print("  - DART API 키 미설정으로 공시 데이터 스킵")

        # 2. 시장 수급 현황 (통합 알림)
        print("\n[2/4] 시장 수급 현황 발송 중...")
        if self.dry_run:
            print("  [DRY RUN] 실제 발송하지 않음")
            print(f"  - 외국인 TOP 5: {[d['stock_name'] for d in foreigner_data[:5]]}")
            print(f"  - 기관 TOP 5: {[d['stock_name'] for d in institution_data[:5]]}")
            print(f"  - 공시: 대량보유 {len(major_shareholder_data)}건, 임원거래 {len(executive_data)}건")
        elif self.notifier:
            self.notifier.send_market_overview(
                foreigner_data, institution_data,
                major_shareholder_data, executive_data
            )
            print("  - 시장 수급 현황 발송 완료 (1개 메시지)")
        else:
            print("  [SKIP] Slack 알림기 미설정")

        # 3. AI 추천 종목 (통합 알림)
        if send_recommendations:
            print("\n[3/4] AI 추천 종목 발송 중...")

            # 추천 데이터 생성
            rule_based = self.recommender.get_rule_based_recommendations(
                foreigner_data, institution_data,
                major_shareholder_data, executive_data, top_n=5
            )
            score_based = self.recommender.get_score_based_recommendations(
                foreigner_data, institution_data,
                major_shareholder_data, executive_data, top_n=5
            )
            ai_analysis = self.recommender.get_ai_recommendations(
                foreigner_data, institution_data,
                major_shareholder_data, executive_data, top_n=5
            )

            if self.dry_run:
                print("  [DRY RUN] 추천 데이터:")
                print(f"  - 수급 일치: {[r.stock_name for r in rule_based[:3]]}")
                print(f"  - 종합점수 TOP: {[r.stock_name for r in score_based[:3]]}")
                print(f"  - AI 분석: {'있음' if ai_analysis else 'GEMINI_API_KEY 필요'}")
                # 사용량 상태 출력
                usage = self.recommender.get_usage_status()
                print(f"  - Gemini 사용량: {usage['count']}/{usage['limit']} ({usage['usage_pct']}%)")
            elif self.notifier:
                # 통합 추천 알림 발송
                self.notifier.send_unified_recommendations(rule_based, score_based, ai_analysis)
                print("  - AI 추천 종목 발송 완료 (1개 메시지)")

                # Gemini 사용량 80% 도달 시 경고 발송
                if self.recommender.should_send_usage_warning():
                    usage = self.recommender.last_usage_info
                    self.notifier.send_gemini_usage_warning(usage)
                    print(f"  - ⚠️ Gemini 사용량 경고 발송 ({usage['usage_pct']}% 도달)")

                # 손절/익절 기준 계산 및 발송
                top_recommendations = (rule_based + score_based)[:5]
                if top_recommendations:
                    print("  - 손절/익절 기준 계산 중...")
                    risk_levels = {}
                    for rec in top_recommendations:
                        risk = self.risk_manager.calculate_risk_levels(rec.stock_code, rec.stock_name)
                        if risk:
                            risk_levels[rec.stock_code] = risk

                    if risk_levels:
                        self.notifier.send_trading_signals(top_recommendations, risk_levels)
                        print("  - 매매 시그널 발송 완료 (손절/익절 포함)")

                # 추천 성과 추적을 위해 저장
                self.performance_tracker.save_recommendations(rule_based, score_based)
        else:
            rule_based = []
            score_based = []
            print("\n[3/4] 추천 스킵")

        # 4. 분석 인사이트 (통합 알림)
        print("\n[4/4] 분석 인사이트 발송 중...")
        analysis_results = self.data_analyzer.get_all_analysis(foreigner_data, institution_data)

        if self.dry_run:
            print("  [DRY RUN] 분석 결과:")
            print(f"  - 모멘텀: {len(analysis_results['momentum_stocks'])}건")
            print(f"  - 섹터 흐름: {len(analysis_results['sector_flow'])}건")
            print(f"  - 연속 매수: 외국인 {len(analysis_results['consecutive_foreigner'])}건, 기관 {len(analysis_results['consecutive_institution'])}건")
        elif self.notifier:
            # 통합 분석 인사이트 발송
            self.notifier.send_analysis_insights(
                analysis_results,
                analysis_results['momentum_stocks'],
                analysis_results['sector_flow']
            )
            print("  - 분석 인사이트 발송 완료 (1개 메시지)")

        # 일일 요약 시 성과 리포트 추가 발송 (옵션)
        if send_summary:
            print("\n[+] 성과 리포트 발송 중...")
            performance_report = self.performance_tracker.get_performance_report(days=7)

            if self.dry_run:
                print(f"  [DRY RUN] 성과: 추천 {performance_report['total_recommendations']}건, 수익률 {performance_report['avg_return']}%, 승률 {performance_report['win_rate']}%")
            elif self.notifier:
                if performance_report['total_recommendations'] > 0:
                    self.notifier.send_performance_summary(performance_report)
                    print("  - 성과 리포트 발송 완료")
                else:
                    print("  - 성과 리포트 스킵 (추천 기록 없음)")

        # 오래된 알림 기록 정리
        self.analyzer.clear_old_alerts(days=7)

        print(f"\n[완료] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def _is_weekday(self) -> bool:
        """평일 여부 확인 (월~금)"""
        return datetime.now().weekday() < 5

    def _run_if_weekday(self, send_summary: bool = False):
        """평일에만 실행"""
        if self._is_weekday():
            self.run_once(send_summary=send_summary)
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] 주말이므로 스킵")

    def run_scheduler(self):
        """스케줄러 실행 (평일 장중 10회)"""
        print("주식 고수 추적 스케줄러 시작")
        print("=" * 50)
        print("스케줄 (평일만 실행):")
        print("  09:10 - 장 시작 직후")
        print("  09:40 - 초반 방향성 확인")
        print("  10:30 - 오전 중반 (외국인/기관 본격 매매)")
        print("  11:30 - 오전장 마무리")
        print("  13:00 - 오후장 시작")
        print("  14:00 - 오후장 본격화")
        print("  14:30 - 장 마감 1시간 전")
        print("  15:10 - 장 마감 직전 (포지션 정리)")
        print("  15:40 - 장 마감 직후 (확정 데이터)")
        print("  17:00 - 일일 요약")
        print("=" * 50)
        print("Ctrl+C로 종료\n")

        # 장중 모니터링 (9회) - 평일만
        schedule.every().day.at("09:10").do(self._run_if_weekday, send_summary=False)
        schedule.every().day.at("09:40").do(self._run_if_weekday, send_summary=False)
        schedule.every().day.at("10:30").do(self._run_if_weekday, send_summary=False)
        schedule.every().day.at("11:30").do(self._run_if_weekday, send_summary=False)
        schedule.every().day.at("13:00").do(self._run_if_weekday, send_summary=False)
        schedule.every().day.at("14:00").do(self._run_if_weekday, send_summary=False)
        schedule.every().day.at("14:30").do(self._run_if_weekday, send_summary=False)
        schedule.every().day.at("15:10").do(self._run_if_weekday, send_summary=False)
        schedule.every().day.at("15:40").do(self._run_if_weekday, send_summary=False)

        # 일일 요약 (1회) - 평일만
        schedule.every().day.at("17:00").do(self._run_if_weekday, send_summary=True)

        while True:
            schedule.run_pending()
            time.sleep(60)


def run_backtest(days: int = 90, send_slack: bool = False):
    """백테스트 실행"""
    print(f"\n{'='*50}")
    print("📊 백테스트 모드")
    print(f"{'='*50}")

    backtester = Backtester()
    summary = backtester.run_backtest(days=days)

    # 콘솔 출력
    print(backtester.get_report_text(summary))

    # Slack 발송
    if send_slack and summary.total_recommendations > 0:
        try:
            notifier = SlackNotifier()
            notifier.send_backtest_report(summary)
            print("\n✅ Slack으로 백테스트 리포트 발송 완료")
        except Exception as e:
            print(f"\n❌ Slack 발송 실패: {e}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="주식 고수 추적 알림 시스템")
    parser.add_argument(
        "--mode",
        choices=["once", "scheduler", "summary", "backtest"],
        default="once",
        help="실행 모드 (once: 1회 실행, scheduler: 스케줄러, summary: 요약만, backtest: 백테스트)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="테스트 모드 (Slack 발송 안함)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="백테스트 분석 기간 (기본: 90일)"
    )

    args = parser.parse_args()

    if args.mode == "backtest":
        run_backtest(days=args.days, send_slack=not args.dry_run)
    else:
        tracker = StockTracker(dry_run=args.dry_run)

        if args.mode == "once":
            tracker.run_once(send_summary=False)
        elif args.mode == "summary":
            tracker.run_once(send_summary=True)
        elif args.mode == "scheduler":
            tracker.run_scheduler()


if __name__ == "__main__":
    main()
