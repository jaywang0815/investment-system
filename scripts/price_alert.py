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

ALERT_THRESHOLD_PCT = 5.0  # แจ้งเตือนเมื่อเปลี่ยนแปลงเกิน 5%


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


def build_alert_msg(ticker: str, price: float, prev_close: float,
                    change_pct: float, sn: dict, customer_name: str) -> str:
    today = date.today().strftime("%Y/%m/%d")
    direction = "上漲" if change_pct > 0 else "下跌"
    arrow = "▲" if change_pct > 0 else "▼"

    # หา initial price และ KO/KI ของ ticker นี้ใน SN
    perf_lines = []
    for i in range(1, 6):
        if (sn.get(f"underlying_{i}") or "").upper() == ticker:
            init = sn.get(f"initial_price_{i}")
            ko = sn.get("ko_barrier")
            ki = sn.get("ki_barrier")
            if init and init > 0:
                perf = price / init * 100
                ko_str = f"  KO水位: {ko*100:.0f}%" if ko else ""
                ki_str = f"  KI水位: {ki*100:.0f}%" if ki else ""
                perf_lines.append(f"期初比較: {perf:.1f}%")
                if ko_str:
                    perf_lines.append(ko_str)
                if ki_str:
                    perf_lines.append(ki_str)
            break

    lines = [
        f"⚠️ 價格警示 — {customer_name}",
        f"─────────────",
        f"股票: {ticker}",
        f"現價: ${price:.2f}",
        f"{arrow} {direction} {abs(change_pct):.2f}%",
        f"昨收: ${prev_close:.2f}",
    ]
    if perf_lines:
        lines.append("─────────────")
        lines.extend(perf_lines)
    lines += [
        "─────────────",
        f"商品: {sn.get('product_code', '—')}",
        f"日期: {today}",
    ]
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

    alerted = []

    for ticker, related_sns in ticker_sns.items():
        price, prev_close, change_pct = get_quote(ticker)

        if not price or change_pct is None:
            print(f"  {ticker}: no data")
            continue

        print(f"  {ticker}: ${price:.2f} ({change_pct:+.2f}%)")

        if abs(change_pct) < ALERT_THRESHOLD_PCT:
            continue

        print(f"  >>> ALERT: {ticker} {change_pct:+.2f}% — sending notifications")
        alerted.append(f"{ticker} {change_pct:+.2f}%")

        # หาลูกค้าที่ถือ SN นี้และมี line_user_id
        notified_customers: set = set()

        for sn in related_sns:
            invs = sb_get("investments", {
                "sn_id": f"eq.{sn['id']}",
                "select": "customer_id,customers(id,name,line_user_id)",
            })

            for inv in invs:
                customer = inv.get("customers") or {}
                cid = customer.get("id")
                line_id = customer.get("line_user_id", "").strip() if customer.get("line_user_id") else ""
                name = customer.get("name", "—")

                if not line_id or cid in notified_customers:
                    continue

                notified_customers.add(cid)
                msg = build_alert_msg(ticker, price, prev_close, change_pct, sn, name)
                push_line(line_id, msg)
                print(f"    Sent to {name} ({line_id[:8]}...)")

        # ส่งให้ admin ทุกคนด้วย (ใช้ข้อมูลครบ ไม่ระบุชื่อลูกค้า)
        if related_sns and admin_ids:
            admin_msg = build_alert_msg(ticker, price, prev_close, change_pct, related_sns[0], "管理員")
            for aid in admin_ids:
                push_line(aid, admin_msg)
                print(f"    Sent to admin ({aid[:8]}...)")

    if alerted:
        print(f"\nAlerts triggered: {', '.join(alerted)}")
    else:
        print("\nNo alerts triggered (all within 5% threshold)")


if __name__ == "__main__":
    main()
