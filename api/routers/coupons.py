"""配息追蹤 — 預計配息，計算方式 per-SN 可設定。
  coupon_freq:  monthly/quarterly/semiannual/annual/maturity  (配息頻率)
  coupon_basis: annualized (年化, ÷頻率) | per_period (每期, 直接用)
每期配息 = annualized: 金額×coupon_pct/頻率次數；per_period: 金額×coupon_pct。
年配息 = 每期配息 × 一年次數。tenant-scoped。"""
import calendar
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


def _months_days(start: date, end: date):
    """full months ระหว่าง start→end + วันเศษหลังเดือนเต็มล่าสุด。"""
    if not start or not end or end <= start:
        return 0, 0
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    months = max(0, months)
    ay = start.year + (start.month - 1 + months) // 12
    am = (start.month - 1 + months) % 12 + 1
    ad = min(start.day, calendar.monthrange(ay, am)[1])
    anchor = date(ay, am, ad)
    leftover = max(0, (end - anchor).days)
    return months, leftover


def _num(v):
    try:
        return float(v) if v not in (None, "") else 0.0
    except (TypeError, ValueError):
        return 0.0


@router.get("")
def coupons(r: Repo = Depends(repo)):
    today = date.today()
    sns = {s["id"]: s for s in r.list("structured_notes")}  # รวม active + KO/出場 (เพื่อคิดดอกสะสม)
    invs = r.find("investments", select="amount_usd,currency,sn_id,customers(name)")

    items = []
    annual_total = 0.0
    accrued_total = 0.0
    for inv in invs:
        sn = sns.get(inv.get("sn_id"))
        if not sn:
            continue
        rate = _num(sn.get("coupon_pct"))
        amt = _num(inv.get("amount_usd"))
        if not rate or not amt:
            continue

        freq = sn.get("coupon_freq") or "monthly"
        basis = sn.get("coupon_basis") or "annualized"
        ppy = PER_YEAR.get(freq, 12)
        per_payment = round(amt * rate / ppy, 2) if basis == "annualized" else round(amt * rate, 2)
        per_year = round(per_payment * ppy if basis == "annualized" else per_payment * ppy, 2)
        # ดอกต่อเดือน/ต่อวัน อิงอัตราต่อปี (amt × rate)
        annual_amt = amt * rate if basis == "annualized" else per_year
        monthly = annual_amt / 12.0
        daily = annual_amt / 365.0
        annual_total += per_year

        # 目前累積配息：คูปองเริ่มจ่าย "หลังถึง 比價日 (observation_date)" เท่านั้น
        # ก่อนถึง 比價日 = ยังไม่มีคูปอง (= 0) ; ถึง 比價日 = งวดแรก, จากนั้นรายเดือน
        # → จำนวนงวด = เดือนเต็มนับจาก 比價日 + 1 ; KO/出場 บวกวันเศษ × ดอกวัน
        obs_start = _d(sn.get("observation_date"))
        status = (sn.get("status") or "active")
        exited = status not in ("active", "", None)
        exit_d = _d(sn.get("exit_date"))
        end = (exit_d or today) if exited else today
        if not obs_start or not end or end < obs_start:
            periods = 0   # ยังไม่ถึง 比價日 → ยังไม่จ่ายคูปอง
            accrued = 0.0
        else:
            months, leftover = _months_days(obs_start, end)
            periods = months + 1
            accrued = periods * monthly + (leftover * daily if exited else 0.0)
        accrued = round(accrued, 2)
        accrued_total += accrued

        obs = _d(sn.get("observation_date"))
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
            "accrued": accrued,
            "accrued_months": periods,
            "exited": exited,
            "status": status,
            "obs_date": obs.isoformat() if obs else None,
            "days_to_obs": (obs - today).days if obs else None,
        })

    items.sort(key=lambda x: x["obs_date"] or "9999")
    return {
        "items": items,
        "summary": {
            "annual_total": round(annual_total, 2),
            "month_avg": round(annual_total / 12, 2),
            "accrued_total": round(accrued_total, 2),
            "count": len(items),
        },
    }
