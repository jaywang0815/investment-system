"""
LINE 通知服務模組
- LINE Notify: 每日自動推播報告
- LINE Messaging API: Bot 回應功能
"""
import requests
import streamlit as st
from datetime import date, datetime
from typing import Optional


# ============================================================
# LINE Notify - 單向推播
# ============================================================

def send_line_notify(message: str, token: Optional[str] = None) -> bool:
    """ส่งข้อความหา Admin ผ่าน LINE Bot (แทน LINE Notify ที่ปิดแล้ว)"""
    try:
        access_token = st.secrets.get("LINE_CHANNEL_ACCESS_TOKEN")
        user_id = st.secrets.get("LINE_ADMIN_USER_ID")
        if not access_token or not user_id:
            return False
        return push_line_message(user_id, [{"type": "text", "text": message}], access_token)
    except Exception:
        return False


def build_daily_report(stats: dict, sns_with_status: list, upcoming_obs: list) -> str:
    """
    建立每日報告文字 (繁體中文)

    Args:
        stats: 統計資料 (total_customers, active_sns, total_investment_usd)
        sns_with_status: 每個 SN 的現況 list
        upcoming_obs: 即將比價的商品 list
    """
    today = date.today().strftime("%Y/%m/%d")
    now = datetime.now().strftime("%H:%M")

    lines = [
        f"\n📊 每日投資報告",
        f"🗓️ {today}  {now}",
        "─────────────────",
    ]

    # 管理概覽
    lines.append(f"\n🏦 管理總覽")
    lines.append(f"• 客戶總數: {stats.get('total_customers', 0)} 人")
    lines.append(f"• 有效商品: {stats.get('active_sns', 0)} 筆")
    total = stats.get('total_investment_usd', 0)
    lines.append(f"• 總投資金額: USD {total:,.0f}")

    # 警示狀況
    alerts = [s for s in sns_with_status
              if s.get("overall_status") in ("ki_triggered", "ki_risk", "ko_triggered", "ko_risk")]

    if alerts:
        lines.append(f"\n⚠️ 今日警示 ({len(alerts)} 筆)")
        for a in alerts[:5]:  # 最多顯示 5 筆
            sn = a.get("sn", {})
            code = sn.get("product_code", "—")
            tickers = " ".join([
                sn.get(f"underlying_{i}", "")
                for i in range(1, 6)
                if sn.get(f"underlying_{i}")
            ])
            emoji = a.get("status_emoji", "⚠️")
            label = a.get("status_label", "")
            lines.append(f"  {emoji} {code} ({tickers})")
            lines.append(f"     → {label}")
    else:
        lines.append(f"\n✅ 今日無警示")

    # 即將比價
    if upcoming_obs:
        lines.append(f"\n📅 近期比價日")
        for obs in upcoming_obs[:7]:  # 最多 7 筆
            obs_date = str(obs.get("observation_date", "—"))[:10]
            code = obs.get("product_code", "—")
            tickers = " / ".join([
                obs.get(f"underlying_{i}", "")
                for i in range(1, 6)
                if obs.get(f"underlying_{i}")
            ])
            lines.append(f"  📌 {obs_date}")
            lines.append(f"     {code} ({tickers})")

    lines.append("\n─────────────────")
    lines.append("💬 輸入客戶姓名取得個人報表")

    return "\n".join(lines)


def build_alert_message(sn: dict, analysis: dict) -> str:
    """建立單一 SN 警示訊息"""
    code = sn.get("product_code", "—")
    obs_date = str(sn.get("observation_date", "—"))[:10]
    emoji = analysis.get("status_emoji", "⚠️")
    label = analysis.get("status_label", "")

    lines = [
        f"\n{emoji} 投資警示通知",
        f"商品代號: {code}",
        f"比價日期: {obs_date}",
        f"狀態: {label}",
        "─────────────",
    ]

    for d in analysis.get("details", []):
        ticker = d["ticker"]
        current = d.get("current_price")
        initial = d.get("initial_price")
        change = d.get("change_pct")
        ki_s = d.get("ki_status", "—")
        ko_s = d.get("ko_status", "—")

        lines.append(f"\n📈 {ticker}")
        if current:
            lines.append(f"  現價: ${current:,.2f}")
        if initial:
            lines.append(f"  期初: ${initial:,.2f}")
        if change is not None:
            lines.append(f"  漲跌: {change:+.2f}%")
        lines.append(f"  KO狀態: {ko_s}")
        lines.append(f"  KI狀態: {ki_s}")

    return "\n".join(lines)


# ============================================================
# LINE Messaging API - Bot 回應
# ============================================================

def reply_line_message(reply_token: str, messages: list, access_token: Optional[str] = None) -> bool:
    """透過 LINE Messaging API 回覆訊息"""
    if access_token is None:
        try:
            access_token = st.secrets["LINE_CHANNEL_ACCESS_TOKEN"]
        except Exception:
            return False

    try:
        resp = requests.post(
            "https://api.line.me/v2/bot/message/reply",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={"replyToken": reply_token, "messages": messages},
            timeout=10
        )
        return resp.status_code == 200
    except Exception:
        return False


def push_line_message(user_id: str, messages: list, access_token: Optional[str] = None) -> bool:
    """主動推播訊息給 LINE 用戶"""
    if access_token is None:
        try:
            access_token = st.secrets["LINE_CHANNEL_ACCESS_TOKEN"]
        except Exception:
            return False

    try:
        resp = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={"to": user_id, "messages": messages},
            timeout=10
        )
        return resp.status_code == 200
    except Exception:
        return False


def send_pdf_via_line(reply_token: str, pdf_bytes: bytes, filename: str,
                      access_token: Optional[str] = None) -> bool:
    """
    傳送 PDF 給 LINE 用戶
    注意: LINE Bot 不支援直接傳 PDF 附件
    改為傳送文字訊息告知下載方式
    """
    msg = f"📄 報表已產生: {filename}\n\n請至管理後台下載完整 PDF 報表。"
    messages = [{"type": "text", "text": msg}]
    return reply_line_message(reply_token, messages, access_token)
