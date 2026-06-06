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
from datetime import date

# ── 設定 ──────────────────────────────────────────────────────
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
FINNHUB_TOKEN = os.environ.get("FINNHUB_TOKEN", "")
BASE_URL = os.environ.get("BASE_URL", "").rstrip("/")

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

            # คำนวณ worst performance (ไม่แสดง KO/KI ใน日報 เพื่อไม่ซ้ำกับ警示)
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
                    detail_lines.append(f"  {ticker}: ${curr:,.2f} ({arrow}{abs(chg):.1f}%)")

            if worst_pct is None:
                continue  # ไม่มีข้อมูลราคา ข้ามไปเลย

            lines.append(f"\n📌 {code}")
            if obs:
                lines.append(f"  {badge} 比價: {obs} ({days_str})")
            lines.extend(detail_lines)

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
        for c in customers[:20]:
            usd = c.get("usd_amount")
            usd_str = f"USD {usd:,.0f}" if usd else ""
            lines.append(f"• {c['name']} {usd_str}")
        if len(customers) > 20:
            lines.append(f"...共 {len(customers)} 位客戶")
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


@app.get("/chart/{ticker}.png")
def chart_endpoint(ticker: str):
    ticker = ticker.upper()[:10]
    try:
        img_bytes = _generate_chart(ticker)
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


def _process_event(reply_token: str, user_text: str, user_id: str) -> None:
    """รัน background — ตอบ LINE หลังจาก webhook คืนค่าแล้ว"""
    try:
        response_text, chart_url = handle_command(user_text, user_id)
        reply(reply_token, response_text, chart_url)
    except Exception:
        pass


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
        if event.get("type") == "message" and event["message"].get("type") == "text":
            reply_token = event.get("replyToken", "")
            user_text = event["message"].get("text", "").strip()
            user_id = event.get("source", {}).get("userId", "")
            background_tasks.add_task(_process_event, reply_token, user_text, user_id)

    # ตอบ LINE ทันที ก่อนที่ reply_token จะหมดอายุ
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
