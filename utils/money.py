"""
多幣別金額處理 — 解析與格式化
規則: 純數字 = USD；有幣別標註則沿用，例如 "20000JPY"、"¥20000"、"NT$ 50,000"、"20000 twd"
"""
import re

# 支援的幣別代碼 (含常見別名 → 正規代碼)
_ALIAS = {
    "NTD": "TWD", "NT": "TWD", "RMB": "CNY", "JP": "JPY",
    "US": "USD", "USD": "USD", "JPY": "JPY", "TWD": "TWD", "HKD": "HKD",
    "CNY": "CNY", "EUR": "EUR", "GBP": "GBP", "AUD": "AUD", "SGD": "SGD",
    "KRW": "KRW", "THB": "THB", "CHF": "CHF", "CAD": "CAD", "NZD": "NZD",
}
_SYMBOLS = [
    ("NT$", "TWD"), ("HK$", "HKD"), ("US$", "USD"),
    ("$", "USD"), ("¥", "JPY"), ("￥", "JPY"), ("€", "EUR"),
    ("£", "GBP"), ("₩", "KRW"), ("฿", "THB"), ("元", "TWD"),
]
DEFAULT_CCY = "USD"


def parse_amount(value, default: str = DEFAULT_CCY):
    """回傳 (amount: float|None, currency: str)"""
    if value is None:
        return None, default
    if isinstance(value, bool):
        return None, default
    if isinstance(value, (int, float)):
        return float(value), default

    s = str(value).strip()
    if not s:
        return None, default

    cur = default
    up = s.upper()

    # 1) 幣別代碼 (前綴或後綴，如 20000JPY / JPY 20000)
    m = re.search(r"[A-Z]{2,4}", up)
    if m and m.group() in _ALIAS:
        cur = _ALIAS[m.group()]
        up = up.replace(m.group(), " ")

    # 2) 貨幣符號
    for sym, c in _SYMBOLS:
        if sym in s:
            cur = c
            up = up.replace(sym.upper(), " ")
            break

    # 3) 取出數字
    num = re.search(r"-?\d[\d,]*(\.\d+)?", up)
    if not num:
        return None, cur
    try:
        return float(num.group().replace(",", "")), cur
    except ValueError:
        return None, cur


def format_money(amount, currency: str = DEFAULT_CCY, decimals: int = 0) -> str:
    """USD 在前 (USD 20,000)；其他幣別在後 (20,000 JPY) — 符合常見金融寫法"""
    if amount is None:
        return "—"
    cur = (currency or DEFAULT_CCY).upper()
    n = f"{amount:,.{decimals}f}"
    return f"USD {n}" if cur == "USD" else f"{n} {cur}"
