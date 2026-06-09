"""
匯入前資料健檢 - 在寫入 DB 前抓出常見錯誤

檢查項目:
  1. 期初價 vs 當日市場價   抓「188.16 寫錯」這類 (用 yfinance 抓交易日收盤對比)
  2. ticker 是否查得到報價   抓打錯/全形/已下市
  3. 同一檔 SN 期初價重複     抓「複製到隔壁欄」
  4. barrier 是否在合理區間   ko 0.85-1.30 / strike 0.40-1.00 / ki 0.30-0.90
  5. 必填欄位是否齊全
  6. 客戶姓名能否對到既有客戶  抓遮罩名/暱稱造成的重複客戶

回傳 list[dict]:
  {"level": "error"|"warn", "code": <SN代號>, "field": <欄位>, "msg": <說明>}
"""
import unicodedata
from utils.customer_match import match_customer

PRICE_TOL = 0.15      # 期初價與市場價偏差超過 15% → 警告
KO_RANGE     = (0.85, 1.30)
STRIKE_RANGE = (0.40, 1.00)
KI_RANGE     = (0.30, 0.90)


def _clean(t: str) -> str:
    return unicodedata.normalize("NFKC", str(t)).lstrip("$").strip().upper()


def _market_price_on(ticker: str, trade_date: str):
    """抓交易日(或最接近的交易日)收盤價。失敗回 None。"""
    try:
        import yfinance as yf
        from datetime import datetime, timedelta
        d = datetime.strptime(str(trade_date)[:10], "%Y-%m-%d")
        hist = yf.Ticker(_clean(ticker)).history(
            start=d.strftime("%Y-%m-%d"),
            end=(d + timedelta(days=6)).strftime("%Y-%m-%d"),
        )
        if hist is None or hist.empty:
            return None
        return float(hist["Close"].iloc[0])
    except Exception:
        return None


def validate_parsed(parsed: dict, existing_customer_names: list,
                    check_prices: bool = True) -> list:
    issues = []
    official = list(existing_customer_names or [])

    for month, sns in (parsed.get("sn_by_month") or {}).items():
        for sn in sns:
            code = sn.get("product_code") or "(無代號)"

            # 5) 必填欄位
            if not sn.get("product_code"):
                issues.append({"level": "error", "code": code, "field": "代號", "msg": "缺少商品代號"})
            if not sn.get("observation_date"):
                issues.append({"level": "warn", "code": code, "field": "比價日", "msg": "缺少比價日"})

            # 4) barrier 區間
            ko = sn.get("ko_barrier"); ki = sn.get("ki_barrier"); strike = sn.get("strike_pct")
            if ko is not None and not (KO_RANGE[0] <= ko <= KO_RANGE[1]):
                issues.append({"level": "warn", "code": code, "field": "KO",
                               "msg": f"KO={ko*100:.0f}% 不在常見區間 {KO_RANGE[0]*100:.0f}-{KO_RANGE[1]*100:.0f}%，請確認"})
            if strike is not None and not (STRIKE_RANGE[0] <= strike <= STRIKE_RANGE[1]):
                issues.append({"level": "warn", "code": code, "field": "執行價",
                               "msg": f"執行價={strike*100:.0f}% 不在常見區間，請確認"})
            if ki is not None and not (KI_RANGE[0] <= ki <= KI_RANGE[1]):
                issues.append({"level": "warn", "code": code, "field": "KI",
                               "msg": f"KI={ki*100:.0f}% 不在常見區間，請確認"})

            # 標的 + 期初價
            seen_prices = {}
            for i in range(1, 6):
                t = sn.get(f"underlying_{i}")
                init = sn.get(f"initial_price_{i}")
                if not t:
                    continue
                tk = _clean(t)

                if not init or init <= 0:
                    issues.append({"level": "error", "code": code, "field": tk,
                                   "msg": f"{tk} 缺少期初價"})
                    continue

                # 3) 同檔重複期初價
                if init in seen_prices:
                    issues.append({"level": "warn", "code": code, "field": tk,
                                   "msg": f"{tk} 期初價 {init} 與 {seen_prices[init]} 相同，疑似複製錯欄"})
                seen_prices[init] = tk

                # 2) ticker 查得到報價嗎 + 1) 價格對比
                if check_prices:
                    mkt = _market_price_on(t, sn.get("trade_date"))
                    if mkt is None:
                        # 沒交易日就用近期價試
                        from utils.stock_prices import get_price  # lazy
                        mkt = get_price(tk)
                        if mkt is None:
                            issues.append({"level": "error", "code": code, "field": tk,
                                           "msg": f"{tk} 查不到報價 (代號錯誤/已下市?)"})
                            continue
                    dev = abs(init - mkt) / mkt
                    if dev > PRICE_TOL:
                        issues.append({"level": "warn", "code": code, "field": tk,
                                       "msg": f"{tk} 期初價 {init} 與市場價約 {mkt:.2f} 偏差 {dev*100:.0f}%，疑似填錯"})

            # 6) 客戶姓名對應
            for inv in sn.get("investments", []):
                cname = inv.get("customer_name", "")
                r = match_customer(cname, official)
                if r["status"] in ("nickname", "ambiguous", "none"):
                    hint = ("可能: " + "、".join(r["options"][:4])) if r["options"] else "查無相近全名"
                    issues.append({"level": "warn", "code": code, "field": "客戶",
                                   "msg": f"「{cname}」對不到開戶全名 → 將建立新客戶 ({hint})"})

    return issues
