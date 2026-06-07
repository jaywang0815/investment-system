"""
LINE Bot Webhook Server - FastAPI
佈署到 Render.com 或本機執行

執行: uvicorn line_bot_server:app --port 8080
"""
import os
import sys
import io
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, Response
import hmac
import hashlib
import base64
import json
import requests
from datetime import date, datetime, timezone, timedelta

TW = timezone(timedelta(hours=8))

# ── 設定 ──────────────────────────────────────────────────────
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
FINNHUB_TOKEN = os.environ.get("FINNHUB_TOKEN", "")
BASE_URL = os.environ.get("BASE_URL", "").rstrip("/")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

app = FastAPI(title="投資管理 LINE Bot")


# ── Supabase 直接 REST 呼叫 (不依賴 streamlit) ────────────────
def sb_get(table: str, params: dict = None) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    resp = requests.get(url, headers=headers, params=params or {}, timeout=10)
    return resp.json() if resp.ok else []


def sb_post(table: str, data: dict) -> dict | None:
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    resp = requests.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=headers, json=data, timeout=15)
    if resp.ok:
        result = resp.json()
        return result[0] if isinstance(result, list) and result else None
    return None


def sb_patch(table: str, filters: dict, data: dict) -> None:
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    params = {k: f"eq.{v}" for k, v in filters.items()}
    requests.patch(f"{SUPABASE_URL}/rest/v1/{table}", headers=headers, params=params, json=data, timeout=15)


def sb_delete(table: str, filters: dict) -> None:
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    params = {k: f"eq.{v}" for k, v in filters.items()}
    requests.delete(f"{SUPABASE_URL}/rest/v1/{table}", headers=headers, params=params, timeout=15)


def get_customers() -> list:
    return sb_get("customers", {"select": "id,name,usd_amount,portal_token"})


def get_sns(status: str = "active") -> list:
    return sb_get("structured_notes", {
        "select": "*",
        "status": f"eq.{status}",
        "order": "observation_date.asc"
    })


def get_customer_investments(customer_id: str) -> list:
    return sb_get("investments", {
        "select": "amount_usd,structured_notes(*)",
        "customer_id": f"eq.{customer_id}"
    })


def get_sn_customer_map() -> dict:
    """Returns {sn_id: [customer_name, ...]}"""
    rows = sb_get("investments", {"select": "sn_id,customers(name)"})
    result: dict = {}
    for r in rows:
        sn_id = r.get("sn_id")
        name = (r.get("customers") or {}).get("name", "")
        if sn_id and name:
            result.setdefault(sn_id, []).append(name)
    return result


def _clean_ticker(t: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFKC", t).lstrip("$").strip().upper()


def get_stock_price(ticker: str) -> Optional[float]:
    try:
        import yfinance as yf
        ticker = _clean_ticker(ticker)
        stock = yf.Ticker(ticker)
        price = stock.fast_info.last_price
        return round(float(price), 2) if price else None
    except Exception:
        return None


# ── LINE Signature 驗證 ────────────────────────────────────────
def verify_signature(body: bytes, signature: str) -> bool:
    hash_value = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        body,
        hashlib.sha256
    ).digest()
    expected = base64.b64encode(hash_value).decode("utf-8")
    return hmac.compare_digest(expected, signature)


# ── 回覆 LINE 訊息 ─────────────────────────────────────────────
def reply(reply_token: str, text: str, chart_url: str = "") -> None:
    messages = [{"type": "text", "text": text[:4000]}]
    if chart_url:
        messages.append({
            "type": "image",
            "originalContentUrl": chart_url,
            "previewImageUrl": chart_url,
        })
    requests.post(
        "https://api.line.me/v2/bot/message/reply",
        headers={
            "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        },
        json={"replyToken": reply_token, "messages": messages},
        timeout=10
    )


# ── 生成股票走勢圖 ────────────────────────────────────────────
def _generate_chart(ticker: str) -> bytes:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import yfinance as yf
    stock = yf.Ticker(ticker)
    hist = stock.history(period="3mo")
    if hist.empty:
        raise ValueError("No data")

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(10, 6),
        gridspec_kw={"height_ratios": [3, 1]},
        facecolor="#131722"
    )

    # ── Price ──
    ax1.set_facecolor("#131722")
    close = hist["Close"]
    color = "#26a69a" if close.iloc[-1] >= close.iloc[0] else "#ef5350"
    ax1.plot(hist.index, close, color=color, linewidth=1.8)
    ax1.fill_between(hist.index, close, close.min(), alpha=0.15, color=color)

    last_price = close.iloc[-1]
    first_price = close.iloc[0]
    chg_pct = (last_price / first_price - 1) * 100
    sign = "+" if chg_pct >= 0 else ""
    ax1.set_title(
        f"{ticker}   ${last_price:,.2f}   {sign}{chg_pct:.2f}%  (3mo)",
        color="white", fontsize=13, pad=8
    )
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    for spine in ax1.spines.values():
        spine.set_color("#2a2e39")
    ax1.tick_params(colors="#8391a3", labelsize=9)
    ax1.yaxis.tick_right()
    ax1.grid(axis="y", color="#2a2e39", linewidth=0.6)
    ax1.set_xlim(hist.index[0], hist.index[-1])

    # ── Volume ──
    ax2.set_facecolor("#131722")
    ax2.bar(hist.index, hist["Volume"], color=color, alpha=0.5, width=0.8)
    ax2.set_ylabel("Vol", color="#8391a3", fontsize=8)
    for spine in ax2.spines.values():
        spine.set_color("#2a2e39")
    ax2.tick_params(colors="#8391a3", labelsize=8)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    ax2.set_xlim(hist.index[0], hist.index[-1])

    plt.tight_layout(pad=1.0)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=110, bbox_inches="tight", facecolor="#131722")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ── 查詢股票現價 ───────────────────────────────────────────────
def _check_stock(ticker: str) -> tuple[str, str]:
    ticker = _clean_ticker(ticker)
    tv_url = f"https://www.tradingview.com/symbols/{ticker}/"

    try:
        import yfinance as yf
        info  = yf.Ticker(ticker).fast_info
        price = info.last_price
        prev  = info.previous_close

        if price and price > 0:
            chg   = price - prev if prev else 0
            chg_p = chg / prev * 100 if prev else 0
            arrow = "▲" if chg >= 0 else "▼"
            sign  = "+" if chg >= 0 else ""
            lines = [
                f"📊 {ticker}",
                f"現價: ${price:,.2f}",
                f"{arrow} {sign}{chg:.2f} ({sign}{chg_p:.2f}%)",
            ]
            if prev and prev > 0:
                lines.append(f"昨收: ${prev:,.2f}")

            # 查詢此標的在哪些 SN 中
            try:
                sns = get_sns("active")
                matched_sns = []
                for sn in sns:
                    for i in range(1, 6):
                        t = sn.get(f"underlying_{i}") or ""
                        if _clean_ticker(t) == ticker:
                            init_p = sn.get(f"initial_price_{i}")
                            matched_sns.append((sn, init_p))
                            break

                if matched_sns:
                    lines.append("─────────────")
                    for sn, init_p in matched_sns[:3]:
                        code = sn.get("product_code", "—")
                        ko   = sn.get("ko_barrier")
                        ki   = sn.get("ki_barrier")
                        lines.append(f"📌 {code}")
                        if init_p and init_p > 0:
                            perf_pct = price / init_p * 100
                            lines.append(f"   期初: ${init_p:,.2f}  [{perf_pct:.1f}%]")
                            if ko:
                                gap_ko = (ko * 100) - perf_pct
                                ko_sign = "+" if gap_ko > 0 else ""
                                lines.append(f"   KO {ko*100:.0f}%  距離 {ko_sign}{gap_ko:.1f}%")
                            if ki:
                                gap_ki = perf_pct - (ki * 100)
                                ki_sign = "+" if gap_ki > 0 else ""
                                lines.append(f"   KI {ki*100:.0f}%  距離 {ki_sign}{gap_ki:.1f}%")
            except Exception:
                pass

            lines += ["─────────────", tv_url]
            text = "\n".join(lines)
        else:
            text = f"📊 {ticker}\n{tv_url}"

    except Exception:
        text = f"📊 {ticker}\n{tv_url}"

    return text, ""


