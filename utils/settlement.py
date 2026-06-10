"""
結算計算 — 依客戶確認的規則
- 配息基準日 = 期初日 + 7 天 (前 7 天不計息)
- 第一個月「保證配息」: 至少給滿第一個月
- 超過第一個月: 按實際天數 (當天計息, 含出場日)；大小月以實際天數處理
- 配息金額 = 本金 × 年化配息率 × 天數 / 365   (原幣)
- 結算合計 = 本金 + 配息金額
"""
from datetime import date, timedelta
from typing import Optional

try:
    from dateutil.relativedelta import relativedelta
    def _add_month(d: date) -> date:
        return d + relativedelta(months=1)
except Exception:
    def _add_month(d: date) -> date:  # fallback: 約 30 天
        return d + timedelta(days=30)

BASE_OFFSET_DAYS = 7
DAY_BASIS = 365


def _to_date(v) -> Optional[date]:
    if v is None or v == "":
        return None
    if isinstance(v, date):
        return v
    s = str(v)[:10]
    try:
        return date.fromisoformat(s)
    except Exception:
        return None


def settle(principal: float, annual_pct: float, trade_date, exit_date,
           currency: str = "USD") -> dict:
    """
    回傳 dict: base_date, exit_date, days, coupon, total, currency, guaranteed(bool)
    annual_pct: 小數 (0.15 = 15%)
    """
    td = _to_date(trade_date)
    ed = _to_date(exit_date)
    out = {"currency": currency, "base_date": None, "exit_date": ed,
           "days": 0, "coupon": 0.0, "total": float(principal or 0),
           "guaranteed": False, "error": None}

    if td is None or ed is None or not principal or not annual_pct:
        out["error"] = "缺少資料 (期初日 / 出場日 / 本金 / 配息率)"
        return out

    base = td + timedelta(days=BASE_OFFSET_DAYS)        # 配息基準日
    first_month_end = _add_month(base)                   # 第一個月結束
    first_month_days = (first_month_end - base).days     # 保證天數 (約30-31)
    actual_days = (ed - base).days + 1                   # 含出場日 (當天計息)

    coupon_days = max(first_month_days, actual_days)
    guaranteed = actual_days <= first_month_days         # 是否用保證天數

    coupon = float(principal) * float(annual_pct) * coupon_days / DAY_BASIS
    out.update({
        "base_date": base,
        "days": coupon_days,
        "coupon": round(coupon, 2),
        "total": round(float(principal) + coupon, 2),
        "guaranteed": guaranteed,
    })
    return out
