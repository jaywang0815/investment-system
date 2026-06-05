"""
每日自動報告 — GitHub Actions
ส่งทุกเช้า 8:00 ไต้หวัน
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


def get_stock_price(ticker: str) -> float | None:
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        hist = t.history(period="1d")
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 2)
    except Exception:
        pass
    return None


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


def analyze_sn(sn, prices):
    ko = sn.get("ko_barrier")
    ki = sn.get("ki_barrier")
    worst_pct = None
    details = []

    for i in range(1, 6):
        ticker = sn.get(f"underlying_{i}")
        init_price = sn.get(f"initial_price_{i}")
        if not isinstance(ticker, str):
            continue
        curr = prices.get(ticker)
        if curr and init_price and init_price > 0:
            pct = curr / init_price
            if worst_pct is None or pct < worst_pct:
                worst_pct = pct
            ko_status = ""
            ki_status = ""
            if ko and pct >= ko:
                ko_status = "🟢 達KO"
            elif ko and pct >= ko * 0.95:
                ko_status = "🟡 接近KO"
            if ki and pct <= ki:
                ki_status = "🔴 觸KI"
            elif ki and pct <= ki * 1.05:
                ki_status = "🟠 接近KI"
            details.append({
                "ticker": ticker,
                "curr": curr,
                "init": init_price,
                "pct": (pct - 1) * 100,
                "ko_status": ko_status,
                "ki_status": ki_status,
            })

    if worst_pct is None:
        overall = "❓"
    elif ko and worst_pct >= ko:
        overall = "🟢 KO觸發"
    elif ko and worst_pct >= ko * 0.95:
        overall = "🟡 接近KO"
    elif ki and worst_pct <= ki:
        overall = "🔴 KI觸發"
    elif ki and worst_pct <= ki * 1.05:
        overall = "🟠 接近KI"
    else:
        overall = "✅ 正常"

    return overall, details


def build_report(stats, sns, prices):
    today = date.today().strftime("%Y/%m/%d")
    now = datetime.now().strftime("%H:%M")
    hour = datetime.utcnow().hour
    if hour < 12:
        session = "🌅 早盤報告 (美股收盤價)"
    else:
        session = "🌙 夜盤報告 (美股開盤後)"

    lines = [
        f"\n📊 {session}",
        f"🗓️ {today}  {now} (台灣時間)",
        "─────────────────",
        f"\n🏦 管理總覽",
        f"• 客戶總數: {stats['total_customers']} 人",
        f"• 有效商品: {stats['active_sns']} 筆",
        f"• 總投資金額: USD {stats['total_investment_usd']:,.0f}",
    ]

    today_date = date.today()

    lines.append(f"\n📋 商品狀況")
    for sn in sns:
        code = sn.get("product_code", "—")
        obs = str(sn.get("observation_date", ""))[:10]
        days_left = (date.fromisoformat(obs) - today_date).days if obs else 0
        badge = "🔴" if days_left <= 3 else "🟡" if days_left <= 7 else "🟢"

        overall, details = analyze_sn(sn, prices)

        invs = get_investments_by_sn(sn["id"])
        names = "、".join([i["customers"]["name"] for i in invs if i.get("customers")])
        total = sum(i.get("amount_usd", 0) or 0 for i in invs)

        lines.append(f"\n{overall} {code}")
        lines.append(f"  {badge} 比價日: {obs} (剩{days_left}天)")
        if names:
            lines.append(f"  👤 {names}")
        if total:
            lines.append(f"  💰 USD {total:,.0f}")

        # ราคาหุ้นแต่ละตัว
        for d in details:
            arrow = "▲" if d["pct"] >= 0 else "▼"
            ko_s = f" {d['ko_status']}" if d["ko_status"] else ""
            ki_s = f" {d['ki_status']}" if d["ki_status"] else ""
            lines.append(f"  📈 {d['ticker']}: ${d['curr']:,.2f} ({arrow}{abs(d['pct']):.1f}%){ko_s}{ki_s}")

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
    import yfinance  # noqa — ensure installed
    stats = get_stats()
    sns = get_active_sns()

    # ดึงราคาหุ้นทั้งหมดในครั้งเดียว
    all_tickers = list(set(
        sn.get(f"underlying_{i}")
        for sn in sns
        for i in range(1, 6)
        if isinstance(sn.get(f"underlying_{i}"), str)
    ))
    print(f"กำลังดึงราคา {len(all_tickers)} ตัว: {all_tickers}")
    prices = {t: get_stock_price(t) for t in all_tickers}

    report = build_report(stats, sns, prices)
    print(report)
    ok = send_line(report)
    print("✅ 發送成功" if ok else "❌ 發送失敗")