# ── 指令處理 ──────────────────────────────────────────────────
def handle_command(text: str, user_id: str = "") -> tuple[str, str]:
    """Returns (reply_text, chart_url_or_empty)"""
    text = text.strip()
    today = date.today().strftime("%Y/%m/%d")

    # myid — 回傳自己的 LINE User ID
    if text.lower() in ["myid", "my id", "我的id", "id"]:
        return (
            f"🔑 您的 LINE User ID:\n\n"
            f"{user_id}\n\n"
            f"請將此 ID 傳給管理員，即可接收投資通知。"
        ), ""

    # เช็คราคาหุ้น — normalize full-width chars ก่อน regex
    import re
    text_clean = _clean_ticker(text)
    if re.match(r'^[A-Za-z]{1,6}(\.[A-Za-z]{1,3})?$', text_clean):
        return _check_stock(text_clean)

    # 幫助
    if text in ["幫助", "help", "說明", "?", "？"]:
        return (
            "📊 投資管理系統指令說明\n\n"
            "🔍 查詢指令:\n"
            "  [股票代號] → 查詢報價+走勢圖 (例: AAPL)\n"
            "  [客戶姓名] → 查詢個人持倉\n"
            "  例: 游家順\n\n"
            "📋 系統指令:\n"
            "  日報 → 今日投資摘要\n"
            "  警示 → KO/KI 警示列表\n"
            "  客戶 → 所有客戶列表\n"
            "  myid → 查詢自己的 LINE ID\n"
            "  幫助 → 顯示此說明"
        ), ""

    # 日報
    if text in ["日報", "報告", "今日", "today"]:
        sns = get_sns("active")
        customers = get_customers()
        total_usd = sum(c.get("usd_amount", 0) or 0 for c in customers)
        today_date = date.today()

        # ดึงราคาทุก ticker ในครั้งเดียว
        all_tickers = list(set(
            s.get(f"underlying_{i}")
            for s in sns for i in range(1, 6)
            if isinstance(s.get(f"underlying_{i}"), str)
        ))
        prices = {t: get_stock_price(t) for t in all_tickers}

        lines = [
            f"📊 每日投資報告",
            f"🗓️ {today}",
            "─────────────",
            f"👥 客戶: {len(customers)} 人",
            f"📊 有效商品: {len(sns)} 筆",
            f"💰 總額度: USD {total_usd:,.0f}",
            "",
            "📋 商品狀況:",
        ]

        pending_sns = []  # SN ที่ยังไม่มีข้อมูลราคา
        sn_customers = get_sn_customer_map()

        for sn in sorted(sns, key=lambda s: s.get("observation_date") or ""):
            code = sn.get("product_code", "—")
            obs = str(sn.get("observation_date") or "")[:10]
            try:
                days_left = (date.fromisoformat(obs) - today_date).days if obs else 0
                badge = "🔴" if days_left <= 3 else "⚠️" if days_left <= 7 else "📅"
                days_str = f"剩{days_left}天"
            except Exception:
                badge = "📅"
                days_str = ""
                days_left = 999

            # คำนวณ worst performance + KO/KI status
            ko = sn.get("ko_barrier")
            ki = sn.get("ki_barrier")
            worst_pct = None
            detail_lines = []
            for i in range(1, 6):
                ticker = sn.get(f"underlying_{i}")
                init_p = sn.get(f"initial_price_{i}")
                if not ticker or not init_p or init_p <= 0:
                    continue
                curr = prices.get(ticker)
                if curr:
                    pct = curr / init_p
                    if worst_pct is None or pct < worst_pct:
                        worst_pct = pct
                    chg = (pct - 1) * 100
                    arrow = "▲" if chg >= 0 else "▼"
                    ko_s = (" 🟢KO" if ko and pct >= ko else " 🟡近KO" if ko and pct >= ko * 0.95 else "")
                    ki_s = (" 🔴KI" if ki and pct <= ki else " 🟠近KI" if ki and pct <= ki * 1.05 else "")
                    detail_lines.append(f"  {ticker}: ${curr:,.2f} ({arrow}{abs(chg):.1f}%){ko_s}{ki_s}")

            if worst_pct is None:
                sn_id = sn.get("id", "")
                names = sn_customers.get(sn_id, [])
                pending_sns.append((code, obs[5:], badge, days_str, names))
                continue
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

            sn_id = sn.get("id", "")
            names = sn_customers.get(sn_id, [])
            lines.append(f"\n{overall} {code}")
            if names:
                lines.append(f"  👤 {' / '.join(names)}")
            if obs:
                lines.append(f"  {badge} 比價: {obs} ({days_str})")
            lines.extend(detail_lines)

        # section ด้านล่าง: SN ที่ยังไม่มีข้อมูลราคา
        if pending_sns:
            lines.append(f"\n─────────────")
            lines.append(f"📋 待補資料 ({len(pending_sns)}筆):")
            for (code, obs_short, badge, days_str, names) in pending_sns:
                lines.append(f"  {code}  {badge} {obs_short} ({days_str})")
                if names:
                    lines.append(f"    👤 {', '.join(names)}")

        lines += ["", "─────────────", "輸入客戶姓名查詢個人持倉"]
        return "\n".join(lines), ""

    # 警示
    if text in ["警示", "alert", "KO", "KI"]:
        sns = get_sns("active")
        alert_msgs = ["⚠️ KO/KI 警示摘要\n─────────────"]
        found = 0

        for s in sns[:10]:  # 限制最多10筆避免逾時
            tickers = [s.get(f"underlying_{i}") for i in range(1, 6) if s.get(f"underlying_{i}")]
            ko = s.get("ko_barrier")
            ki = s.get("ki_barrier")

            for ticker in tickers:
                price = get_stock_price(ticker)
                init_price = s.get(f"initial_price_{tickers.index(ticker)+1}")

                if price and init_price and init_price > 0:
                    perf = price / init_price
                    if ki and perf <= ki * 1.1:
                        alert_msgs.append(f"🔴 {s['product_code']} | {ticker} {perf*100:.1f}% → 接近KI")
                        found += 1
                    elif ko and perf >= ko * 0.97:
                        alert_msgs.append(f"🟢 {s['product_code']} | {ticker} {perf*100:.1f}% → 接近KO")
                        found += 1

        if found == 0:
            alert_msgs.append("✅ 目前無警示")
        return "\n".join(alert_msgs), ""

    # 客戶列表
    if text in ["客戶", "客户", "列表", "list"]:
        customers = get_customers()
        if not customers:
            return "尚無客戶資料", ""
        lines = [f"👥 客戶列表 ({len(customers)} 人)\n─────────────"]
        for c in customers:
            usd = c.get("usd_amount")
            usd_str = f"USD {usd:,.0f}" if usd else ""
            lines.append(f"• {c['name']} {usd_str}")
        return "\n".join(lines), ""

    # 匯出 Excel
    if text in ["匯出", "excel", "Excel", "匯出Excel", "匯出excel", "導出"]:
        return "⏳ 產生中，完成後會傳連結給你...", ""

    # 美股盤 — ราคาปัจจุบัน + % เปลี่ยน ของทุก underlying ใน SN active
    if text in ["美股盤", "美股盘", "美股", "盤況", "盘况"]:
        sns = get_sns("active")
        # รวบรวม ticker ที่ไม่ซ้ำ พร้อม initial_price
        ticker_init: dict[str, float] = {}
        for sn in sns:
            for i in range(1, 6):
                t = sn.get(f"underlying_{i}")
                if not t:
                    continue
                t = _clean_ticker(t)
                init_p = sn.get(f"initial_price_{i}")
                if t and t not in ticker_init:
                    ticker_init[t] = float(init_p) if init_p else 0.0

        if not ticker_init:
            return "目前無有效商品標的", ""

        lines = [
            f"📊 美股盤況",
            f"🗓️ {today}",
            "─────────────",
        ]

        results = []
        for ticker in sorted(ticker_init.keys()):
            try:
                import yfinance as yf
                info = yf.Ticker(ticker).fast_info
                price = info.last_price
                prev  = info.previous_close
                if price and price > 0:
                    chg_pct = (price / prev - 1) * 100 if prev and prev > 0 else 0
                    results.append((ticker, price, prev, chg_pct, ticker_init[ticker]))
                else:
                    results.append((ticker, None, None, None, ticker_init[ticker]))
            except Exception:
                results.append((ticker, None, None, None, ticker_init[ticker]))

        # เรียงจาก % เปลี่ยนมาก → น้อย (None ไว้ท้าย)
        results.sort(key=lambda x: (x[3] is None, x[3] if x[3] is not None else 0), reverse=True)

        for ticker, price, prev, chg_pct, init_p in results:
            tv_url = f"https://www.tradingview.com/symbols/{ticker}/"
            if price is None:
                lines.append(f"• {ticker}  —\n  {tv_url}")
                continue
            arrow = "▲" if chg_pct >= 0 else "▼"
            sign  = "+" if chg_pct >= 0 else ""
            line  = f"{arrow} {ticker}  ${price:,.2f}  {sign}{chg_pct:.2f}%"
            if init_p and init_p > 0:
                from_init = (price / init_p - 1) * 100
                from_sign = "+" if from_init >= 0 else ""
                line += f"  [{from_sign}{from_init:.1f}%↑期初]" if from_init >= 0 else f"  [{from_sign}{from_init:.1f}%↓期初]"
            lines.append(f"{line}\n  {tv_url}")

        lines.append("─────────────")
        lines.append(f"共 {len(results)} 檔標的")
        return "\n".join(lines), ""

    # 依客戶姓名查詢
    customers = get_customers()
    matched = [c for c in customers if text in c["name"] or c["name"] in text]

    if matched:
        c = matched[0]
        investments = get_customer_investments(c["id"])

        if not investments:
            return f"👤 {c['name']}\n目前無投資持倉記錄", ""

        total = sum(i.get("amount_usd", 0) or 0 for i in investments)
        lines = [
            f"👤 {c['name']} 持倉報告",
            f"🗓️ {today}",
            "─────────────",
            f"持倉筆數: {len(investments)} 筆",
            f"總金額: USD {total:,.0f}",
            ""
        ]

        for inv in investments[:5]:
            sn = inv.get("structured_notes") or {}
            if not sn:
                continue

            code      = sn.get("product_code", "—")
            obs       = str(sn.get("observation_date", ""))[:10]
            exit_date = str(sn.get("exit_date") or "")[:10]
            amount    = inv.get("amount_usd", 0) or 0
            coupon    = sn.get("coupon_pct")
            ko        = sn.get("ko_barrier")
            ki        = sn.get("ki_barrier")
            order_amt = sn.get("total_order_amount")
            temp_set  = sn.get("temp_settlement")
            chu       = sn.get("chu") or ""

            coupon_str = f"  配息 {coupon*100:.1f}%" if coupon else ""
            ko_str     = f"KO {ko*100:.0f}%" if ko else ""
            ki_str     = f"KI {ki*100:.0f}%" if ki else ""
            barrier_str = "  ".join(b for b in [ko_str, ki_str] if b)

            lines.append(f"📌 {code}")
            lines.append(f"   金額: USD {amount:,.0f}{coupon_str}")
            if order_amt:
                lines.append(f"   下單金: USD {order_amt:,.0f}")
            if barrier_str:
                lines.append(f"   障礙: {barrier_str}")
            lines.append(f"   比價日: {obs}")
            if exit_date:
                lines.append(f"   出場日: {exit_date}")
            if temp_set:
                lines.append(f"   暫結: {temp_set:,.0f}")
            if chu:
                lines.append(f"   CHU: {chu}")

            # ── 各標的現況 ──────────────────────────────────────
            ticker_rows = []
            worst_perf = None
            worst_ticker = ""
            for i in range(1, 6):
                ticker = _clean_ticker(sn.get(f"underlying_{i}") or "")
                init   = sn.get(f"initial_price_{i}")
                if not ticker or not init or init <= 0:
                    continue
                price = get_stock_price(ticker)
                if price:
                    perf  = price / init * 100
                    chg   = perf - 100
                    arrow = "▲" if chg >= 0 else "▼"
                    # KO/KI status indicator
                    status = ""
                    if ko and perf / 100 >= ko:
                        status = " 🟢KO"
                    elif ko and perf / 100 >= ko * 0.95:
                        status = " 🟡近KO"
                    elif ki and perf / 100 <= ki:
                        status = " 🔴KI"
                    elif ki and perf / 100 <= ki * 1.05:
                        status = " 🟠近KI"
                    ticker_rows.append(
                        (ticker, price, init, perf, chg, arrow, status)
                    )
                    if worst_perf is None or perf < worst_perf:
                        worst_perf   = perf
                        worst_ticker = ticker
                else:
                    ticker_rows.append((ticker, None, init, None, None, "", ""))

            if ticker_rows:
                lines.append("   ┈┈ 標的現況 ┈┈")
                for (t, price, init, perf, chg, arrow, status) in ticker_rows:
                    worst_mark = " ⭐" if t == worst_ticker else ""
                    if price:
                        sign = "+" if chg >= 0 else ""
                        lines.append(
                            f"   {arrow}{t}{worst_mark}  ${price:,.2f} ({sign}{chg:.1f}%)"
                        )
                        lines.append(
                            f"     期初${init:,.0f}  [{perf:.1f}%]{status}"
                        )
                    else:
                        lines.append(f"   {t} 無法取得報價")

                if worst_perf is not None:
                    # overall status
                    if ko and worst_perf / 100 >= ko:
                        overall = "🟢 KO觸發"
                    elif ko and worst_perf / 100 >= ko * 0.95:
                        overall = "🟡 接近KO"
                    elif ki and worst_perf / 100 <= ki:
                        overall = "🔴 KI觸發"
                    elif ki and worst_perf / 100 <= ki * 1.05:
                        overall = "🟠 接近KI"
                    else:
                        overall = "✅ 正常"
                    lines.append(f"   整體: {overall}  最差 {worst_perf:.1f}% ({worst_ticker})")

            lines.append("")

        if len(investments) > 5:
            lines.append(f"...共 {len(investments)} 筆，請至後台查看完整報表")

        lines.append("─────────────")
        lines.append("完整PDF請至管理後台下載")
        return "\n".join(lines), ""

    # 找不到
    return (
        f"❓ 找不到「{text}」\n\n"
        "可能的指令:\n"
        "• 輸入客戶姓名查詢持倉\n"
        "• 日報 → 每日摘要\n"
        "• 警示 → KO/KI 警示\n"
        "• 幫助 → 指令說明"
    ), ""


