"""配息追蹤 — 預計配息，計算方式 per-SN 可設定。
  coupon_freq:  monthly/quarterly/semiannual/annual/maturity  (配息頻率)
  coupon_basis: annualized (年化, ÷頻率) | per_period (每期, 直接用)
每期配息 = annualized: 金額×coupon_pct/頻率次數；per_period: 金額×coupon_pct。
年配息 = 每期配息 × 一年次數。tenant-scoped。"""
from datetime import date
from fastapi import APIRouter, Depends
from ..deps import repo
from ..db import Repo

router = APIRouter(prefix="/api/coupons", tags=["coupons"])

# 一年配息次數 (maturity/到期一次 視為 1)
PER_YEAR = {"monthly": 12, "quarterly": 4, "semiannual": 2, "annual": 1, "maturity": 1}


def _d(v):
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None


@router.get("")
def coupons(r: Repo = Depends(repo)):
    today = date.today()
    sns = {s["id"]: s for s in r.find("structured_notes", status="active")}
    invs = r.find("investments", select="amount_usd,currency,sn_id,customers(name)")

    items = []
    annual_total = 0.0
    for inv in invs:
        sn = sns.get(inv.get("sn_id"))
        if not sn:
            continue
        rate = sn.get("coupon_pct")
        amt = inv.get("amount_usd") or 0
        if not rate or not amt:
            continue

        freq = sn.get("coupon_freq") or "monthly"
        basis = sn.get("coupon_basis") or "annualized"
        ppy = PER_YEAR.get(freq, 12)
        per_payment = round(amt * rate / ppy, 2) if basis == "annualized" else round(amt * rate, 2)
        per_year = round(per_payment * ppy, 2)
        annual_total += per_year

        obs = _d(sn.get("observation_date"))
        days_to_obs = (obs - today).days if obs else None

        items.append({
            "customer": (inv.get("customers") or {}).get("name"),
            "product_code": sn.get("product_code"),
            "currency": inv.get("currency") or "USD",
            "amount": amt,
            "annual_pct": round(rate * 100, 2),
            "freq": freq,
            "basis": basis,
            "per_payment": per_payment,
            "per_year": per_year,
            "obs_date": obs.isoformat() if obs else None,
            "days_to_obs": days_to_obs,
        })

    items.sort(key=lambda x: x["obs_date"] or "9999")
    return {
        "items": items,
        "summary": {
            "annual_total": round(annual_total, 2),
            "month_avg": round(annual_total / 12, 2),
            "count": len(items),
        },
    }
