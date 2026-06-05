"""
LINE Bot Webhook Server - FastAPI
佈署到 Render.com 或本機執行

執行: uvicorn line_bot_server:app --port 8080
"""
import os
import sys
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
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


def get_stock_price(ticker: str) -> Optional[float]:
    try:
        import yfinance as yf
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
def reply(reply_token: str, text: str) -> None:
    requests.post(
        "https://api.line.me/v2/bot/message/reply",
        headers={
            "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "replyToken": reply_token,
            "messages": [{"type": "text", "text": text[:4000]}]
        },
        timeout=10
    )


# ── 查詢股票現價 ───────────────────────────────────────────────
def _check_stock(ticker: str) -> str:
    try:
        if not FINNHUB_TOKEN:
            return "股票查詢尚未設定 API Key"

        resp = requests.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": ticker, "token": FINNHUB_TOKEN},
            timeout=10
        )
        if not resp.ok:
            return f"查詢「{ticker}」失敗，請稍後再試"

        q = resp.json()
        price = q.get("c")   # current price
        prev_close = q.get("pc")  # previous close
        high = q.get("h")    # high of day
        low = q.get("l")     # low of day
        change = q.get("d", 0)
        change_pct = q.get("dp", 0)

        if not price or price == 0:
            return f"找不到「{ticker}」\n請確認股票代號是否正確 (例: AAPL, AMD, TSLA)"

        arrow = "▲" if change >= 0 else "▼"
        sign = "+" if change >= 0 else ""

        # 檢查是否為系統內持有的標的
        sns = get_sns("active")
        related = []
        for s in sns:
            for i in range(1, 6):
                if (s.get(f"underlying_{i}") or "").upper() == ticker:
                    init = s.get(f"initial_price_{i}")
                    ko = s.get("ko_barrier")
                    ki = s.get("ki_barrier")
                    if init and init > 0:
                        perf = price / init
                        status = ""
                        if ko and perf >= ko:
                            status = " [KO觸發]"
                        elif ki and perf <= ki:
                            status = " [KI觸發]"
                        elif ko and perf >= ko * 0.97:
                            status = " [接近KO]"
                        elif ki and perf <= ki * 1.1:
                            status = " [接近KI]"
                        related.append(
                            f"  {s.get('product_code','—')} "
                            f"({perf*100:.1f}%){status}"
                        )

        lines = [
            f"[{ticker}] 即時報價",
            f"現價: ${price:.2f}",
            f"{arrow} {sign}{change:.2f} ({sign}{change_pct:.2f}%)",
            f"今日: ${low:.2f} – ${high:.2f}",
        ]

        if related:
            lines.append("")
            lines.append("相關持倉:")
            lines.extend(related[:5])

        return "\n".join(lines)

    except Exception as e:
        return f"查詢失敗: {e}"