# ── API 端點 ──────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "LINE Bot Server Running", "date": str(date.today())}


_AI_SYSTEM = """\
你是投資管理系統的 LINE Bot 助手，個性甜美可愛，說話像在跟心愛的人撒嬌。
一律用繁體中文回覆，稱呼對方為「寶寶」，語氣溫柔、活潑、帶點撒嬌感。
系統管理 Structured Note (SN) 投資產品與客戶資料。

可執行的指令：
- query_customer: 查詢客戶持倉，需要 {"name": "客戶姓名"}
- query_price: 查詢股票即時報價，需要 {"ticker": "股票代號(英文)"}
- daily_report: 每日投資摘要
- alert: KO/KI 警示列表
- customer_list: 所有客戶列表
- ppt: 製作 PPT 圖表報告
- help: 指令說明
- chat: 一般對話（無法執行其他指令時使用）

使用者可能用各種方式表達同一件事，例如：
「幫我看一下王先生的持倉」→ query_customer, name=王先生
「AAPL今天怎樣」→ query_price, ticker=AAPL
「給我今天的報告」→ daily_report
「有沒有快到KI的」→ alert

請分析用戶輸入，只回覆 JSON，不要有其他文字：
{"action": "指令名稱", "params": {}, "message": "補充說明或 chat 時的完整回覆（要有寶寶語氣）"}

若無法判斷意圖，使用 chat 並在 message 用可愛語氣說明可用功能。\
"""


