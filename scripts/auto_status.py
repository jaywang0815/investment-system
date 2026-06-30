"""自動更新 SN 狀態 (每日 cron) — 多租戶。
  1) 期末到期: status=active 且 到期日(exit_date) 已過 → matured   (純日期, deterministic)
  2) 已出場(KO): status=active 且 [觀察日(比價日)已到] 且 worst-of 現價 ≥ KO 障壁
                 (且每檔都有報價) → exited + LINE 通知

安全原則:
  - 只動 active 的 SN；exited/matured/inactive 不碰 (idempotent, 可重複跑)
  - **KO 必須 觀察日(observation_date) 已到才判斷** — 觀察日前在保證配息期, 不會 autocall;
    價格暫時站上 KO 也不算出場 (避免把「現價>KO 但還沒到比價日」誤判成已出場)
  - KO 判斷需「每一檔標的都有現價」才下結論；任一檔報價缺 → 不自動出場 (避免誤判)
  - 應在美股收盤後跑 (用收盤價判斷, 降低盤中假突破)
  - DRY_RUN=1 → 只印出將要變更, 不寫入 DB
  - LINE 通知只送「機器人所屬租戶」(BOT_DEFAULT_TENANT_ID) 的 SN, 避免跨租戶外洩
"""
import os
import sys
from datetime import date

import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
BOT_TENANT = (os.environ.get("BOT_DEFAULT_TENANT_ID") or "").strip()
DRY_RUN = (os.environ.get("DRY_RUN") or "").strip().lower() not in ("", "0", "false", "no")

_HDR = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}


def sb_get(table: str, params: dict) -> list:
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=_HDR, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def sb_patch(table: str, row_id: str, data: dict) -> None:
    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers={**_HDR, "Content-Type": "application/json", "Prefer": "return=minimal"},
        params={"id": f"eq.{row_id}"}, json=data, timeout=30)
    r.raise_for_status()


def push_line(user_id: str, text: str) -> None:
    requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={"Authorization": f"Bearer {LINE_TOKEN}", "Content-Type": "application/json"},
        json={"to": user_id, "messages": [{"type": "text", "text": text}]}, timeout=30)


def get_quote(ticker: str):
    """yfinance 現價 (lstrip '$' 依專案慣例)。失敗回 None。"""
    try:
        import yfinance as yf
        t = ticker.lstrip("$").strip()
        if not t:
            return None
        fi = yf.Ticker(t).fast_info
        p = fi.get("last_price") or fi.get("lastPrice")
        return float(p) if p else None
    except Exception:
        return None


def _f(v):
    try:
        return float(v) if v is not None and v != "" else None
    except (TypeError, ValueError):
        return None


def _underlyings(sn: dict):
    out = []
    for i in range(1, 6):
        t = (sn.get(f"underlying_{i}") or "").strip()
        init = _f(sn.get(f"initial_price_{i}"))
        if t and init:
            out.append((t.lstrip("$"), init))
    return out


def ko_triggered(sn: dict, quotes: dict):
    """worst-of 現價 ≥ KO 障壁 → True。任一檔缺報價 → None (สรุปไม่ได้)。"""
    ko = _f(sn.get("ko_barrier"))
    us = _underlyings(sn)
    if not ko or not us:
        return None
    worst = None
    for tk, init in us:
        price = quotes.get(tk)
        if price is None:
            return None  # ราคาหาย → ไม่ตัดสิน
        perf = price / init
        worst = perf if worst is None else min(worst, perf)
    return worst is not None and worst >= ko


def _customers_of(sn_id: str):
    try:
        rows = sb_get("investments", {"sn_id": f"eq.{sn_id}", "select": "customers(name)"})
        return [(r.get("customers") or {}).get("name") for r in rows if (r.get("customers") or {}).get("name")]
    except Exception:
        return []


def main():
    if not (SUPABASE_URL and SUPABASE_KEY):
        print("[auto_status] missing SUPABASE creds"); sys.exit(1)

    today = date.today().isoformat()
    sns = sb_get("structured_notes", {
        "status": "eq.active",
        "select": "id,product_code,status,exit_date,observation_date,ko_barrier,tenant_id,"
                  + ",".join(f"underlying_{i},initial_price_{i}" for i in range(1, 6)),
    })
    print(f"[auto_status] {today}: {len(sns)} active SN to check")

    # ราคา: ดึง quote เฉพาะ ticker ที่ยังไม่ถึงวันครบกำหนด (ต้องเช็ค KO)
    need_ko = [s for s in sns if not (s.get("exit_date") and s["exit_date"][:10] <= today)]
    tickers = sorted({tk for s in need_ko for tk, _ in _underlyings(s)})
    quotes = {tk: get_quote(tk) for tk in tickers}
    print(f"[auto_status] quotes: {sum(1 for v in quotes.values() if v)}/{len(tickers)} ok")

    matured, exited = [], []
    for sn in sns:
        ed = (sn.get("exit_date") or "")[:10]
        if ed and ed <= today:
            matured.append(sn)
            if not DRY_RUN:
                sb_patch("structured_notes", sn["id"], {"status": "matured"})
            continue
        # KO: ต้อง "หลัง" 保證配息日(觀察日) + ราคา breach ครบทุกตัว (過後→每日觀察)
        obs = (sn.get("observation_date") or "")[:10]
        if obs and obs < today and ko_triggered(sn, quotes):
            exited.append(sn)
            if not DRY_RUN:
                sb_patch("structured_notes", sn["id"], {"status": "exited"})

    print(f"[auto_status] 期末到期(matured): {len(matured)} · 已出場(KO): {len(exited)}"
          + ("  [DRY RUN — no writes]" if DRY_RUN else ""))
    for s in matured:
        print(f"  matured  {s['product_code']} (到期 {s.get('exit_date')}) t={(s.get('tenant_id') or '')[:8]}")
    for s in exited:
        print(f"  exited   {s['product_code']} (KO) t={(s.get('tenant_id') or '')[:8]}")

    # LINE: เฉพาะ KO 出場 ของ租戶 ที่ผูกบอตไว้ (กันข้อมูลข้ามบ้าน)
    ko_for_line = [s for s in exited if (not BOT_TENANT) or (s.get("tenant_id") == BOT_TENANT)]
    if ko_for_line and LINE_TOKEN and not DRY_RUN:
        lines = ["🟢 KO 觸發 — 已自動標記「已出場」", ""]
        for s in ko_for_line:
            names = _customers_of(s["id"])
            who = ("（" + "、".join(names) + "）") if names else ""
            lines.append(f"• {s['product_code']} {who}")
        lines += ["", "請確認券商通知後辦理贖回。"]
        msg = "\n".join(lines)
        try:
            admins = sb_get("admins", {"select": "line_user_id"})
            for a in admins:
                uid = (a.get("line_user_id") or "").strip()
                if uid:
                    push_line(uid, msg)
            print(f"[auto_status] LINE sent to {len(admins)} admin(s)")
        except Exception as e:
            print(f"[auto_status] LINE failed: {e}")


if __name__ == "__main__":
    main()
