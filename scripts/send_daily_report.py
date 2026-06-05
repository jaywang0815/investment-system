"""
每日自動報告 — ใช้ใน GitHub Actions
ส่งรายงานไป LINE ทุกเช้า 8:00 (ไต้หวัน)
"""
import os
import requests
from datetime import date, datetime
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
LINE_TOKEN   = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_USER_ID = os.environ["LINE_ADMIN_USER_ID"]

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_stats():
    customers = sb.table("customers").select("id", count="exact").execute()
    sns_active = sb.table("structured_notes").select("id", count="exact").eq("status", "active").execute()
    investments = sb.table("investments").select("amount_usd").execute()
    total_usd = sum(i["amount_usd"] for i in (investments.data or []) if i.get("amount_usd"))
    return {
        "total_customers": customers.count or 0,
        "active_sns": sns_active.count or 0,
        "total_investment_usd": total_usd,
    }

def get_active_sns():
    resp = sb.table("structured_notes").select("*").eq("status", "active").order("observation_date").execute()
    return resp.data or []

def get_investments_by_sn(sn_id):
    resp = sb.table("investments").select("amount_usd, customers(name)").eq("sn_id", sn_id).execute()
    return resp.data or []

def get_upcoming_obs(sns, days=14):
    today = date.today()
    upcoming = []
    for sn in sns:
        obs = sn.get("observation_date", "")
        if obs:
            obs_date = date.fromisoformat(str(obs)[:10])
            if 0 <= (obs_date - today).days <= days:
                upcoming.append(sn)
    return sorted(upcoming, key=lambda x: x.get("observation_date", ""))

def build_report(stats, sns, upcoming):
    today = date.today().strftime("%Y/%m/%d")
    now = datetime.now().strftime("%H:%M")
    lines = [
        f"\n📊 每日投資報告",
        f"🗓️ {today}  {now}",
        "─────────────────",
        f"\n🏦 管理總覽",
        f"• 客戶總數: {stats['total_customers']} 人",
        f"• 有效商品: {stats['active_sns']} 筆",
        f"• 總投資金額: USD {stats['total_investment_usd']:,.0f}",
    ]

    # 每個 SN 的客戶清單
    lines.append(f"\n📋 商品與客戶")
    for sn in sns[:10]:
        code = sn.get("product_code", "—")
        tickers = " / ".join([sn.get(f"underlying_{i}") for i in range(1, 6)
                               if isinstance(sn.get(f"underlying_{i}"), str)])
        obs = str(sn.get("observation_date", ""))[:10]
        invs = get_investments_by_sn(sn["id"])
        names = "、".join([i["customers"]["name"] for i in invs if i.get("customers")])
        total = sum(i.get("amount_usd", 0) or 0 for i in invs)
        lines.append(f"\n  📌 {code}")
        lines.append(f"     {tickers}  比價日: {obs}")
        if names:
            lines.append(f"     👤 {names}")
        if total:
            lines.append(f"     💰 USD {total:,.0f}")

    # 近期比價日
    if upcoming:
        lines.append(f"\n📅 近 14 天比價日")
        today_date = date.today()
        for sn in upcoming[:5]:
            obs = str(sn.get("observation_date", ""))[:10]
            code = sn.get("product_code", "—")
            days_left = (date.fromisoformat(obs) - today_date).days
            badge = "🔴" if days_left <= 3 else "🟡" if days_left <= 7 else "🟢"
            lines.append(f"  {badge} {obs} (剩 {days_left} 天) {code}")

    lines.append("\n─────────────────")
    return "\n".join(lines)

def send_line(message):
    resp = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={
            "Authorization": f"Bearer {LINE_TOKEN}",
            "Content-Type": "application/json"
        },
        json={"to": LINE_USER_ID, "messages": [{"type": "text", "text": message}]},
        timeout=10
    )
    return resp.status_code == 200

if __name__ == "__main__":
    stats = get_stats()
    sns = get_active_sns()
    upcoming = get_upcoming_obs(sns)
    report = build_report(stats, sns, upcoming)
    ok = send_line(report)
    print("✅ 發送成功" if ok else "❌ 發送失敗")