def _ai_handle(text: str, user_id: str) -> str | None:
    """Claude Haiku 解析意圖 → 路由到對應指令，回傳回覆文字"""
    if not ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic
        import json as _json
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system=_AI_SYSTEM,
            messages=[{"role": "user", "content": text}],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        data = _json.loads(raw)
        action = data.get("action", "chat")
        params = data.get("params", {})

        if action == "query_customer":
            result, _ = handle_command(params.get("name", ""), user_id)
            return result
        if action == "query_price":
            result, _ = handle_command(params.get("ticker", ""), user_id)
            return result
        if action == "daily_report":
            result, _ = handle_command("日報", user_id)
            return result
        if action == "alert":
            result, _ = handle_command("警示", user_id)
            return result
        if action == "customer_list":
            result, _ = handle_command("客戶", user_id)
            return result
        if action == "help":
            result, _ = handle_command("幫助", user_id)
            return result
        if action == "ppt":
            result, _ = handle_command("ppt", user_id)
            return result

        return data.get("message") or None

    except Exception as e:
        print(f"[ai_handle error] {e}")
        return None


_excel_cache: dict[str, bytes] = {}  # user_id → raw Excel bytes (short-lived, in-memory)


def _download_line_content(message_id: str) -> bytes | None:
    resp = requests.get(
        f"https://api-data.line.me/v2/bot/message/{message_id}/content",
        headers={"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"},
        timeout=30,
    )
    return resp.content if resp.ok else None


def _process_file_event(reply_token: str, message_id: str, filename: str, user_id: str) -> None:
    """Handle Excel file sent by user — parse, ask confirmation"""
    if not filename.lower().endswith((".xlsx", ".xls")):
        reply(reply_token, "寶寶～ 只支援 Excel 檔案喔（.xlsx / .xls）😊")
        return

    file_bytes = _download_line_content(message_id)
    if not file_bytes:
        reply(reply_token, "寶寶～ 下載檔案失敗了，再傳一次好嗎？😢")
        return

    try:
        from utils.excel_parser import parse_excel_file, get_summary
        parsed = parse_excel_file(BytesIO(file_bytes))
        summary = get_summary(parsed)
    except Exception:
        reply(reply_token, "寶寶～ 讀取檔案失敗了耶 😢\n格式不對嗎？")
        return

    _excel_cache[user_id] = file_bytes
    _session_save(user_id, {"step": "excel_action", "summary": summary, "filename": filename})

    months = summary.get("months", [])
    month_str = "、".join(sorted(months)) if months else "（未偵測到）"

    lines = ["寶寶～ 收到檔案了！✨", "幫你看了一下：", ""]
    if summary["customers"] > 0:
        lines.append(f"・客戶資料：{summary['customers']} 位")
    if summary["total_sns"] > 0:
        lines.append(f"・SN商品：{summary['total_sns']} 筆")
        lines.append(f"・月份：{month_str}")
    lines += ["", "是要新增，還是更新已有的資料呢？", "1️⃣ 新增", "2️⃣ 更新（覆蓋舊資料）", "❌ 取消"]
    reply(reply_token, "\n".join(lines))


def _handle_excel_session(reply_token: str, text: str, user_id: str, session: dict) -> None:
    """Handle confirmation steps for Excel import"""
    step = session.get("step")
    summary = session.get("summary", {})

    if text in ["❌", "取消", "cancel", "Cancel", "不", "不要"]:
        _session_clear(user_id)
        _excel_cache.pop(user_id, None)
        reply(reply_token, "寶寶～ 取消囉，沒關係的～ 😊")
        return

    if step == "excel_action":
        if text in ["1", "1️⃣", "新增"]:
            action, action_label = "new", "新增"
        elif text in ["2", "2️⃣", "更新", "覆蓋", "更新（覆蓋舊資料）"]:
            action, action_label = "update", "更新（覆蓋舊資料）"
        else:
            reply(reply_token, "寶寶～ 請選 1️⃣ 新增 或 2️⃣ 更新 喔～")
            return

        months = summary.get("months", [])
        month_str = "、".join(sorted(months)) if months else "（未偵測到）"
        _session_save(user_id, {**session, "step": "excel_final", "action": action, "action_label": action_label})

        lines = ["寶寶確認一下～ 👀", "", f"動作：{action_label}"]
        if summary.get("total_sns", 0) > 0:
            lines.append(f"SN商品：{summary['total_sns']} 筆（{month_str}）")
        if summary.get("customers", 0) > 0:
            lines.append(f"客戶資料：{summary['customers']} 位")
        lines += ["", "確定要匯入嗎？", "✅ 確認 / ❌ 取消"]
        reply(reply_token, "\n".join(lines))

    elif step == "excel_final":
        if text not in ["✅", "確認", "ok", "OK", "是", "確定", "好"]:
            reply(reply_token, "寶寶～ 請回覆 ✅ 確認 或 ❌ 取消 喔！")
            return

        file_bytes = _excel_cache.get(user_id)
        if not file_bytes:
            _session_clear(user_id)
            reply(reply_token, "寶寶～ 檔案快取過期了，請重新傳送 Excel 喔 😢")
            return

        action = session.get("action", "new")
        _session_clear(user_id)
        reply(reply_token, "寶寶～ 開始匯入了！稍等一下喔 ⏳")
        _do_excel_import(user_id, file_bytes, action)


