"""報表 — 重用既有 Python 模組 (pdf_report / excel_export)，tenant-scoped。"""
import threading
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from datetime import date
from urllib.parse import quote
from utils import branding as B
from ..deps import repo
from ..db import Repo

router = APIRouter(prefix="/api/reports", tags=["reports"])

# 主題色用「覆寫全域 branding」方式 → 用鎖序列化 PDF 產生，避免併發互相干擾。
_PDF_LOCK = threading.Lock()


def _tenant_branding(r: Repo):
    """อ่านชื่อบริษัท/報告人/logo ของ tenant ที่ login (ไว้ใส่ใน PDF)。"""
    for cols in ("company_name,reporter,logo", "company_name,reporter"):
        try:
            rows = r.sb.table("tenants").select(cols).eq("id", r.tenant_id).execute().data
            t = rows[0] if rows else {}
            return t.get("company_name"), t.get("reporter"), t.get("logo")
        except Exception:
            continue
    return None, None, None


def _generate_with_theme(theme: Optional[str], branding, fn, *args, **kwargs) -> bytes:
    """套用主題色 + tenant 品牌 → 產生 PDF → 還原預設 (緒安全)。branding=(company, reporter, logo)。"""
    from utils.pdf_report import _refresh_palette
    company, reporter, logo = (branding or (None, None, None))
    with _PDF_LOCK:
        B.apply_theme(theme)
        B.apply_identity(company, reporter, logo)
        _refresh_palette()
        try:
            return fn(*args, **kwargs)
        finally:
            B.apply_theme(B.DEFAULT_THEME)
            B.apply_identity()
            _refresh_palette()


def _pdf_response(pdf: bytes, name: str) -> Response:
    """Content-Disposition 需 latin-1，含中文檔名改用 RFC 5987 (filename*)。"""
    ascii_name = f"report_{date.today():%Y%m%d}.pdf"
    disp = f"inline; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name)}"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": disp})


def _prices_for(invs):
    from utils.stock_prices import get_prices
    tickers = []
    for inv in invs:
        sn = inv.get("structured_notes") or {}
        for i in range(1, 6):
            t = sn.get(f"underlying_{i}")
            if isinstance(t, str):
                tickers.append(t)
    return get_prices(list(set(tickers))) if tickers else {}


# 可選欄位 (給前端彈窗下拉用；標的名稱固定顯示)
REPORT_COLUMNS = ["期初價格", "現價", "漲跌幅", "執行價", "KO 水位", "KI 水位", "狀態"]
# 走勢圖區間 (value -> 中文標籤)
CHART_PERIODS = [
    {"value": "3mo", "label": "3 個月"}, {"value": "6mo", "label": "6 個月"},
    {"value": "1y", "label": "1 年"}, {"value": "2y", "label": "2 年"},
    {"value": "3y", "label": "3 年"}, {"value": "5y", "label": "5 年"},
]


@router.get("/options")
def report_options(r: Repo = Depends(repo)):
    """報表設定彈窗用的選項 (欄位 / 區間 / 主題色)。"""
    return {"columns": REPORT_COLUMNS, "periods": CHART_PERIODS, "themes": B.themes_list()}


@router.get("/customer/{cid}/pdf")
def customer_pdf(cid: str, charts: bool = False, period: str = "6mo",
                 columns: Optional[str] = None, show_info: bool = True,
                 show_amount: bool = True, theme: Optional[str] = None,
                 sns: Optional[str] = None,
                 r: Repo = Depends(repo)):
    """單一客戶完整報表 PDF (含投資明細 + 走勢圖)。
    columns: 逗號分隔欄位名 (省略=全部)；sns: 逗號分隔 SN id (省略=全部商品)；charts=true 會較慢 (抓 yfinance)。"""
    cust = r.get("customers", cid)
    if not cust:
        raise HTTPException(status_code=404, detail="找不到客戶")
    invs = r.find("investments", select="amount_usd,currency,structured_notes(*)", customer_id=cid)
    if not invs:
        raise HTTPException(status_code=404, detail="此客戶尚無投資記錄，無法產生報表")

    # filter เฉพาะ SN ที่เลือก (ถ้าส่งมา) — ไม่ส่ง = ทั้งหมด
    if sns:
        want = {s.strip() for s in sns.split(",") if s.strip()}
        invs = [iv for iv in invs if (iv.get("structured_notes") or {}).get("id") in want]
        if not invs:
            raise HTTPException(status_code=404, detail="所選商品無投資記錄")

    cols = [c.strip() for c in columns.split(",") if c.strip()] if columns else None
    from utils.pdf_report import generate_customer_report
    prices = _prices_for(invs) if charts else {}
    pdf = _generate_with_theme(theme, _tenant_branding(r), generate_customer_report,
                               cust, invs, prices,
                               chart_period=period, columns=cols, show_info=show_info,
                               show_amount=show_amount, show_charts=charts)
    return _pdf_response(pdf, f"report_{cust.get('name','customer')}_{date.today():%Y%m%d}.pdf")


@router.get("/portfolio/pdf")
def portfolio_pdf(section: str = "CTBC", theme: Optional[str] = None,
                  customer_ids: Optional[str] = None, r: Repo = Depends(repo)):
    """客戶投資明細表 PDF (此租戶)。customer_ids: 逗號分隔 customer id (省略=全部客戶)。"""
    rows = r.find("investments",
                  select="amount_usd,currency,customer_id,customers(name),structured_notes(product_code,trade_date,observation_date,coupon_pct,exit_date,status)")
    if customer_ids:
        want = {c.strip() for c in customer_ids.split(",") if c.strip()}
        rows = [x for x in rows if x.get("customer_id") in want]
    items = []
    for x in rows:
        sn = x.get("structured_notes") or {}
        items.append({
            "customer": (x.get("customers") or {}).get("name", "—"),
            "trade_date": sn.get("trade_date"),
            "product_code": sn.get("product_code"),
            "observation_date": sn.get("observation_date"),
            "coupon_pct": sn.get("coupon_pct"),
            "amount": x.get("amount_usd"),
            "currency": x.get("currency") or "USD",
            "exit_date": sn.get("exit_date"),
            "status": sn.get("status"),
        })
    if not items:
        raise HTTPException(status_code=404, detail="無投資資料")
    items.sort(key=lambda i: i["customer"] or "zz")
    from utils.pdf_report import generate_portfolio_detail
    pdf = _generate_with_theme(theme, _tenant_branding(r), generate_portfolio_detail, items,
                               report_date=str(date.today()), section_title=section)
    return _pdf_response(pdf, f"portfolio_{date.today():%Y%m%d}.pdf")