# ── 指令處理 ──────────────────────────────────────────────────
def handle_command(text: str, user_id: str = "") -> str:
    text = text.strip()
    today = date.today().strftime("%Y/%m/%d")

    # myid — 回傳自己的 LINE User ID
    if text.lower() in ["myid", "my id", "我的id", "id"]:
        return (
            f"🔑 您的 LINE User ID:\n\n"
            f"{user_id}\n\n"
            f"請將此 ID 傳給管理員，即可接收投資通知。"
        )

    # เช็คราคาหุ้น — ตรวจสอบว่าเป็น ticker หรือเปล่า
    import re
    if re.match(r'^[A-Za-z]{1,6}(\.[A-Za-z]{1,3})?$', text):
        return _check_stock(text.upper())

    # 幫助
    if text in ["幫助", "help", "說明", "?", "？"]:
        return (
            "📊 投資管理系統指令說明\n\n"
            "🔍 查詢指令:\n"
            "  [股票代號] → 查詢股票現價 (例: AAPL)\n"
            "  [客戶姓名] → 查詢個人持倉\n"
            "  例: 游家順\n\n"
            "📋 系統指令:\n"
            "  日報 → 今日投資摘要\n"
            "  警示 → KO/KI 警示列表\n"
            "  客戶 → 所有客戶列表\n"
            "  myid → 查詢自己的 LINE ID\n"
            "  幫助 → 顯示此說明"
        )

    # 日報
    if text in ["日報", "報告", "今日", "today"]:
        sns = get_sns("active")
        customers = get_customers()
        total_usd = sum(c.get("usd_amount", 0) or 0 for c in customers)

        lines = [
            f"📊 每日投資報告",
            f"🗓️ {today}",
            "─────────────",
            f"👥 客戶總數: {len(customers)} 人",
            f"📊 有效商品: {len(sns)} 筆",
            f"💰 總額度: USD {total_usd:,.0f}",
            "",
            "📅 近期比價日:"
        ]

        today_date = date.today()
        from datetime import timedelta
        upcoming = [s for s in sns if s.get("observation_date") and
                    s["observation_date"] >= str(today_date) and
                    s["observation_date"] <= str(today_date + timedelta(days=14))]

        if upcoming:
            for s in upcoming[:5]:
                obs = s["observation_date"][:10]
                code = s.get("product_code", "—")
                _nums = ["①","②","③","④","⑤"]
                tstr = " ".join(
                    f"{_nums[i-1]}{s.get(f'underlying_{i}')}"
                    for i in range(1, 6)
                    if s.get(f"underlying_{i}")
                )
                lines.append(f"  📌 {obs} | {code} ({tstr})")
        else:
            lines.append("  近期無比價日")

        lines += ["", "─────────────", "輸入客戶姓名查詢個人持倉"]
        return "\n".join(lines)

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
        return "\n".join(alert_msgs)

    # 客戶列表
    if text in ["客戶", "客户", "列表", "list"]:
        customers = get_customers()
        if not customers:
            return "尚無客戶資料"
        lines = [f"👥 客戶列表 ({len(customers)} 人)\n─────────────"]
        for c in customers[:20]:
            usd = c.get("usd_amount")
            usd_str = f"USD {usd:,.0f}" if usd else ""
            lines.append(f"• {c['name']} {usd_str}")
        if len(customers) > 20:
            lines.append(f"...共 {len(customers)} 位客戶")
        return "\n".join(lines)

    # 依客戶姓名查詢
    customers = get_customers()
    matched = [c for c in customers if text in c["name"] or c["name"] in text]

    if matched:
        c = matched[0]
        investments = get_customer_investments(c["id"])

        if not investments:
            return f"👤 {c['name']}\n目前無投資持倉記錄"

        total = sum(i.get("amount_usd", 0) or 0 for i in investments)
        lines = [
            f"👤 {c['name']} 持倉報告",
            f"🗓️ {today}",
            "─────────────",
            f"持倉筆數: {len(investments)} 筆",
            f"總金額: USD {total:,.0f}",
            ""
        ]

        for inv in investments[:5]:  # 最多5筆
            sn = inv.get("structured_notes") or {}
            if not sn:
                continue
            code = sn.get("product_code", "—")
            _nums = ["①","②","③","④","⑤"]
            tstr = " ".join(
                f"{_nums[i-1]}{sn.get(f'underlying_{i}')}"
                for i in range(1, 6)
                if sn.get(f"underlying_{i}")
            )
            obs = str(sn.get("observation_date", ""))[:10]
            amount = inv.get("amount_usd", 0) or 0
            coupon = sn.get("coupon_pct")
            coupon_str = f" 配息{coupon*100:.1f}%" if coupon else ""

            # 取得最差標的現價 (所有標的都比較)
            worst_str = ""
            worst_perf = None
            for i in range(1, 6):
                ticker = sn.get(f"underlying_{i}")
                init = sn.get(f"initial_price_{i}")
                if ticker and init and init > 0:
                    price = get_stock_price(ticker)
                    if price:
                        perf = price / init * 100
                        if worst_perf is None or perf < worst_perf:
                            worst_perf = perf
                            worst_str = f" ({ticker} {perf:.1f}%)"

            lines.append(f"📌 {code}")
            lines.append(f"   標的: {tstr}")
            lines.append(f"   金額: USD {amount:,.0f}{coupon_str}")
            lines.append(f"   比價: {obs}{worst_str}")
            lines.append("")

        if len(investments) > 5:
            lines.append(f"...共 {len(investments)} 筆，請至後台查看完整報表")

        lines.append("─────────────")
        lines.append("完整PDF請至管理後台下載")
        return "\n".join(lines)

    # 找不到
    return (
        f"❓ 找不到「{text}」\n\n"
        "可能的指令:\n"
        "• 輸入客戶姓名查詢持倉\n"
        "• 日報 → 每日摘要\n"
        "• 警示 → KO/KI 警示\n"
        "• 幫助 → 指令說明"
    )


# ── API 端點 ──────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "LINE Bot Server Running", "date": str(date.today())}


@app.post("/webhook")
async def webhook(request: Request):
    # 驗證 LINE 簽名
    body = await request.body()
    signature = request.headers.get("X-Line-Signature", "")

    if LINE_CHANNEL_SECRET and not verify_signature(body, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 解析事件
    try:
        data = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    for event in data.get("events", []):
        if event.get("type") == "message" and event["message"].get("type") == "text":
            reply_token = event.get("replyToken", "")
            user_text = event["message"].get("text", "").strip()
            user_id = event.get("source", {}).get("userId", "")

            response_text = handle_command(user_text, user_id)
            reply(reply_token, response_text)

    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