def _do_excel_import(user_id: str, file_bytes: bytes, action: str) -> None:
    """Import Excel data to Supabase — called after user confirms"""
    try:
        from utils.excel_parser import parse_excel_file
        parsed = parse_excel_file(BytesIO(file_bytes))
        upsert = (action == "update")

        total_customers = 0
        total_sns = 0
        total_updated = 0

        # existing customers
        existing_customers = {c["name"]: c["id"] for c in sb_get("customers", {"select": "id,name"})}

        # import customers
        for cust in parsed.get("customers", []):
            name = cust.get("name", "")
            if not name or name in existing_customers:
                continue
            result = sb_post("customers", cust)
            if result:
                existing_customers[name] = result["id"]
                total_customers += 1

        # import SNs
        all_sns = [sn for month_sns in parsed.get("sn_by_month", {}).values() for sn in month_sns]

        for sn in all_sns:
            investments = sn.pop("investments", [])
            code = sn.get("product_code", "")

            existing = sb_get("structured_notes", {"product_code": f"eq.{code}", "select": "id"})
            sn_id = None

            if existing:
                if upsert:
                    sn_id = existing[0]["id"]
                    sb_patch("structured_notes", {"id": sn_id}, sn)
                    sb_delete("investments", {"sn_id": sn_id})
                    total_updated += 1
                else:
                    continue
            else:
                result = sb_post("structured_notes", sn)
                if result:
                    sn_id = result["id"]
                    total_sns += 1

            if not sn_id:
                continue

            for inv in investments:
                cname = inv.get("customer_name", "")
                amount = inv.get("amount_usd", 0)
                customer_id = existing_customers.get(cname)
                if not customer_id:
                    cname_clean = cname.replace("*", "").replace("＊", "").strip()
                    for k, v in existing_customers.items():
                        if cname_clean in k.replace("*", "").replace("＊", "").strip():
                            customer_id = v
                            break
                if customer_id:
                    sb_post("investments", {"customer_id": customer_id, "sn_id": sn_id, "amount_usd": amount})

        lines = ["✅ 匯入完成！寶寶辛苦了～ 🎉", ""]
        if total_customers > 0:
            lines.append(f"新增客戶：{total_customers} 位")
        if total_sns > 0:
            lines.append(f"新增 SN：{total_sns} 筆")
        if total_updated > 0:
            lines.append(f"更新 SN：{total_updated} 筆")
        if total_customers == 0 and total_sns == 0 and total_updated == 0:
            lines.append("沒有新資料需要匯入喔～")

        _push_line(user_id, "\n".join(lines))

    except Exception as e:
        print(f"[excel_import error] {e}")
        _push_line(user_id, f"❌ 匯入失敗了 😢\n請確認 Excel 格式是否正確")
    finally:
        _excel_cache.pop(user_id, None)


def _push_to_admins(text: str) -> None:
    admins = sb_get("admins", {"select": "line_user_id"})
    for a in admins:
        uid = a.get("line_user_id", "")
        if uid:
            requests.post(
                "https://api.line.me/v2/bot/message/push",
                headers={
                    "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
                    "Content-Type": "application/json"
                },
                json={"to": uid, "messages": [{"type": "text", "text": text[:4000]}]},
                timeout=10
            )


@app.get("/trigger-report")
def trigger_report(background_tasks: BackgroundTasks, secret: str = ""):
    """cron-job.org เรียก endpoint นี้แทน GitHub Actions"""
    REPORT_SECRET = os.environ.get("REPORT_SECRET", "")
    if REPORT_SECRET and secret != REPORT_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    background_tasks.add_task(_run_daily_report)
    return {"status": "ok", "message": "report queued"}


@app.get("/trigger-obs-alert")
def trigger_obs_alert(background_tasks: BackgroundTasks, secret: str = ""):
    """cron-job.org เรียก endpoint นี้ทุกเช้า 07:00 TWN"""
    REPORT_SECRET = os.environ.get("REPORT_SECRET", "")
    if REPORT_SECRET and secret != REPORT_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    background_tasks.add_task(_run_obs_alert)
    return {"status": "ok", "message": "obs alert queued"}


_GREETINGS = {
    "morning": [
        "早安☀️ 今天也要加油喔，遇到的都是好客戶！",
        "早安～ 新的一天，心情好一點，事情會順很多的。",
        "起床了嗎☀️ 今天也要好好的喔。",
        "早安！昨晚睡得好嗎？今天加油💪",
        "早安～ 喝杯咖啡，準備出發了🫡",
    ],
    "noon": [
        "中午了🍱 記得吃飯，別餓著自己。",
        "吃飯了嗎？別忘了休息一下，下午還有硬仗。",
        "午休時間～ 工作先放一放，吃個飯再說🍱",
        "中午了，今天上午還順利嗎？吃飯充電繼續！",
        "記得吃午飯喔，下午才有力氣應付客戶😄",
    ],
    "night": [
        "晚了🌙 今天辛苦了，早點休息。",
        "該休息了，明天的事明天再說🌙",
        "收工了嗎？今天做得不錯，好好睡一覺。",
        "晚安～ 身體最重要，別太晚睡了。",
        "一天結束了🌙 辛苦了，明天繼續加油。",
    ],
}


def _get_greeting(type: str) -> str:
    period = {"morning": "早上", "noon": "中午", "night": "晚上"}.get(type, "")
    if ANTHROPIC_API_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=80,
                messages=[{"role": "user", "content":
                    f"用繁體中文傳一句{period}問候語給投資顧問，語氣自然像朋友，不要肉麻，不要用「寶寶」，一到兩句就好，不要加任何前綴或說明。"
                }],
            )
            return resp.content[0].text.strip()
        except Exception:
            pass
    import random
    return random.choice(_GREETINGS.get(type, [""]))


@app.get("/trigger-greeting")
def trigger_greeting(background_tasks: BackgroundTasks, type: str = "", secret: str = ""):
    """cron-job.org ยิง 3 ครั้ง/วัน — morning / noon / night"""
    REPORT_SECRET = os.environ.get("REPORT_SECRET", "")
    if REPORT_SECRET and secret != REPORT_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    if type not in _GREETINGS:
        raise HTTPException(status_code=400, detail="type must be morning / noon / night")
    background_tasks.add_task(_push_to_admins, _get_greeting(type))
    return {"status": "ok", "type": type}


def _run_obs_alert() -> None:
    try:
        today = datetime.now(TW).date()
        today_str = today.strftime("%Y/%m/%d")

        sns_today = sb_get("structured_notes", {
            "observation_date": f"eq.{today}",
            "status": "eq.active",
            "select": "*",
        })
        if not sns_today:
            return

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

            invs = sb_get("investments", {
                "sn_id": f"eq.{sn['id']}",
                "select": "customers(name)",
            })
            customer_names = sorted({
                inv["customers"]["name"]
                for inv in invs
                if inv.get("customers") and inv["customers"].get("name")
            })

            lines.append(f"・{sn.get('product_code', '—')}")
            lines.append(f"  {ticker_str}")
            if ko_ki:
                lines.append(f"  {ko_ki}")
            if customer_names:
                lines.append(f"  客戶：{'、'.join(customer_names)}")
            lines.append("")

        _push_to_admins("\n".join(lines).rstrip())

    except Exception as e:
        print(f"[obs_alert error] {e}")


