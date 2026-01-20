"""
Slack Webhook을 통한 알림 발송
"""

import requests
from typing import Optional
from datetime import datetime
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
        """Slack 메시지 발송"""
        payload = {"text": text}
        if blocks:
            payload["blocks"] = blocks

        response = requests.post(self.webhook_url, json=payload)
        return response.status_code == 200

    def send_foreigner_summary(self, data_list: list, top_n: int = 10) -> bool:
        """외국인 순매수 TOP N 요약 발송"""
        if not data_list:
            return True

        today = datetime.now().strftime("%Y-%m-%d")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📈 외국인 순매수 TOP {min(len(data_list), top_n)}",
                }
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"📅 {today}"}
                ]
            },
            {"type": "divider"},
        ]

        # TOP N 종목 리스트
        stock_lines = []
        for i, item in enumerate(data_list[:top_n], 1):
            amount = item["net_buy_amount"] / 100_000_000
            stock_lines.append(f"*{i}.* {item['stock_name']} (`{item['stock_code']}`) - *{amount:,.0f}억원*")

        # 10개씩 나눠서 섹션 추가 (Slack 제한)
        for i in range(0, len(stock_lines), 5):
            chunk = stock_lines[i:i+5]
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(chunk)}
            })

        return self.send_message(f"외국인 순매수 TOP {min(len(data_list), top_n)}", blocks)

    def send_institution_summary(self, data_list: list, top_n: int = 10) -> bool:
        """기관 순매수 TOP N 요약 발송"""
        if not data_list:
            return True

        today = datetime.now().strftime("%Y-%m-%d")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🏦 기관 순매수 TOP {min(len(data_list), top_n)}",
                }
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"📅 {today}"}
                ]
            },
            {"type": "divider"},
        ]

        stock_lines = []
        for i, item in enumerate(data_list[:top_n], 1):
            amount = item["net_buy_amount"] / 100_000_000
            stock_lines.append(f"*{i}.* {item['stock_name']} (`{item['stock_code']}`) - *{amount:,.0f}억원*")

        for i in range(0, len(stock_lines), 5):
            chunk = stock_lines[i:i+5]
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(chunk)}
            })

        return self.send_message(f"기관 순매수 TOP {min(len(data_list), top_n)}", blocks)

    def send_major_shareholder_summary(self, data_list: list, top_n: int = 10) -> bool:
        """대량보유 공시 요약 발송"""
        if not data_list:
            return True

        today = datetime.now().strftime("%Y-%m-%d")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📋 대량보유 공시 ({len(data_list)}건)",
                }
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"📅 {today} | 5% 이상 지분 보유/변동"}
                ]
            },
            {"type": "divider"},
        ]

        # 최근 N건만 표시
        disclosure_lines = []
        for item in data_list[:top_n]:
            corp_name = item['corp_name'][:10] + "..." if len(item['corp_name']) > 10 else item['corp_name']
            flr_nm = item.get('flr_nm', '-')[:15] + "..." if len(item.get('flr_nm', '-')) > 15 else item.get('flr_nm', '-')
            disclosure_lines.append(f"• *{corp_name}* - {flr_nm}")

        for i in range(0, len(disclosure_lines), 5):
            chunk = disclosure_lines[i:i+5]
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(chunk)}
            })

        if len(data_list) > top_n:
            blocks.append({
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"_외 {len(data_list) - top_n}건 더 있음_"}
                ]
            })

        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "DART에서 전체 보기"},
                    "url": "https://dart.fss.or.kr/dsab001/main.do?option=stock"
                }
            ]
        })

        return self.send_message(f"대량보유 공시 {len(data_list)}건", blocks)

    def send_executive_trading_summary(self, data_list: list, top_n: int = 10) -> bool:
        """임원/주요주주 거래 공시 요약 발송"""
        if not data_list:
            return True

        today = datetime.now().strftime("%Y-%m-%d")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"👔 임원/주요주주 거래 ({len(data_list)}건)",
                }
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"📅 {today} | 내부자 주식 거래"}
                ]
            },
            {"type": "divider"},
        ]

        disclosure_lines = []
        for item in data_list[:top_n]:
            corp_name = item['corp_name'][:10] + "..." if len(item['corp_name']) > 10 else item['corp_name']
            disclosure_lines.append(f"• *{corp_name}* - {item.get('flr_nm', '-')[:15]}")

        for i in range(0, len(disclosure_lines), 5):
            chunk = disclosure_lines[i:i+5]
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(chunk)}
            })

        if len(data_list) > top_n:
            blocks.append({
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"_외 {len(data_list) - top_n}건 더 있음_"}
                ]
            })

        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "DART에서 전체 보기"},
                    "url": "https://dart.fss.or.kr/dsab001/main.do?option=stock"
                }
            ]
        })

        return self.send_message(f"임원/주요주주 거래 {len(data_list)}건", blocks)

    def send_daily_summary(self, summary: dict) -> bool:
        """일일 종합 요약 알림 발송"""
        today = datetime.now().strftime("%Y-%m-%d")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📊 일일 종합 요약",
                }
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"📅 {today}"}
                ]
            },
            {"type": "divider"},
        ]

        # 외국인 TOP 5
        if summary.get("foreigner_top"):
            foreigner_text = "*📈 외국인 순매수 TOP 5*\n"
            for i, item in enumerate(summary["foreigner_top"][:5], 1):
                amount = item["net_buy_amount"] / 100_000_000
                foreigner_text += f"{i}. {item['stock_name']}: {amount:,.0f}억\n"
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": foreigner_text}
            })

        # 기관 TOP 5
        if summary.get("institution_top"):
            inst_text = "*🏦 기관 순매수 TOP 5*\n"
            for i, item in enumerate(summary["institution_top"][:5], 1):
                amount = item["net_buy_amount"] / 100_000_000
                inst_text += f"{i}. {item['stock_name']}: {amount:,.0f}억\n"
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": inst_text}
            })

        # 공시 요약
        major_count = summary.get("major_shareholder_count", 0)
        exec_count = summary.get("executive_trading_count", 0)

        if major_count > 0 or exec_count > 0:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📋 오늘의 공시*\n대량보유: {major_count}건 | 임원거래: {exec_count}건"
                }
            })

        return self.send_message("일일 종합 요약", blocks)


if __name__ == "__main__":
    notifier = SlackNotifier()
    test_result = notifier.send_message("Stock Tracker 테스트 메시지입니다.")
    print(f"테스트 메시지 발송: {'성공' if test_result else '실패'}")
