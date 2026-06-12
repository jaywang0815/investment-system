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
