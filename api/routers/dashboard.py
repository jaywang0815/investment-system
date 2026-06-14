"""總覽統計 — tenant-scoped。"""
import math
from fastapi import APIRouter, Depends
from ..deps import repo
from ..db import Repo

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _f(v):
    # Supabase NUMERIC อาจคืนเป็น string → กัน TypeError; กัน NaN ไม่ให้ยอดรวมพังทั้งหน้า
    try:
        f = float(v) if v not in (None, "") else 0.0
        return 0.0 if math.isnan(f) else f
    except (TypeError, ValueError):
        return 0.0


@router.get("/stats")
def stats(r: Repo = Depends(repo)):
    customers = r.list("customers", select="id,usd_amount,currency")
    sns = r.list("structured_notes", select="id,status")
    invs = r.list("investments", select="amount_usd,currency")

    by_ccy = {}
    for inv in invs:
        c = inv.get("currency") or "USD"
        by_ccy[c] = by_ccy.get(c, 0) + _f(inv.get("amount_usd"))

    return {
        "customers": len(customers),
        "products_total": len(sns),
        "products_active": sum(1 for s in sns if s.get("status") == "active"),
        "investments": len(invs),
        "invested_by_currency": by_ccy,
        "invested_usd_total": by_ccy.get("USD", 0),                            # ยอดลงทุนจริงใน SN
        "credit_usd_total": sum(_f(c.get("usd_amount")) for c in customers),   # เงินทุนลูกค้า
    }
