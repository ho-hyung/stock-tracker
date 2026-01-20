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
from src.notifiers.slack_notifier import SlackNotifier


class StockTracker:
    """주식 고수 추적 메인 클래스"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.dart_collector = None
        self.krx_collector = None
        self.analyzer = None
        self.notifier = None

    def _init_components(self):
        """컴포넌트 초기화 (지연 로딩)"""
        if self.krx_collector is None:
            self.krx_collector = KrxCollector()

        if self.analyzer is None:
            self.analyzer = SignalAnalyzer()

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

    def run_once(self, send_summary: bool = False):
        """
        한 번 실행

        Args:
            send_summary: 일일 요약 발송 여부
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

        # 2. 신호 분석
        print("\n[2/4] 신호 분석 중...")
        signals = self.analyzer.analyze_all(
            foreigner_data,
            institution_data,
            major_shareholder_data,
            executive_data
        )
        print(f"  생성된 알림 신호: {len(signals)}건")

        # 3. 알림 발송
        print("\n[3/4] 알림 발송 중...")
        if self.dry_run:
            print("  [DRY RUN] 실제 발송하지 않음")
            for signal in signals:
                print(f"  - [{signal.priority}] {signal.signal_type}: {signal.reason}")
        elif self.notifier:
            sent_count = 0
            for signal in signals:
                success = self._send_signal(signal)
                if success:
                    sent_count += 1
            print(f"  발송 완료: {sent_count}/{len(signals)}건")
        else:
            print("  [SKIP] Slack 알림기 미설정")

        # 4. 일일 요약 (옵션)
        if send_summary:
            print("\n[4/4] 일일 요약 발송 중...")
            summary = self.analyzer.get_daily_summary(
                foreigner_data,
                institution_data,
                major_shareholder_data,
                executive_data
            )
            if self.dry_run:
                print("  [DRY RUN] 요약 데이터:")
                print(f"    외국인 TOP: {[d['stock_name'] for d in summary['foreigner_top'][:3]]}")
                print(f"    기관 TOP: {[d['stock_name'] for d in summary['institution_top'][:3]]}")
            elif self.notifier:
                self.notifier.send_daily_summary(summary)
                print("  일일 요약 발송 완료")
        else:
            print("\n[4/4] 일일 요약 스킵")

        # 오래된 알림 기록 정리
        self.analyzer.clear_old_alerts(days=7)

        print(f"\n[완료] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def _send_signal(self, signal) -> bool:
        """신호에 따른 알림 발송"""
        if signal.signal_type == "foreigner":
            return self.notifier.send_foreigner_alert(signal.data)
        elif signal.signal_type == "institution":
            return self.notifier.send_institution_alert(signal.data)
        elif signal.signal_type == "major_shareholder":
            return self.notifier.send_major_shareholder_alert(signal.data)
        elif signal.signal_type == "executive_trading":
            return self.notifier.send_executive_trading_alert(signal.data)
        return False

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


def main():
    parser = argparse.ArgumentParser(description="주식 고수 추적 알림 시스템")
    parser.add_argument(
        "--mode",
        choices=["once", "scheduler", "summary"],
        default="once",
        help="실행 모드 (once: 1회 실행, scheduler: 스케줄러, summary: 요약만)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="테스트 모드 (Slack 발송 안함)"
    )

    args = parser.parse_args()

    tracker = StockTracker(dry_run=args.dry_run)

    if args.mode == "once":
        tracker.run_once(send_summary=False)
    elif args.mode == "summary":
        tracker.run_once(send_summary=True)
    elif args.mode == "scheduler":
        tracker.run_scheduler()


if __name__ == "__main__":
    main()
