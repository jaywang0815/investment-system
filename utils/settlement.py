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


def detect_exit_date(observation_date, underlyings: list) -> dict:
    """
    依「收盤價」推算出場日 (worst-of autocall, sticky KO)
    規則 (客戶確認): 從比價日起，每隻標的找「收盤價 >= 期初 × KO%」首次發生日；
    出場日 = 所有標的中最晚的那個 KO 日 (即最後一隻 KO 當天)。
    任一標的至今未 KO → 未出場 (exit_date=None)。

    underlyings: [{"ticker","initial","ko_barrier"}]
    回傳: {"exit_date": date|None, "status": str, "stocks": [{ticker,ko_price,ko_date}]}
    """
    obs = _to_date(observation_date)
    if not obs:
        return {"exit_date": None, "status": "無比價日", "stocks": []}

    import unicodedata
    import yfinance as yf

    def _clean(t):
        return unicodedata.normalize("NFKC", str(t)).lstrip("$").strip().upper()

    stocks = []
    ko_dates = []
    all_ko = True
    for u in underlyings:
        tkr = _clean(u.get("ticker", ""))
        init = u.get("initial")
        ko = u.get("ko_barrier")
        if not tkr or not init or not ko:
            stocks.append({"ticker": tkr, "ko_price": None, "ko_date": None})
            all_ko = False
            continue
        ko_price = round(float(init) * float(ko), 4)
        ko_date = None
        try:
            hist = yf.Ticker(tkr).history(start=obs.isoformat())
            if hist is not None and not hist.empty:
                for ts, row in hist.iterrows():
                    c = row.get("Close")
                    if c is not None and float(c) >= ko_price:
                        ko_date = ts.date()
                        break
        except Exception:
            ko_date = None
        stocks.append({"ticker": tkr, "ko_price": round(ko_price, 2), "ko_date": ko_date})
        if ko_date is None:
            all_ko = False
        else:
            ko_dates.append(ko_date)

    if all_ko and ko_dates:
        return {"exit_date": max(ko_dates), "status": "已出場(推算)", "stocks": stocks}
    return {"exit_date": None, "status": "未出場", "stocks": stocks}