def _run_daily_report() -> None:
    try:
        now_tw = datetime.now(TW)
        today = now_tw.strftime("%Y/%m/%d")
        now_str = now_tw.strftime("%H:%M")
        hour = now_tw.hour
        is_morning = hour < 12
        if is_morning:
            session     = "🌅 早盤報告"
            price_note  = "📌 價格為美股昨日收盤價"
        else:
            session     = "🌙 夜盤報告"
            price_note  = "📌 價格為美股盤中即時報價"

        customers = get_customers()
        sns = get_sns("active")
        total_usd = sum(c.get("usd_amount", 0) or 0 for c in customers)

        all_tickers = list(set(
            s.get(f"underlying_{i}")
            for s in sns for i in range(1, 6)
            if isinstance(s.get(f"underlying_{i}"), str)
        ))
        prices = {t: get_stock_price(t) for t in all_tickers}

        lines = [
            f"\n📊 {session}",
            f"🗓️ {today}  {now_str} (台灣時間)",
            price_note,
            "─────────────────",
            f"\n🏦 管理總覽",
            f"• 客戶總數: {len(customers)} 人",
            f"• 有效商品: {len(sns)} 筆",
            f"• 總投資金額: USD {total_usd:,.0f}",
            "\n📋 商品狀況",
        ]

        today_date = now_tw.date()
        sn_customers = get_sn_customer_map()
        pending_sns = []

        for sn in sorted(sns, key=lambda s: s.get("observation_date") or ""):
            code = sn.get("product_code", "—")
            obs = str(sn.get("observation_date") or "")[:10]
            sn_id = sn.get("id", "")
            try:
                days_left = (date.fromisoformat(obs) - today_date).days if obs else 0
                badge = "🔴" if days_left <= 3 else "⚠️" if days_left <= 7 else "📅"
                days_str = f"剩{days_left}天"
            except Exception:
                badge = "📅"
                days_str = ""

            ko = sn.get("ko_barrier")
            ki = sn.get("ki_barrier")
            worst_pct = None
            detail_lines = []
            for i in range(1, 6):
                ticker = sn.get(f"underlying_{i}")
                init_p = sn.get(f"initial_price_{i}")
                if not ticker or not init_p or init_p <= 0:
                    continue
                curr = prices.get(ticker)
                if curr:
                    pct = curr / init_p
                    if worst_pct is None or pct < worst_pct:
                        worst_pct = pct
                    chg = (pct - 1) * 100
                    arrow = "▲" if chg >= 0 else "▼"
                    ko_s = (" 🟢KO" if ko and pct >= ko else " 🟡近KO" if ko and pct >= ko * 0.95 else "")
                    ki_s = (" 🔴KI" if ki and pct <= ki else " 🟠近KI" if ki and pct <= ki * 1.05 else "")
                    detail_lines.append(f"  {ticker}: ${curr:,.2f} ({arrow}{abs(chg):.1f}%){ko_s}{ki_s}")

            if worst_pct is None:
                names = sn_customers.get(sn_id, [])
                pending_sns.append((code, obs[5:], badge, days_str, names))
                continue
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

            names = sn_customers.get(sn_id, [])
            lines.append(f"\n{overall} {code}")
            if names:
                lines.append(f"  👤 {' / '.join(names)}")
            lines.append(f"  {badge} 比價日: {obs} ({days_str})")
            lines.extend(detail_lines)

        if pending_sns:
            lines.append("\n─────────────")
            lines.append(f"📋 待補資料 ({len(pending_sns)}筆):")
            for (code, obs_short, badge, days_str, names) in pending_sns:
                lines.append(f"  {code}  {badge} {obs_short} ({days_str})")
                if names:
                    lines.append(f"    👤 {', '.join(names)}")

        _push_to_admins("\n".join(lines))
    except Exception as e:
        _push_to_admins(f"⚠️ 日報發送失敗: {e}")


@app.get("/chart/{ticker}.png")
def chart_endpoint(ticker: str):
    ticker = ticker.upper()[:10]
    try:
        img_bytes = _generate_chart(ticker)
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── PPT flow session state ────────────────────────────────────────
_ppt_sessions: dict = {}  # user_id → session dict (backed by Supabase)


def _session_save(user_id: str, data: dict) -> None:
    _ppt_sessions[user_id] = data
    try:
        import json as _json
        sb_get("app_settings", {})  # reuse connection check
        requests.post(
            f"{SUPABASE_URL}/rest/v1/app_settings",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates",
            },
            json={"key": f"ppt_session_{user_id}", "value": _json.dumps(data)},
            timeout=5,
        )
    except Exception:
        pass


def _session_load(user_id: str) -> dict | None:
    if user_id in _ppt_sessions:
        return _ppt_sessions[user_id]
    try:
        import json as _json
        rows = sb_get("app_settings", {
            "select": "value",
            "key": f"eq.ppt_session_{user_id}",
        })
        if rows:
            data = _json.loads(rows[0]["value"])
            _ppt_sessions[user_id] = data
            return data
    except Exception:
        pass
    return None


def _session_clear(user_id: str) -> None:
    _ppt_sessions.pop(user_id, None)
    try:
        requests.delete(
            f"{SUPABASE_URL}/rest/v1/app_settings",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            },
            params={"key": f"eq.ppt_session_{user_id}"},
            timeout=5,
        )
    except Exception:
        pass


def _push_line(user_id: str, text: str) -> None:
    requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={
            "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
        json={"to": user_id, "messages": [{"type": "text", "text": text[:4000]}]},
        timeout=10,
    )


def _upload_excel(excel_bytes: bytes, filename: str) -> str | None:
    """Upload Excel to Supabase Storage, return public URL or None."""
    try:
        url = f"{SUPABASE_URL}/storage/v1/object/excel-reports/{filename}"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "x-upsert": "true",
        }
        resp = requests.post(url, headers=headers, data=excel_bytes, timeout=60)
        if resp.ok:
            return f"{SUPABASE_URL}/storage/v1/object/public/excel-reports/{filename}"
    except Exception as e:
        print(f"[upload_excel error] {e}")
    return None


def _generate_and_send_excel(user_id: str) -> None:
    """Style source_data.xlsx, upload to Supabase Storage, push download link."""
    try:
        from utils.excel_export import build_excel_bytes
        excel_bytes = build_excel_bytes()
        filename = f"export_{datetime.now(TW).strftime('%Y%m%d_%H%M%S')}.xlsx"
        pub_url = _upload_excel(excel_bytes, filename)
        if pub_url:
            _push_line(user_id, f"✅ Excel 已完成！\n\n⬇️ 點擊下載:\n{pub_url}")
        else:
            _push_line(user_id, "❌ 上傳失敗，請重試")
    except Exception as e:
        print(f"[generate_excel error] {e}")
        _push_line(user_id, "❌ Excel 匯出失敗，請重試")


def _upload_ppt(ppt_bytes: bytes, filename: str) -> str | None:
    """Upload PPT to Supabase Storage, return public URL or None."""
    try:
        url = f"{SUPABASE_URL}/storage/v1/object/ppt-reports/{filename}"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "x-upsert": "true",
        }
        resp = requests.post(url, headers=headers, data=ppt_bytes, timeout=60)
        if resp.ok:
            return f"{SUPABASE_URL}/storage/v1/object/public/ppt-reports/{filename}"
    except Exception as e:
        print(f"[upload_ppt error] {e}")
    return None


