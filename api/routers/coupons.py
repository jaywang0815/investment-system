"""配息追蹤 — 預計每月配息 (FCN 保證配息: 月配, coupon_pct 為年化)。
公式: 每月配息 = 投資金額 × coupon_pct / 12。
注意: 資料目前無 exit_date(到期日)，比價日(observation_date) 視為到期參考；
      累計/到期總額需確認到期模式後再加。tenant-scoped。"""
from datetime import date
from fastapi import APIRouter, Depends
from ..deps import repo
from ..db import Repo

router = APIRouter(prefix="/api/coupons", tags=["coupons"])


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
    month_total = 0.0
    for inv in invs:
        sn = sns.get(inv.get("sn_id"))
        if not sn:
            continue
        rate = sn.get("coupon_pct")
        amt = inv.get("amount_usd") or 0
        if not rate or not amt:
            continue
        monthly = round(amt * rate / 12, 2)
        month_total += monthly

        obs = _d(sn.get("observation_date"))
        days_to_obs = (obs - today).days if obs else None

        items.append({
            "customer": (inv.get("customers") or {}).get("name"),
            "product_code": sn.get("product_code"),
            "currency": inv.get("currency") or "USD",
            "amount": amt,
            "annual_pct": round(rate * 100, 2),
            "monthly": monthly,
            "obs_date": obs.isoformat() if obs else None,
            "days_to_obs": days_to_obs,
        })

    items.sort(key=lambda x: x["obs_date"] or "9999")
    return {
        "items": items,
        "summary": {
            "month_total": round(month_total, 2),
            "count": len(items),
        },
    }
