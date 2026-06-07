"""
比價日提醒 — รันทุกเช้า 09:00 TWN (GitHub Actions)
แจ้งเตือน admin เมื่อมี SN ถึง observation_date วันนี้
"""
import os
import sys
import requests
from datetime import datetime, timezone, timedelta

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")


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


def get_admin_line_ids() -> list:
    rows = sb_get("admins", {"select": "line_user_id"})
    return [r["line_user_id"] for r in rows if r.get("line_user_id")]


def build_msg(sns_today: list, today_str: str) -> str:
    lines = [
        "📅 比價日提醒",
        today_str,
        f"今日共 {len(sns_today)} 檔商品比價",
        "",
    ]
    for sn in sns_today:
        tickers = [
            (sn.get(f"underlying_{i}") or "").lstrip("$")
            for i in range(1, 6)
        ]
        tickers = [t for t in tickers if t.strip()]
        ticker_str = "  /  ".join(tickers) if tickers else "—"

        ko = sn.get("ko_barrier")
        ki = sn.get("ki_barrier")
        ko_ki = ""
        if ko and ki:
            ko_ki = f"KO：{ko*100:.0f}%　KI：{ki*100:.0f}%"
        elif ko:
            ko_ki = f"KO：{ko*100:.0f}%"
        elif ki:
            ko_ki = f"KI：{ki*100:.0f}%"

        # ดึงชื่อลูกค้าที่ลงทุนใน SN นี้
        invs = sb_get("investments", {
            "sn_id": f"eq.{sn['id']}",
            "select": "customers(name)",
        })
        customer_names = list({
            inv["customers"]["name"]
            for inv in invs
            if inv.get("customers") and inv["customers"].get("name")
        })

        lines.append(f"・{sn.get('product_code', '—')}")
        lines.append(f"  {ticker_str}")
        if ko_ki:
            lines.append(f"  {ko_ki}")
        if customer_names:
            lines.append(f"  客戶：{'、'.join(sorted(customer_names))}")
        lines.append("")

    return "\n".join(lines).rstrip()


def main():
    if not all([LINE_CHANNEL_ACCESS_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
        print("ERROR: Missing environment variables")
        sys.exit(1)

    tz_8 = timezone(timedelta(hours=8))
    today = datetime.now(tz_8).date()
    today_str = today.strftime("%Y/%m/%d")
    print(f"Checking observation_date == {today_str}")

    sns_today = sb_get("structured_notes", {
        "observation_date": f"eq.{today}",
        "status": "eq.active",
        "select": "*",
    })

    if not sns_today:
        print("No SNs with observation_date today")
        return

    print(f"Found {len(sns_today)} SNs")

    admin_ids = get_admin_line_ids()
    if not admin_ids:
        print("No admin LINE IDs found")
        return

    msg = build_msg(sns_today, today_str)
    for aid in admin_ids:
        push_line(aid, msg)
        print(f"  Sent to admin {aid[:8]}...")


if __name__ == "__main__":
    main()
