"""
Slack Webhook을 통한 알림 발송
"""

import requests
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import SLACK_WEBHOOK_URL


class SlackNotifier:
    """Slack Webhook을 통한 알림 발송"""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or SLACK_WEBHOOK_URL
        if not self.webhook_url:
            raise ValueError("SLACK_WEBHOOK_URL이 설정되지 않았습니다. .env 파일을 확인하세요.")

    def send_message(self, text: str, blocks: Optional[list] = None) -> bool:
        """
        Slack 메시지 발송

        Args:
            text: 기본 텍스트 (알림 미리보기용)
            blocks: Slack Block Kit 형식의 메시지 (선택)

        Returns:
            성공 여부
        """
        payload = {"text": text}
        if blocks:
            payload["blocks"] = blocks

        response = requests.post(self.webhook_url, json=payload)
        return response.status_code == 200

    def send_foreigner_alert(self, data: dict) -> bool:
        """외국인 매매 알림 발송"""
        amount_billion = data["net_buy_amount"] / 100_000_000
        action = "순매수" if data["net_buy_amount"] > 0 else "순매도"
        emoji = ":chart_with_upwards_trend:" if data["net_buy_amount"] > 0 else ":chart_with_downwards_trend:"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} 외국인 {action} 알림",
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*종목*\n{data['stock_name']} ({data['stock_code']})"},
                    {"type": "mrkdwn", "text": f"*{action} 금액*\n{abs(amount_billion):.1f}억원"},
                    {"type": "mrkdwn", "text": f"*종가*\n{data.get('close_price', '-')}원"},
                    {"type": "mrkdwn", "text": f"*등락률*\n{data.get('change_rate', '-')}%"},
                ]
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"일자: {data['date']}"}
                ]
            },
            {"type": "divider"}
        ]

        return self.send_message(
            f"외국인 {action}: {data['stock_name']} {abs(amount_billion):.1f}억원",
            blocks
        )

    def send_institution_alert(self, data: dict) -> bool:
        """기관 매매 알림 발송"""
        amount_billion = data["net_buy_amount"] / 100_000_000
        action = "순매수" if data["net_buy_amount"] > 0 else "순매도"
        emoji = ":bank:" if data["net_buy_amount"] > 0 else ":office:"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} 기관 {action} 알림",
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*종목*\n{data['stock_name']} ({data['stock_code']})"},
                    {"type": "mrkdwn", "text": f"*{action} 금액*\n{abs(amount_billion):.1f}억원"},
                    {"type": "mrkdwn", "text": f"*종가*\n{data.get('close_price', '-')}원"},
                    {"type": "mrkdwn", "text": f"*등락률*\n{data.get('change_rate', '-')}%"},
                ]
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"일자: {data['date']}"}
                ]
            },
            {"type": "divider"}
        ]

        return self.send_message(
            f"기관 {action}: {data['stock_name']} {abs(amount_billion):.1f}억원",
            blocks
        )

    def send_major_shareholder_alert(self, data: dict) -> bool:
        """대량보유 공시 알림 발송"""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":page_facing_up: 대량보유 공시",
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*종목*\n{data['corp_name']}"},
                    {"type": "mrkdwn", "text": f"*보유자*\n{data.get('flr_nm', '-')}"},
                    {"type": "mrkdwn", "text": f"*공시명*\n{data['report_name']}"},
                    {"type": "mrkdwn", "text": f"*접수일*\n{data['rcept_date']}"},
                ]
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "공시 보기"},
                        "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={data['rcept_no']}"
                    }
                ]
            },
            {"type": "divider"}
        ]

        return self.send_message(
            f"대량보유 공시: {data['corp_name']} - {data.get('flr_nm', '')}",
            blocks
        )

    def send_executive_trading_alert(self, data: dict) -> bool:
        """임원/주요주주 거래 알림 발송"""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":bust_in_silhouette: 임원/주요주주 거래 공시",
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*종목*\n{data['corp_name']}"},
                    {"type": "mrkdwn", "text": f"*공시명*\n{data['report_name']}"},
                    {"type": "mrkdwn", "text": f"*제출인*\n{data.get('flr_nm', '-')}"},
                    {"type": "mrkdwn", "text": f"*접수일*\n{data['rcept_date']}"},
                ]
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "공시 보기"},
                        "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={data['rcept_no']}"
                    }
                ]
            },
            {"type": "divider"}
        ]

        return self.send_message(
            f"임원 거래 공시: {data['corp_name']} - {data['report_name']}",
            blocks
        )

    def send_daily_summary(self, summary: dict) -> bool:
        """일일 요약 알림 발송"""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":newspaper: 오늘의 주식 고수 동향 요약",
                }
            },
        ]

        # 외국인 TOP 5
        if summary.get("foreigner_top"):
            foreigner_text = "*외국인 순매수 TOP 5*\n"
            for i, item in enumerate(summary["foreigner_top"][:5], 1):
                amount = item["net_buy_amount"] / 100_000_000
                foreigner_text += f"{i}. {item['stock_name']}: {amount:.1f}억원\n"
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": foreigner_text}
            })

        # 기관 TOP 5
        if summary.get("institution_top"):
            inst_text = "*기관 순매수 TOP 5*\n"
            for i, item in enumerate(summary["institution_top"][:5], 1):
                amount = item["net_buy_amount"] / 100_000_000
                inst_text += f"{i}. {item['stock_name']}: {amount:.1f}억원\n"
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": inst_text}
            })

        # 공시 요약
        disclosure_count = summary.get("major_shareholder_count", 0) + summary.get("executive_trading_count", 0)
        if disclosure_count > 0:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*오늘의 공시*\n대량보유: {summary.get('major_shareholder_count', 0)}건 | 임원거래: {summary.get('executive_trading_count', 0)}건"
                }
            })

        blocks.append({"type": "divider"})

        return self.send_message("오늘의 주식 고수 동향 요약", blocks)


if __name__ == "__main__":
    # 테스트
    notifier = SlackNotifier()

    # 테스트 메시지
    test_result = notifier.send_message("Stock Tracker 테스트 메시지입니다.")
    print(f"테스트 메시지 발송: {'성공' if test_result else '실패'}")
