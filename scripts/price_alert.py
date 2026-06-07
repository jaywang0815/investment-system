"""
Price Alert — ตรวจ 2 ครั้ง/วัน ช่วงตลาด US เปิด (GitHub Actions)
แจ้งเตือนเมื่อหุ้นลงเกิน 7% หรือขึ้นเกิน 5% จากราคาเมื่อวัน
"""
import os
import sys
import requests
import yfinance as yf
from datetime import datetime, timezone, timedelta

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

ALERT_DOWN_PCT = 7.0
ALERT_UP_PCT   = 5.0


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
    """ดึงราคาจาก yfinance → (price, prev_close, change_pct)"""
    clean = ticker.lstrip("$")
    try:
        info = yf.Ticker(clean).fast_info
        price = info.last_price
        prev_close = info.previous_close
        if not price or not prev_close or prev_close == 0:
            return None, None, None
        change_pct = (price - prev_close) / prev_close * 100
        return round(price, 2), round(prev_close, 2), round(change_pct, 2)
    except Exception:
        return None, None, None


def _ticker_perf(ticker: str, price: float, sn: dict) -> list[str]:
    """Return lines: 期初表現, KO/KI for the given ticker in a SN."""
    clean = ticker.lstrip("$").upper()
    for i in range(1, 6):
        db_ticker = (sn.get(f"underlying_{i}") or "").lstrip("$").upper()
        if db_ticker == clean:
            init = sn.get(f"initial_price_{i}")
            ko   = sn.get("ko_barrier")
            ki   = sn.get("ki_barrier")
            lines = []
            if init and init > 0:
                lines.append(f"期初表現：{price / init * 100:.1f}%")
            if ko and ki:
                lines.append(f"KO：{ko * 100:.0f}%　KI：{ki * 100:.0f}%")
            elif ko:
                lines.append(f"KO：{ko * 100:.0f}%")
            elif ki:
                lines.append(f"KI：{ki * 100:.0f}%")
            return lines
    return []


def build_alert_msg(alerts: list, recipient: str = None) -> str:
    """
    alerts = [(ticker, price, prev_close, change_pct, sn, customer_names), ...]
    recipient = ชื่อลูกค้า (ใส่ใน header เมื่อส่งให้ลูกค้า), None = admin
    """
    tz_8 = timezone(timedelta(hours=8))
    now  = datetime.now(tz_8).strftime("%Y/%m/%d  %H:%M")

    up   = [a for a in alerts if a[3] > 0]
    down = [a for a in alerts if a[3] <= 0]

    header = f"📊 價格警示 — {recipient}" if recipient else "📊 價格警示"
    lines  = [header, now]

    def _block(ticker, price, prev_close, chg, sn, customer_names, arrow, sign):
        block = [
            "",
            f"{arrow} {ticker}　{sign}{abs(chg):.2f}%",
            f"現價：${price:.2f}",
            f"昨收：${prev_close:.2f}",
        ]
        block.extend(_ticker_perf(ticker, price, sn))
        block.append(f"商品：{sn.get('product_code', '—')}")
        if customer_names:
            block.append(f"客戶：{'、'.join(customer_names)}")
        return block

    if up:
        lines += ["", f"📈 上漲警示（{len(up)} 支）"]
        for t, p, pc, c, s, cnames in up:
            lines += _block(t, p, pc, c, s, cnames, "▲", "+")

    if down:
        lines += ["", f"⚠️ 下跌警示（{len(down)} 支）"]
        for t, p, pc, c, s, cnames in down:
            lines += _block(t, p, pc, c, s, cnames, "▼", "-")

    return "\n".join(lines)


def get_admin_line_ids() -> list:
    rows = sb_get("admins", {"select": "line_user_id"})
    return [r["line_user_id"] for r in rows if r.get("line_user_id")]


def main():
    if not all([LINE_CHANNEL_ACCESS_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
        print("ERROR: Missing environment variables")
        sys.exit(1)

    admin_ids = get_admin_line_ids()
    print(f"Admins: {len(admin_ids)}")

    sns = sb_get("structured_notes", {"status": "eq.active", "select": "*"})
    if not sns:
        print("No active SNs")
        return

    ticker_sns: dict[str, list] = {}
    for sn in sns:
        for i in range(1, 6):
            ticker = (sn.get(f"underlying_{i}") or "").strip().upper()
            if ticker:
                ticker_sns.setdefault(ticker, []).append(sn)

    print(f"Checking {len(ticker_sns)} tickers: {', '.join(ticker_sns)}")

    # admin_alerts: (ticker, price, prev_close, change_pct, sn, [customer_names])
    admin_alerts: list = []
    # customer_id → (line_id, name, [(ticker, price, prev_close, change_pct, sn, [])])
    customer_alerts: dict = {}

    for ticker, related_sns in ticker_sns.items():
        price, prev_close, change_pct = get_quote(ticker)

        if price is None or change_pct is None:
            print(f"  {ticker}: no data")
            continue

        print(f"  {ticker}: ${price:.2f} ({change_pct:+.2f}%)")

        if not (change_pct <= -ALERT_DOWN_PCT or change_pct >= ALERT_UP_PCT):
            continue

        print(f"  >>> ALERT: {ticker} {change_pct:+.2f}%")

        ticker_customer_names: list[str] = []

        for sn in related_sns:
            invs = sb_get("investments", {
                "sn_id": f"eq.{sn['id']}",
                "select": "customer_id,customers(id,name,line_user_id)",
            })
            for inv in invs:
                customer = inv.get("customers") or {}
                cid      = customer.get("id")
                line_id  = (customer.get("line_user_id") or "").strip()
                name     = customer.get("name", "—")
                if not cid:
                    continue
                if name not in ticker_customer_names:
                    ticker_customer_names.append(name)
                if line_id:
                    if cid not in customer_alerts:
                        customer_alerts[cid] = (line_id, name, [])
                    customer_alerts[cid][2].append(
                        (ticker, price, prev_close, change_pct, sn, [])
                    )

        if related_sns:
            admin_alerts.append(
                (ticker, price, prev_close, change_pct, related_sns[0], ticker_customer_names)
            )

    if not admin_alerts:
        print(f"No alerts (down>{ALERT_DOWN_PCT}% / up>{ALERT_UP_PCT}%)")
        return

    print(f"\nAlerts: {', '.join(f'{t} {c:+.2f}%' for t, _, _, c, _, _ in admin_alerts)}")

    msg = build_alert_msg(admin_alerts)
    for aid in admin_ids:
        push_line(aid, msg)
        print(f"  Sent to admin {aid[:8]}...")

    for cid, (line_id, name, alerts) in customer_alerts.items():
        push_line(line_id, build_alert_msg(alerts, recipient=name))
        print(f"  Sent to {name} ({line_id[:8]}...)")


if __name__ == "__main__":
    main()
