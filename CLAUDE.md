# CLAUDE.md — DOUU WORK 投資管理系統

## โปรเจกต์คืออะไร
ระบบจัดการ Structured Note (SN) สำหรับลูกค้าการลงทุน — ดูแลข้อมูลลูกค้า, ติดตาม KO/KI, ส่งแจ้งเตือนผ่าน LINE, ออกรายงาน PDF/Excel/PPT

## Tech Stack
- **Frontend**: Streamlit multipage app → deploy บน Streamlit Cloud
- **Backend**: FastAPI (LINE Bot webhook) → deploy บน Render.com
- **Database**: Supabase (PostgreSQL)
- **LINE Bot**: LINE Messaging API (push + reply)
- **Charts**: TradingView widget (web), mplfinance + matplotlib (PPT)
- **Reports**: python-pptx, reportlab (PDF), openpyxl (Excel)

## Deploy URLs
- Streamlit app: `https://douuwork.streamlit.app/` (หรือ domain ที่ตั้งไว้)
- LINE Bot webhook: Render.com (ต้องตั้ง `BASE_URL` env var)

## Secrets ที่ต้องตั้งใน Streamlit Cloud
```
SUPABASE_URL
SUPABASE_KEY
ADMIN_PASSWORD   # ปัจจุบัน: 1227
LINE_CHANNEL_ACCESS_TOKEN
LINE_CHANNEL_SECRET
GOOGLE_SHEETS_CREDS  # JSON service account
```

## Secrets ที่ต้องตั้งใน Render.com
```
LINE_CHANNEL_SECRET
LINE_CHANNEL_ACCESS_TOKEN
SUPABASE_URL
SUPABASE_KEY
BASE_URL   # https://<app-name>.onrender.com
```

## โครงสร้างไฟล์สำคัญ
```
app.py                     # Login + cookie auth (streamlit-cookies-controller)
line_bot_server.py         # FastAPI LINE webhook + /chart/{ticker}.png
pages/
  0_🐾_系統設定.py         # Admin settings, LINE admin management
  1_🐶_客戶管理.py         # Customer CRUD
  2_🦮_SN商品管理.py       # SN product management (KO/KI/barriers)
  3_🐕_KO_KI警示.py        # Real-time KO/KI alert dashboard
  4_🐩_報表匯出.py         # PDF/Excel export
  5_🐕‍🦺_資料匯入.py       # Import SN data from Excel
  6_🐶_月份管理.py         # Monthly observation management
  7_🐾_即時圖表.py         # TradingView charts + PPT export
utils/
  database.py              # Supabase CRUD helpers
  ui_helpers.py            # dog_header(), _img_b64() — page headers with dog icons
  ppt_export.py            # build_ppt() — candlestick+RSI+MACD charts
  pdf_report.py            # PDF generation
  excel_export.py          # Excel export
  stock_prices.py          # yfinance price fetching
assets/
  logo.png                 # Two cartoon dogs (icon)
  dog_bw.png               # Lying B&W French bulldog
  animals/                 # 28 animal PNG icons for page headers
```

## Database Tables (Supabase)
- `customers` — id, name, usd_amount, portal_token, line_user_id
- `structured_notes` — product_code, underlying_1..5, initial_price_1..5, ko_barrier, ki_barrier, coupon_pct, observation_date, exit_date, status
- `investments` — customer_id, structured_note_id, amount_usd
- `admins` — line_user_id, name (รับ LINE push notifications)
- `months` — month management

## Auth
- PIN-based login (ADMIN_PASSWORD secret)
- Cookie persistence 30 วัน ด้วย `streamlit-cookies-controller`
- `st.session_state["authenticated"] = True` เมื่อ login สำเร็จ

## LINE Bot Commands
- `[TICKER]` — ราคาหุ้น + TradingView link (yfinance fast_info)
- `日報` — รายงานรายวัน SN ทั้งหมด + สถานะ KO/KI
- `警示` — รายการใกล้ KO/KI
- `客戶` — รายชื่อลูกค้า
- `[ชื่อลูกค้า]` — ดูพอร์ตลูกค้า
- `myid` — ดู LINE User ID ของตัวเอง

## ข้อตกลงสำคัญ
- Ticker ใน DB อาจมี `$` นำหน้า (เช่น `$ANET`) — ต้อง `lstrip("$")` ก่อน yfinance เสมอ
- ทุกหน้าใช้ `dog_header("หัวข้อ")` จาก `utils/ui_helpers.py` แทน `st.title()`
- NaN จาก DB ต้องเช็คด้วย `math.isnan()` ไม่ใช่แค่ `if val:`
- PPT chart ใช้ mplfinance (candlestick+RSI+MACD) มี fallback เป็น pure matplotlib

## Style / Design
- โทนสี: Navy (#1E3A8A), Green (#26a69a), Red (#ef5350)
- ธีม: ฝรั่งเศสบูลด็อก "DOUU WORK" — ใช้รูปหมาตกแต่งทุกหน้า
- ไม่ใช้ emoji ใน code comment
- ตอบสั้นกระชับ ไม่ต้องสรุปซ้ำท้าย response

## งานที่ค้างอยู่ / Known Issues
- `st.components.v1.html` → deprecated ควรเปลี่ยนเป็น `st.iframe` (warning เท่านั้น ไม่ crash)
- BASE_URL บน Render.com ต้องตั้งเองใน env vars เพื่อให้ /chart/{ticker}.png ทำงาน
