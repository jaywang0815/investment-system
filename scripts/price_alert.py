"""
Price Alert — รันทุก 1 ชั่วโมงช่วงตลาด US เปิด (GitHub Actions)
ถ้าหุ้นในพอร์ตขึ้น/ลงเกิน 5% จากราคาเมื่อวัน → ส่ง LINE แจ้งลูกค้าทุกคนที่มี line_user_id
"""
import os
import sys
import requests
from datetime import date

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
FINNHUB_TOKEN = os.environ.get("FINNHUB_TOKEN", "")

ALERT_THRESHOLD_PCT = 7.0  # แจ้งเตือนเมื่อลดลงเกิน 7%


def sb_get(table: str, params: dict = None) -> list:
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
        params=params or {},
        timeout=15,
    )
    return resp.json() if resp.ok else []


def push_line(user_id: str, text: str) -> None:
    requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={
            "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
        json={"to": user_id, "messages": [{"type": "text", "text": text[:4000]}]},
        timeout=10,
    )


def get_quote(ticker: str):
    """ดึงราคาจาก Finnhub → (price, prev_close, change_pct)"""
    resp = requests.get(
        "https://finnhub.io/api/v1/quote",
        params={"symbol": ticker, "token": FINNHUB_TOKEN},
        timeout=10,
    )
    if not resp.ok:
        return None, None, None
    q = resp.json()
    return q.get("c"), q.get("pc"), q.get("dp")


def _ticker_perf_line(ticker: str, price: float, sn: dict) -> str:
    """Return 'KO: 100%  期初: 91.5%' string for one ticker inside a SN."""
    for i in range(1, 6):
        if (sn.get(f"underlying_{i}") or "").upper() == ticker:
            init = sn.get(f"initial_price_{i}")
            ko = sn.get("ko_barrier")
            ki = sn.get("ki_barrier")
            parts = []
            if init and init > 0:
                parts.append(f"期初: {price/init*100:.1f}%")
            if ko:
                parts.append(f"KO: {ko*100:.0f}%")
            if ki:
                parts.append(f"KI: {ki*100:.0f}%")
            return "  " + "  ".join(parts) if parts else ""
    return ""


def build_batch_alert_msg(alerts: list, recipient_name: str) -> str:
    """
    alerts = [(ticker, price, prev_close, change_pct, sn), ...]
    Builds one combined message for all triggered tickers.
    """
    today = date.today().strftime("%Y/%m/%d")
    lines = [
        f"⚠️ 價格警示 — {recipient_name}",
        f"日期: {today}  共 {len(alerts)} 支觸發",
        "═════════════",
    ]
    for ticker, price, prev_close, change_pct, sn in alerts:
        arrow = "▲" if change_pct > 0 else "▼"
        direction = "上漲" if change_pct > 0 else "下跌"
        lines.append(f"{arrow} {ticker}  ${price:.2f}  {direction} {abs(change_pct):.2f}%")
        lines.append(f"  昨收: ${prev_close:.2f}")
        perf = _ticker_perf_line(ticker, price, sn)
        if perf:
            lines.append(perf)
        lines.append(f"  商品: {sn.get('product_code', '—')}")
        lines.append("─────────────")
    return "\n".join(lines)


def get_admin_line_ids() -> list:
    """ดึง LINE User ID ของ admin ทั้งหมด"""
    rows = sb_get("admins", {"select": "line_user_id"})
    return [r["line_user_id"] for r in rows if r.get("line_user_id")]


def main():
    if not all([LINE_CHANNEL_ACCESS_TOKEN, SUPABASE_URL, SUPABASE_KEY, FINNHUB_TOKEN]):
        print("ERROR: Missing environment variables")
        sys.exit(1)

    admin_ids = get_admin_line_ids()
    print(f"Admin LINE IDs: {len(admin_ids)} คน")

    # ดึง SN ทั้งหมดที่ active
    sns = sb_get("structured_notes", {"status": "eq.active", "select": "*"})
    if not sns:
        print("No active SNs found")
        return

    # รวม ticker ทั้งหมด + SN ที่ใช้
    ticker_sns: dict[str, list] = {}
    for sn in sns:
        for i in range(1, 6):
            ticker = (sn.get(f"underlying_{i}") or "").strip().upper()
            if ticker:
                ticker_sns.setdefault(ticker, []).append(sn)

    print(f"Checking {len(ticker_sns)} tickers: {', '.join(ticker_sns.keys())}")

    # รวบ alerts ทั้งหมดก่อน แล้วค่อยส่งทีเดียว
    admin_alerts: list = []
    # customer_id → (line_id, name, [(ticker, price, prev, chg, sn), ...])
    customer_alerts: dict = {}

    for ticker, related_sns in ticker_sns.items():
        price, prev_close, change_pct = get_quote(ticker)

        if not price or change_pct is None:
            print(f"  {ticker}: no data")
            continue

        print(f"  {ticker}: ${price:.2f} ({change_pct:+.2f}%)")

        if abs(change_pct) < ALERT_THRESHOLD_PCT:
            continue

        print(f"  >>> ALERT: {ticker} {change_pct:+.2f}%")

        # เก็บ alert สำหรับ admin
        if related_sns:
            admin_alerts.append((ticker, price, prev_close, change_pct, related_sns[0]))

        # เก็บ alert สำหรับลูกค้าแต่ละคน
        for sn in related_sns:
            invs = sb_get("investments", {
                "sn_id": f"eq.{sn['id']}",
                "select": "customer_id,customers(id,name,line_user_id)",
            })
            for inv in invs:
                customer = inv.get("customers") or {}
                cid = customer.get("id")
                line_id = (customer.get("line_user_id") or "").strip()
                name = customer.get("name", "—")
                if not line_id or not cid:
                    continue
                if cid not in customer_alerts:
                    customer_alerts[cid] = (line_id, name, [])
                customer_alerts[cid][2].append((ticker, price, prev_close, change_pct, sn))

    # ── ส่งข้อความรวมเดียว ─────────────────────────────────────
    if not admin_alerts:
        print("\nNo alerts triggered (all within 5% threshold)")
        return

    print(f"\nAlerts triggered: {', '.join(f'{t} {c:+.2f}%' for t,_,_,c,_ in admin_alerts)}")

    # ส่งให้ admin ทุกคน — 1 ข้อความรวม
    if admin_ids:
        admin_msg = build_batch_alert_msg(admin_alerts, "管理員")
        for aid in admin_ids:
            push_line(aid, admin_msg)
            print(f"  Sent batch to admin ({aid[:8]}...)")

    # ส่งให้ลูกค้าแต่ละคน — 1 ข้อความรวมต่อคน
    for cid, (line_id, name, alerts) in customer_alerts.items():
        msg = build_batch_alert_msg(alerts, name)
        push_line(line_id, msg)
        print(f"  Sent batch to {name} ({line_id[:8]}...)")


if __name__ == "__main__":
    main()
