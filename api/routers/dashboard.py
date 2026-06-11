"""總覽統計 — tenant-scoped。"""
from fastapi import APIRouter, Depends
from ..deps import repo
from ..db import Repo

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def stats(r: Repo = Depends(repo)):
    customers = r.list("customers", select="id,usd_amount,currency")
    sns = r.list("structured_notes", select="id,status")
    invs = r.list("investments", select="amount_usd,currency")

    by_ccy = {}
    for inv in invs:
        c = inv.get("currency") or "USD"
        by_ccy[c] = by_ccy.get(c, 0) + (inv.get("amount_usd") or 0)

    return {
        "customers": len(customers),
        "products_total": len(sns),
        "products_active": sum(1 for s in sns if s.get("status") == "active"),
        "investments": len(invs),
        "invested_by_currency": by_ccy,
        "credit_usd_total": sum(c.get("usd_amount") or 0 for c in customers),
    }