def _generate_and_send_ppt(user_id: str, tickers: list, period: str = "6mo",
                           customer_names: list | None = None) -> None:
    """Generate PPT, upload, push link to user."""
    try:
        sns = get_sns("active")
        sn_info = {}
        sn_id_map = {}  # ticker → sn_id
        for sn in sns:
            for i in range(1, 6):
                t = _clean_ticker(sn.get(f"underlying_{i}") or "")
                if t and t in tickers and t not in sn_info:
                    sn_info[t] = {
                        "ko": sn.get("ko_barrier"),
                        "ki": sn.get("ki_barrier"),
                        "initial_price": sn.get(f"initial_price_{i}"),
                        "product_code": sn.get("product_code", ""),
                        "strike_pct": sn.get("strike_pct"),
                        "coupon_pct": sn.get("coupon_pct"),
                        "observation_date": sn.get("observation_date"),
                        "exit_date": sn.get("exit_date"),
                    }
                    sn_id_map[t] = sn.get("id")

        # attach customer investment amounts
        if customer_names:
            all_customers = get_customers()
            for cname in customer_names:
                matched_c = [c for c in all_customers if c["name"] == cname]
                if not matched_c:
                    continue
                investments = get_customer_investments(matched_c[0]["id"])
                for inv in investments:
                    sn = inv.get("structured_notes") or {}
                    sn_id = sn.get("id")
                    amount = inv.get("amount_usd") or 0
                    for t, tid in sn_id_map.items():
                        if tid == sn_id and "amount_usd" not in sn_info.get(t, {}):
                            sn_info.setdefault(t, {})["customer_name"] = (
                                "、".join(customer_names)
                                if len(customer_names) > 1 else cname
                            )
                            sn_info[t]["amount_usd"] = amount

        from utils.ppt_export import build_ppt
        ppt_bytes = build_ppt(tickers, sn_info, period=period)

        filename = f"ppt_{datetime.now(TW).strftime('%Y%m%d_%H%M%S')}.pptx"
        pub_url = _upload_ppt(ppt_bytes, filename)

        if pub_url:
            _push_line(user_id,
                f"✅ PPT 已完成！\n"
                f"📊 {', '.join(tickers)}\n\n"
                f"⬇️ 點擊下載:\n{pub_url}"
            )
        else:
            _push_line(user_id, "❌ 上傳失敗，請重試")
    except Exception as e:
        print(f"[generate_ppt error] {e}")
        _push_line(user_id, f"❌ PPT 製作失敗，請重試")


def _parse_amount(text: str) -> int | None:
    if text.strip() in ["跳過", "skip", "-", "無", "/"]:
        return None
    try:
        val = int(float(text.replace(",", "").replace("USD", "").strip()))
        return val if val >= 0 else None
    except ValueError:
        return -1  # sentinel: parse error


def _handle_new_customer(reply_token: str, text: str, user_id: str, session: dict) -> None:
    step = session.get("step")

    if text in ["❌", "取消", "cancel", "Cancel", "不", "不要"]:
        _session_clear(user_id)
        reply(reply_token, "已取消。")
        return

    if step == "new_cust_name":
        name = text.strip()
        if not name:
            reply(reply_token, "姓名不能空白，請重新輸入：")
            return
        existing = sb_get("customers", {"select": "id", "name": f"eq.{name}"})
        if existing:
            _session_clear(user_id)
            reply(reply_token, f"「{name}」已存在於系統中。")
            return
        _session_save(user_id, {"step": "new_cust_usd", "name": name})
        reply(reply_token, f"姓名：{name}\n\nUSD 額度？\n（沒有請輸入 跳過）")

    elif step == "new_cust_usd":
        val = _parse_amount(text)
        if val == -1:
            reply(reply_token, "格式不對，請輸入數字（例：500000）或輸入 跳過：")
            return
        _session_save(user_id, {**session, "step": "new_cust_checks", "usd": val})
        reply(reply_token,
            "以下項目已完成的輸入號碼（可多選，逗號分隔）：\n\n"
            "1. 統一開戶\n"
            "2. ＰＩ見簽\n"
            "3. 已下單\n\n"
            "（都沒有請輸入 跳過）"
        )

    elif step == "new_cust_checks":
        import re
        nums = set(re.findall(r'[123]', text))
        if text.strip() not in ["跳過", "skip", "-", "無"] and not nums and text.strip():
            reply(reply_token, "請輸入 1、2、3 的組合，或輸入 跳過：")
            return
        _session_save(user_id, {
            **session,
            "step": "new_cust_month",
            "unified": "1" in nums,
            "pi": "2" in nums,
            "ordered": "3" in nums,
        })
        reply(reply_token, "下單月份？\n（例：5月  或輸入 跳過）")

    elif step == "new_cust_month":
        month = text.strip() if text.strip() not in ["跳過", "skip", "-", "無"] else ""
        _session_save(user_id, {**session, "step": "new_cust_confirm", "month": month})

        s = session
        usd = s.get("usd")
        unified = s.get("unified", False)
        pi = s.get("pi", False)
        ordered = s.get("ordered", False)
        usd_str = f"USD {usd:,}" if usd else "未設定"
        checks = "  ".join(filter(None, [
            "統一開戶✓" if unified else "",
            "PI見簽✓" if pi else "",
            "已下單✓" if ordered else "",
        ])) or "—"
        reply(reply_token,
            f"確認新增？\n\n"
            f"姓名：{s['name']}\n"
            f"USD 額度：{usd_str}\n"
            f"開戶狀態：{checks}\n"
            f"下單月份：{month or '—'}\n\n"
            f"✅ 確認  /  ❌ 取消"
        )

    elif step == "new_cust_confirm":
        if text not in ["✅", "確認", "ok", "OK", "是", "確定", "好"]:
            reply(reply_token, "請回覆 ✅ 確認 或 ❌ 取消")
            return

        name = session.get("name", "")
        usd = session.get("usd")
        _session_clear(user_id)

        data: dict = {"name": name}
        if usd:
            data["usd_amount"] = usd
        if session.get("unified"):
            data["unified_account"] = True
        if session.get("pi"):
            data["pi_signed"] = True
        if session.get("ordered"):
            data["ordered"] = True
        if session.get("month"):
            data["month_label"] = session["month"]

        result = sb_post("customers", data)
        if result:
            usd_str = f"USD {usd:,}" if usd else "未設定"
            reply(reply_token, f"✅ 已新增客戶\n\n姓名：{name}\nUSD 額度：{usd_str}")
        else:
            reply(reply_token, "❌ 新增失敗，請稍後再試。")


