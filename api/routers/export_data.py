"""資料匯出 — tenant 的 客戶/商品/投資 匯出成 Excel (與範本同格式、含空白列可續填、可再匯入)。"""
import io
from datetime import date
from fastapi import APIRouter, Depends, Response
from ..deps import repo
from ..db import Repo

router = APIRouter(prefix="/api/export", tags=["export"])

FREQ_REV = {"monthly": "月配", "quarterly": "季配", "semiannual": "半年配", "annual": "年配", "maturity": "到期一次"}
STATUS_REV = {"active": "進行中", "exited": "已出場", "inactive": "暫停"}


def _pct(v):
    return round(float(v) * 100, 4) if isinstance(v, (int, float)) else None


def _d(v):
    return str(v)[:10] if v else None


def _pctstr(v):
    """0.1533 → '15.33%' (ตรงรูปแบบไฟล์ 統一)。"""
    return f"{float(v) * 100:.2f}%" if isinstance(v, (int, float)) else None


# 月配→'1' (round-trip กับฟอร์แมต 統一 ที่ใช้เลข)
FREQ_TO_NUM = {"monthly": "1", "quarterly": "3", "semiannual": "6", "annual": "12", "maturity": ""}


@router.get("/unidos")
def export_unidos(blank: bool = False, r: Repo = Depends(repo)):
    """匯出成 統一證券 庫存查詢 ฟอร์แมต (32 คอลัมน์) — import กลับได้。
    blank=true → ฟอร์มเปล่า (หัวอย่างเดียว, เหมือน Template.xlsx) สำหรับกรอกใหม่。"""
    from utils.excel_template import build_unidos_workbook

    invs = [] if blank else r.find("investments", select="amount_usd,currency,customers(name),structured_notes(*)")
    rows = []
    for iv in invs:
        sn = iv.get("structured_notes") or {}
        row = {
            "PSC商品代碼": sn.get("product_code"),
            "幣別": iv.get("currency") or "USD",
            "名目本金(計價幣)": iv.get("amount_usd"),
            "客戶名稱": (iv.get("customers") or {}).get("name"),
            "交易日": _d(sn.get("trade_date")),
            "最後保證配息日": _d(sn.get("observation_date")),
            "發行日": _d(sn.get("issue_date")),
            "期末訂價日": _d(sn.get("final_pricing_date")),
            "商品到期日": _d(sn.get("exit_date")),
            "產品別": sn.get("product_type") or "FCN",
            "天期 (月)": sn.get("tenor_months"),
            "利率": _pctstr(sn.get("coupon_pct")),
            "配息頻率": FREQ_TO_NUM.get(sn.get("coupon_freq") or "monthly", "1"),
            "配息區間/執行價": _pctstr(sn.get("strike_pct")),
            "提前出場型式": sn.get("ko_type"),
            "提前出場價": _pctstr(sn.get("ko_barrier")),
            "下限型式": sn.get("ki_type"),
            "界限價": _pctstr(sn.get("ki_barrier")),
            "交割日": sn.get("settlement_days"),
            "保證配息月數": sn.get("guaranteed_coupon_months"),
            "成交上手": sn.get("counterparty"),
            "價格": sn.get("price_type"),
        }
        for i in range(1, 6):
            row[f"連結標的{i}"] = sn.get(f"underlying_{i}")
            row[f"期初價格{i}"] = sn.get(f"initial_price_{i}")
        rows.append(row)

    wb = build_unidos_workbook(rows)
    buf = io.BytesIO(); wb.save(buf)
    name = "unidos_template.xlsx" if blank else f"unidos_export_{date.today():%Y%m%d}.xlsx"
    return Response(content=buf.getvalue(),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/excel")
def export_excel(r: Repo = Depends(repo)):
    from utils.excel_template import build_workbook

    custs = r.list("customers", order="name")
    prods = r.list("structured_notes", order="product_code")
    invs = r.find("investments", select="amount_usd,currency,customers(name),structured_notes(product_code)")

    data = {
        "customers": [{
            "name": c.get("name"), "usd_amount": c.get("usd_amount"),
            "currency": c.get("currency") or "USD",
            "unified_account": c.get("unified_account"), "notes": c.get("notes"),
        } for c in custs],
        "products": [{
            "product_code": p.get("product_code"), "category": p.get("category") or "SN",
            "underlying_1": p.get("underlying_1"), "initial_price_1": p.get("initial_price_1"),
            "underlying_2": p.get("underlying_2"), "initial_price_2": p.get("initial_price_2"),
            "underlying_3": p.get("underlying_3"), "initial_price_3": p.get("initial_price_3"),
            "ko_barrier": _pct(p.get("ko_barrier")), "ki_barrier": _pct(p.get("ki_barrier")),
            "strike_pct": _pct(p.get("strike_pct")), "coupon_pct": _pct(p.get("coupon_pct")),
            "coupon_freq": FREQ_REV.get(p.get("coupon_freq") or "monthly", "月配"),
            "trade_date": _d(p.get("trade_date")), "observation_date": _d(p.get("observation_date")),
            "exit_date": _d(p.get("exit_date")), "status": STATUS_REV.get(p.get("status") or "active", "進行中"),
        } for p in prods],
        "investments": [{
            "customer": (iv.get("customers") or {}).get("name"),
            "product_code": (iv.get("structured_notes") or {}).get("product_code"),
            "amount_usd": iv.get("amount_usd"), "currency": iv.get("currency") or "USD",
        } for iv in invs],
    }

    wb = build_workbook(data)
    buf = io.BytesIO(); wb.save(buf)
    name = f"investment_export_{date.today():%Y%m%d}.xlsx"
    return Response(content=buf.getvalue(),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})
