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

    # ========== 통합 알림 메서드 (NEW) ==========

    def send_market_overview(
        self,
        foreigner_data: list,
        institution_data: list,
        major_shareholder_data: list,
        executive_data: list
    ) -> bool:
        """
        시장 개요 통합 알림 (외국인/기관/공시 한눈에)
        """
        today = datetime.now().strftime("%Y-%m-%d %H:%M")

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "📊 시장 수급 현황"}
            },
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"🕐 {today}"}]
            },
            {"type": "divider"},
        ]

        # 외국인 TOP 5 (한 줄로 압축)
        if foreigner_data:
            f_text = "*🌍 외국인 순매수*\n"
            for i, item in enumerate(foreigner_data[:5], 1):
                amt = item["net_buy_amount"] / 100_000_000
                change = item.get("change_rate", "0")
                emoji = "📉" if str(change).startswith("-") else "📈"
                f_text += f"`{i}` *{item['stock_name']}* {amt:,.0f}억 {emoji}{change}%\n"
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f_text}})

        # 기관 TOP 5 (한 줄로 압축)
        if institution_data:
            i_text = "*🏦 기관 순매수*\n"
            for i, item in enumerate(institution_data[:5], 1):
                amt = item["net_buy_amount"] / 100_000_000
                change = item.get("change_rate", "0")
                emoji = "📉" if str(change).startswith("-") else "📈"
                i_text += f"`{i}` *{item['stock_name']}* {amt:,.0f}억 {emoji}{change}%\n"
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": i_text}})

        # 공시 요약 (간단히)
        if major_shareholder_data or executive_data:
            blocks.append({"type": "divider"})
            d_text = "*📋 오늘의 공시*\n"
            if major_shareholder_data:
                d_text += f"• 대량보유(5%↑): *{len(major_shareholder_data)}건*\n"
            if executive_data:
                d_text += f"• 임원거래: *{len(executive_data)}건*"
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": d_text}})

        return self.send_message("시장 수급 현황", blocks)

    def send_unified_recommendations(
        self,
        rule_based: list,
        score_based: list,
        ai_analysis: str = None
    ) -> bool:
        """
        추천 종목 통합 알림 (3가지 추천을 하나로)
        """
        today = datetime.now().strftime("%Y-%m-%d")

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "💡 AI 추천 종목"}
            },
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"📅 {today} | 외국인+기관 수급 기반 분석"}]
            },
            {"type": "divider"},
        ]

        # 규칙 기반 추천 (수급 일치 종목)
        if rule_based:
            r_text = "*🎯 수급 일치 종목* (외국인+기관 동시 매수)\n"
            for rec in rule_based[:3]:
                r_text += f"• *{rec.stock_name}* `{rec.stock_code}` - {rec.score:.0f}점\n"
                r_text += f"  └ {', '.join(rec.reasons[:2])}\n"
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": r_text}})

        # 점수 기반 TOP 3
        if score_based:
            blocks.append({"type": "divider"})
            s_text = "*📊 종합점수 TOP 3* (외국인40+기관40+내부자20)\n"
            for i, rec in enumerate(score_based[:3], 1):
                bar = "█" * int(rec.score / 10) + "░" * (10 - int(rec.score / 10))
                s_text += f"`{i}` *{rec.stock_name}* {bar} *{rec.score:.0f}점*\n"
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": s_text}})

        # AI 분석 (Slack 블록 제한: 3000자)
        if ai_analysis:
            blocks.append({"type": "divider"})
            max_length = 2900  # Slack 블록 텍스트 제한

            if len(ai_analysis) <= max_length:
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*🤖 AI 분석*\n{ai_analysis}"}
                })
            else:
                # 긴 텍스트를 여러 블록으로 분할
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*🤖 AI 분석*"}
                })
                chunks = [ai_analysis[i:i+max_length] for i in range(0, len(ai_analysis), max_length)]
                for chunk in chunks[:3]:  # 최대 3개 블록
                    blocks.append({
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": chunk}
                    })

        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "_⚠️ 투자 판단의 책임은 본인에게 있습니다_"}]
        })

        return self.send_message("AI 추천 종목", blocks)

    def send_analysis_insights(
        self,
        consecutive_data: dict,
        momentum_stocks: list,
        sector_flows: list
    ) -> bool:
        """
        분석 인사이트 통합 알림 (연속매수/모멘텀/섹터 한눈에)
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # 표시할 내용이 있는지 확인
        has_consecutive = (consecutive_data.get("consecutive_foreigner") or
                          consecutive_data.get("consecutive_institution"))
        has_momentum = bool(momentum_stocks)
        has_sector = bool(sector_flows)

        if not (has_consecutive or has_momentum or has_sector):
            return True

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🔍 시장 분석 인사이트"}
            },
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"📅 {today}"}]
            },
            {"type": "divider"},
        ]

        # 모멘텀 종목 (순매수 + 상승)
        if momentum_stocks:
            m_text = "*🚀 모멘텀 종목* (순매수 + 주가상승)\n"
            for item in momentum_stocks[:5]:
                amt = item.net_buy_amount / 100_000_000
                investor = "외" if item.investor_type == "foreigner" else "기"
                m_text += f"• *{item.stock_name}* +{item.price_change_pct:.1f}% | {amt:,.0f}억({investor})\n"
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": m_text}})

        # 섹터 자금 흐름
        if sector_flows:
            blocks.append({"type": "divider"})
            inflow = [s for s in sector_flows if s.flow_direction == "inflow"]
            outflow = [s for s in sector_flows if s.flow_direction == "outflow"]

            sec_text = "*💰 섹터 자금 흐름*\n"
            if inflow:
                sec_text += "유입: "
                sec_text += " | ".join([f"*{s.sector}* +{s.net_buy_amount/100_000_000:,.0f}억" for s in inflow[:3]])
                sec_text += "\n"
            if outflow:
                sec_text += "유출: "
                sec_text += " | ".join([f"{s.sector} {s.net_buy_amount/100_000_000:,.0f}억" for s in outflow[:3]])
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": sec_text}})

        # 연속 매수 종목
        if has_consecutive:
            blocks.append({"type": "divider"})
            c_text = "*🔥 연속 순매수 종목*\n"
            for item in consecutive_data.get("consecutive_foreigner", [])[:3]:
                c_text += f"• *{item.stock_name}* {item.consecutive_days}일 연속 (외국인)\n"
            for item in consecutive_data.get("consecutive_institution", [])[:3]:
                c_text += f"• *{item.stock_name}* {item.consecutive_days}일 연속 (기관)\n"
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": c_text}})

        return self.send_message("시장 분석 인사이트", blocks)

    def send_performance_summary(self, report: dict) -> bool:
        """
        성과 리포트 (간결 버전)
        """
        if report.get("total_recommendations", 0) == 0:
            return True

        avg_return = report.get("avg_return", 0)
        win_rate = report.get("win_rate", 0)
        total = report.get("total_recommendations", 0)

        # 이모지 결정
        if avg_return >= 3:
            emoji, grade = "🚀", "A+"
        elif avg_return >= 1:
            emoji, grade = "📈", "B+"
        elif avg_return >= 0:
            emoji, grade = "➡️", "C"
        else:
            emoji, grade = "📉", "D"

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "📊 추천 성과 리포트 (7일)"}
            },
            {"type": "divider"},
        ]

        # 핵심 지표 한 줄
        summary = f"{emoji} *성과등급: {grade}* | 수익률 *{avg_return:+.1f}%* | 승률 *{win_rate:.0f}%* | {total}종목"
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": summary}})

        # 최고/최저 성과
        best = report.get("best_performer")
        worst = report.get("worst_performer")

        if best or worst:
            blocks.append({"type": "divider"})
            perf_text = ""
            if best:
                perf_text += f"🏆 *최고* {best.stock_name} *+{best.return_pct:.1f}%*"
            if worst and worst.return_pct < 0:
                if perf_text:
                    perf_text += "\n"
                perf_text += f"📉 *최저* {worst.stock_name} *{worst.return_pct:.1f}%*"
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": perf_text}})

        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "_과거 성과가 미래 수익을 보장하지 않습니다_"}]
        })

        return self.send_message("추천 성과 리포트", blocks)

    # ========== 기존 메서드 (하위 호환용) ==========

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

    def send_rule_based_recommendations(self, recommendations: list) -> bool:
        """규칙 기반 추천 발송"""
        if not recommendations:
            return True

        today = datetime.now().strftime("%Y-%m-%d")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"1. 규칙 기반 추천 TOP {len(recommendations)}",
                }
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"📅 {today} | 외국인+기관 수급 분석"}
                ]
            },
            {"type": "divider"},
        ]

        for i, rec in enumerate(recommendations, 1):
            action_emoji = "🟢" if rec.action == "BUY" else "🟡" if rec.action == "HOLD" else "🔴"
            rec_text = f"*{i}. {rec.stock_name}* (`{rec.stock_code}`) {action_emoji} {rec.action}\n"
            rec_text += f"📊 점수: *{rec.score:.0f}점*\n"
            rec_text += f"✅ 이유: {', '.join(rec.reasons)}\n"
            rec_text += f"⚠️ 리스크: {', '.join(rec.risk_factors)}"

            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": rec_text}
            })

        return self.send_message("규칙 기반 추천", blocks)

    def send_score_based_recommendations(self, recommendations: list) -> bool:
        """점수 기반 추천 발송"""
        if not recommendations:
            return True

        today = datetime.now().strftime("%Y-%m-%d")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"2. 점수 기반 추천 TOP {len(recommendations)}",
                }
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"📅 {today} | 외국인(40)+기관(40)+내부자(20) = 100점"}
                ]
            },
            {"type": "divider"},
        ]

        for i, rec in enumerate(recommendations, 1):
            action_emoji = "🟢" if rec.action == "BUY" else "🟡" if rec.action == "HOLD" else "🔴"
            rec_text = f"*{i}. {rec.stock_name}* (`{rec.stock_code}`) {action_emoji} {rec.action}\n"
            rec_text += f"📊 종합점수: *{rec.score:.0f}점*\n"
            rec_text += f"✅ {', '.join(rec.reasons)}"

            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": rec_text}
            })

        return self.send_message("점수 기반 추천", blocks)

    def send_ai_recommendations(self, ai_analysis: str) -> bool:
        """AI 분석 추천 발송"""
        if not ai_analysis:
            return True

        today = datetime.now().strftime("%Y-%m-%d")

        # AI 응답이 너무 길면 분할
        max_length = 2900  # Slack 블록 텍스트 제한

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "3. AI 분석 추천 (Gemini)",
                }
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"📅 {today} | AI 종합 분석"}
                ]
            },
            {"type": "divider"},
        ]

        # 텍스트 분할
        if len(ai_analysis) <= max_length:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": ai_analysis}
            })
        else:
            # 긴 텍스트를 여러 블록으로 분할
            chunks = [ai_analysis[i:i+max_length] for i in range(0, len(ai_analysis), max_length)]
            for chunk in chunks[:5]:  # 최대 5개 블록
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": chunk}
                })

        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "_⚠️ AI 분석은 참고용이며 투자 판단의 책임은 본인에게 있습니다._"}
            ]
        })

        return self.send_message("AI 분석 추천", blocks)

    def send_consecutive_buy_alert(self, consecutive_data: dict) -> bool:
        """연속 매수 종목 알림 발송"""
        foreigner_list = consecutive_data.get("consecutive_foreigner", [])
        institution_list = consecutive_data.get("consecutive_institution", [])

        if not foreigner_list and not institution_list:
            return True

        today = datetime.now().strftime("%Y-%m-%d")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔥 연속 순매수 종목",
                }
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"📅 {today} | N일 연속 순매수 감지"}
                ]
            },
            {"type": "divider"},
        ]

        # 외국인 연속 매수
        if foreigner_list:
            text = "*📈 외국인 연속 매수*\n"
            for item in foreigner_list[:5]:
                amount = item.total_net_buy / 100_000_000
                text += f"• *{item.stock_name}* - {item.consecutive_days}일 연속 ({amount:,.0f}억원)\n"
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": text}
            })

        # 기관 연속 매수
        if institution_list:
            text = "*🏦 기관 연속 매수*\n"
            for item in institution_list[:5]:
                amount = item.total_net_buy / 100_000_000
                text += f"• *{item.stock_name}* - {item.consecutive_days}일 연속 ({amount:,.0f}억원)\n"
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": text}
            })

        return self.send_message("연속 매수 종목", blocks)

    def send_momentum_alert(self, momentum_stocks: list) -> bool:
        """모멘텀 종목 (순매수 + 주가 상승) 알림 발송"""
        if not momentum_stocks:
            return True

        today = datetime.now().strftime("%Y-%m-%d")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚀 모멘텀 종목 (수급+상승)",
                }
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"📅 {today} | 순매수 + 주가 상승 동반"}
                ]
            },
            {"type": "divider"},
        ]

        text = ""
        for i, item in enumerate(momentum_stocks[:10], 1):
            amount = item.net_buy_amount / 100_000_000
            investor = "외국인" if item.investor_type == "foreigner" else "기관"
            text += f"*{i}. {item.stock_name}* - +{item.price_change_pct:.1f}% | {amount:,.0f}억 ({investor})\n"

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": text}
        })

        return self.send_message("모멘텀 종목", blocks)

    def send_sector_flow_alert(self, sector_flows: list) -> bool:
        """섹터별 자금 흐름 알림 발송"""
        if not sector_flows:
            return True

        today = datetime.now().strftime("%Y-%m-%d")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📊 섹터별 자금 흐름",
                }
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"📅 {today} | 업종별 외국인/기관 수급"}
                ]
            },
            {"type": "divider"},
        ]

        # 유입 섹터
        inflow_text = "*💰 자금 유입 섹터*\n"
        outflow_text = "*💸 자금 유출 섹터*\n"

        for sector in sector_flows:
            amount = abs(sector.net_buy_amount) / 100_000_000
            top_stocks = ", ".join(sector.top_stocks[:2]) if sector.top_stocks else "-"

            if sector.flow_direction == "inflow":
                inflow_text += f"• *{sector.sector}*: +{amount:,.0f}억 ({top_stocks})\n"
            else:
                outflow_text += f"• *{sector.sector}*: -{amount:,.0f}억 ({top_stocks})\n"

        if "+" in inflow_text:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": inflow_text}
            })

        if "-" in outflow_text:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": outflow_text}
            })

        return self.send_message("섹터별 자금 흐름", blocks)

    def send_performance_report(self, report: dict) -> bool:
        """추천 성과 리포트 발송"""
        if report.get("total_recommendations", 0) == 0:
            return True

        today = datetime.now().strftime("%Y-%m-%d")
        period = report.get("period_days", 7)

        # 평균 수익률에 따른 이모지
        avg_return = report.get("avg_return", 0)
        if avg_return >= 3:
            emoji = "🚀"
            status = "대박"
        elif avg_return >= 1:
            emoji = "📈"
            status = "양호"
        elif avg_return >= 0:
            emoji = "➡️"
            status = "보합"
        else:
            emoji = "📉"
            status = "부진"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 추천 성과 리포트 ({period}일)",
                }
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"📅 {today} | 지난 {period}일간 추천 종목 성과"}
                ]
            },
            {"type": "divider"},
        ]

        # 요약 통계
        summary_text = f"*{emoji} 전체 성과: {status}*\n\n"
        summary_text += f"• 추천 종목 수: *{report['total_recommendations']}개*\n"
        summary_text += f"• 평균 수익률: *{avg_return:+.2f}%*\n"
        summary_text += f"• 승률 (수익 종목): *{report['win_rate']:.1f}%*"

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": summary_text}
        })

        blocks.append({"type": "divider"})

        # 최고/최저 성과
        best = report.get("best_performer")
        worst = report.get("worst_performer")

        if best:
            best_text = f"*🏆 최고 성과*\n"
            best_text += f"• {best.stock_name} (`{best.stock_code}`)\n"
            best_text += f"• 추천가: {best.recommended_price:,.0f}원 → 현재가: {best.current_price:,.0f}원\n"
            best_text += f"• 수익률: *+{best.return_pct:.2f}%* ({best.days_held}일)"
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": best_text}
            })

        if worst and worst.return_pct < 0:
            worst_text = f"*📉 최저 성과*\n"
            worst_text += f"• {worst.stock_name} (`{worst.stock_code}`)\n"
            worst_text += f"• 추천가: {worst.recommended_price:,.0f}원 → 현재가: {worst.current_price:,.0f}원\n"
            worst_text += f"• 수익률: *{worst.return_pct:.2f}%* ({worst.days_held}일)"
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": worst_text}
            })

        # 전체 결과 (상위 5개만)
        results = report.get("results", [])
        if results:
            blocks.append({"type": "divider"})
            results_text = "*📋 전체 성과*\n"
            for i, r in enumerate(results[:5], 1):
                sign = "+" if r.return_pct >= 0 else ""
                results_text += f"{i}. {r.stock_name}: *{sign}{r.return_pct:.2f}%*\n"

            if len(results) > 5:
                results_text += f"_외 {len(results) - 5}개 종목..._"

            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": results_text}
            })

        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "_⚠️ 과거 성과가 미래 수익을 보장하지 않습니다._"}
            ]
        })

        return self.send_message("추천 성과 리포트", blocks)

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


    def send_gemini_usage_warning(self, usage_info: dict) -> bool:
        """
        Gemini API 사용량 80% 경고 알림

        Args:
            usage_info: {
                "count": 현재 사용량,
                "limit": 일일 한도,
                "usage_pct": 사용률 (%)
            }
        """
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "⚠️ Gemini API 사용량 경고"}
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*일일 무료 한도의 {usage_info['usage_pct']:.0f}%에 도달했습니다*\n\n"
                           f"• 현재 사용량: *{usage_info['count']:,}회*\n"
                           f"• 일일 한도: *{usage_info['limit']:,}회*\n"
                           f"• 남은 횟수: *{usage_info['limit'] - usage_info['count']:,}회*"
                }
            },
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": "_한도 초과 시 AI 분석 기능이 일시 중단됩니다. 내일 자정에 리셋됩니다._"}
                ]
            }
        ]

        return self.send_message("Gemini API 사용량 경고", blocks)


if __name__ == "__main__":
    notifier = SlackNotifier()
    test_result = notifier.send_message("Stock Tracker 테스트 메시지입니다.")
    print(f"테스트 메시지 발송: {'성공' if test_result else '실패'}")