def _process_event(reply_token: str, user_text: str, user_id: str) -> None:
    """รัน background — ตอบ LINE หลังจาก webhook คืนค่าแล้ว"""
    import re
    try:
        text = user_text.strip()

        # ── Excel import session (ตรวจก่อนทุกอย่าง) ─────────────────
        _es = _session_load(user_id)
        if _es and _es.get("step", "").startswith("excel_"):
            _handle_excel_session(reply_token, text, user_id, _es)
            return

        # ── Step 1: เริ่ม PPT flow — แสดงรายชื่อลูกค้า ──────────────
        if re.match(r'^(給我|给我)?\s*ppt$', text, re.IGNORECASE):
            customers = get_customers()
            sns = get_sns("active")

            # สร้าง customer → tickers map
            cust_map = {}
            for c in customers:
                cid = c["id"]
                cname = c["name"]
                invs = get_customer_investments(cid)
                tickers = []
                for inv in invs:
                    sn = inv.get("structured_notes") or {}
                    for i in range(1, 6):
                        t = _clean_ticker(sn.get(f"underlying_{i}") or "")
                        if t and t not in tickers:
                            tickers.append(t)
                if tickers:
                    cust_map[cname] = tickers

            if not cust_map:
                reply(reply_token, "❌ 系統中尚無標的資料")
                return

            cust_list = list(cust_map.keys())
            _session_save(user_id, {"step": "customer", "cust_map": cust_map, "cust_list": cust_list})

            lines = ["👥 選擇客戶 (可多選，逗號分隔)\n"]
            for idx, name in enumerate(cust_list, 1):
                tickers_preview = ", ".join(cust_map[name][:3])
                if len(cust_map[name]) > 3:
                    tickers_preview += f"...+{len(cust_map[name])-3}"
                lines.append(f"{idx}. {name}  ({tickers_preview})")
            lines += ["", "例: 1,3  或  全部"]
            reply(reply_token, "\n".join(lines))
            return

        # ── Step 2: รับคำตอบ PPT flow ──────────────────────────
        session = _session_load(user_id)
        if session:

            # Step 2a: เลือกลูกค้า
            if session.get("step") == "customer":
                cust_map = session["cust_map"]
                cust_list = session["cust_list"]
                selected_tickers = []

                if text in ["全部", "all", "ALL"]:
                    for tickers in cust_map.values():
                        for t in tickers:
                            if t not in selected_tickers:
                                selected_tickers.append(t)
                else:
                    nums = re.findall(r'\d+', text)
                    for n in nums:
                        idx = int(n) - 1
                        if 0 <= idx < len(cust_list):
                            for t in cust_map[cust_list[idx]]:
                                if t not in selected_tickers:
                                    selected_tickers.append(t)

                if not selected_tickers:
                    _session_clear(user_id)
                    reply(reply_token, "❌ 找不到所選客戶\n請重新輸入「給我PPT」")
                    return

                selected_customers = []
                if text in ["全部", "all", "ALL"]:
                    selected_customers = list(cust_map.keys())
                else:
                    for n in re.findall(r'\d+', text):
                        idx = int(n) - 1
                        if 0 <= idx < len(cust_list):
                            selected_customers.append(cust_list[idx])

                _session_save(user_id, {"step": "period", "selected": selected_tickers, "customers": selected_customers})
                reply(reply_token,
                    f"✅ 已選標的:\n{', '.join(selected_tickers)}\n\n"
                    "📅 選擇圖表區間:\n"
                    "1. 1個月\n2. 3個月\n3. 6個月\n"
                    "4. 1年\n5. 1年半\n6. 2年\n7. 3年\n8. 4年\n9. 5年"
                )
                return

            # Step 2b: เลือกหุ้น (legacy - ถ้ายังมี session เก่า)
            if session.get("step") == "tickers":
                options = session["options"]
                selected = []

                if text in ["全部", "ทั้งหมด", "all", "ALL"]:
                    selected = options[:]
                else:
                    nums = re.findall(r'\d+', text)
                    for n in nums:
                        idx = int(n) - 1
                        if 0 <= idx < len(options):
                            selected.append(options[idx])
                    if not selected:
                        for part in re.split(r'[\s,]+', text):
                            t = _clean_ticker(part)
                            if t:
                                selected.append(t)

                if not selected:
                    _session_clear(user_id)
                    reply(reply_token, "❌ 找不到所選標的\n請重新輸入「給我PPT」")
                    return

                _session_save(user_id, {"step": "period", "selected": selected})
                reply(reply_token,
                    f"✅ 已選: {', '.join(selected)}\n\n"
                    "📅 選擇圖表區間:\n"
                    "1. 1個月\n2. 3個月\n3. 6個月\n"
                    "4. 1年\n5. 1年半\n6. 2年\n7. 3年\n8. 4年\n9. 5年"
                )
                return

            # Step 2b: เลือก period
            if session.get("step") == "period":
                _session_clear(user_id)
                selected = session["selected"]
                session_customers = session.get("customers") or []
                period_map = {
                    "1": "1mo", "2": "3mo", "3": "6mo",
                    "4": "1y",  "5": "18mo","6": "2y", "7": "3y", "8": "4y", "9": "5y",
                    "1mo": "1mo", "3mo": "3mo", "6mo": "6mo",
                    "1y": "1y", "18mo": "18mo", "2y": "2y", "3y": "3y", "4y": "4y", "5y": "5y",
                    "1個月": "1mo", "3個月": "3mo", "6個月": "6mo",
                    "1年": "1y", "1年半": "18mo", "2年": "2y", "3年": "3y", "4年": "4y", "5年": "5y",
                    "1个月": "1mo", "3个月": "3mo", "6个月": "6mo",
                }
                period = period_map.get(text.strip())
                if not period:
                    _session_save(user_id, {"step": "period", "selected": selected})
                    reply(reply_token,
                        "❓ 無法識別，請重新選擇\n\n"
                        "📅 選擇圖表區間:\n"
                        "1. 1個月\n2. 3個月\n3. 6個月\n"
                        "4. 1年\n5. 1年半\n6. 2年\n7. 3年\n8. 4年\n9. 5年"
                    )
                    return
                period_label = {
                    "1mo":"1個月","3mo":"3個月","6mo":"6個月",
                    "1y":"1年","18mo":"1年半","2y":"2年","3y":"3年","4y":"4年","5y":"5年",
                }.get(period, period)

                cust_str = "、".join(session_customers) if session_customers else ""
                reply(reply_token,
                    f"⏳ 製作中...\n"
                    f"{'👤 ' + cust_str + chr(10) if cust_str else ''}"
                    f"📊 {', '.join(selected)}\n"
                    f"📅 {period_label}\n"
                    f"約需 1 分鐘，請稍候⌛"
                )
                _generate_and_send_ppt(user_id, selected, period,
                                       customer_names=session_customers or None)
                return

        # ── New customer flow ────────────────────────────────
        if text in ["新增客戶", "加客戶", "新客戶", "新增客户"]:
            _session_save(user_id, {"step": "new_cust_name"})
            reply(reply_token, "新增客戶\n\n請輸入客戶姓名：")
            return

        _nc = _session_load(user_id)
        if _nc and _nc.get("step", "").startswith("new_cust_"):
            _handle_new_customer(reply_token, text, user_id, _nc)
            return

        # ── Excel export (background) ────────────────────────
        if text in ["匯出", "excel", "Excel", "匯出Excel", "匯出excel", "導出"]:
            reply(reply_token, "⏳ 產生中，完成後會傳連結給你...")
            _generate_and_send_excel(user_id)
            return

        # ── คำสั่งปกติ ──────────────────────────────────────────
        response_text, chart_url = handle_command(user_text, user_id)

        # ถ้าไม่รู้จำคำสั่ง → ให้ AI ช่วยตีความ
        if response_text.startswith("❓") and ANTHROPIC_API_KEY:
            ai_response = _ai_handle(user_text, user_id)
            if ai_response:
                reply(reply_token, ai_response)
                return

        reply(reply_token, response_text, chart_url)
    except Exception as e:
        print(f"[process_event error] {e}")


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    # ตรวจ signature ก่อน
    body = await request.body()
    signature = request.headers.get("X-Line-Signature", "")

    if LINE_CHANNEL_SECRET and not verify_signature(body, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        data = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    for event in data.get("events", []):
        if event.get("type") != "message":
            continue
        msg = event.get("message", {})
        reply_token = event.get("replyToken", "")
        user_id = event.get("source", {}).get("userId", "")

        if msg.get("type") == "text":
            user_text = msg.get("text", "").strip()
            background_tasks.add_task(_process_event, reply_token, user_text, user_id)

        elif msg.get("type") == "file":
            message_id = msg.get("id", "")
            filename = msg.get("fileName", "file.xlsx")
            background_tasks.add_task(_process_file_event, reply_token, message_id, filename, user_id)

    # ตอบ LINE ทันที ก่อนที่ reply_token จะหมดอายุ
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
