"""
股票即時價格模組 - 使用 Yahoo Finance
"""
try:
    import streamlit as st  # Streamlit app context → 真的快取
except Exception:           # API (Render) 沒裝 streamlit → no-op 裝飾器
    class _NoCacheST:
        @staticmethod
        def cache_data(*dargs, **dkwargs):
            if dargs and callable(dargs[0]) and not dkwargs:
                return dargs[0]
            def deco(fn):
                return fn
            return deco
    st = _NoCacheST()
import yfinance as yf
import unicodedata
from typing import Optional
from datetime import datetime, date
import pandas as pd


def clean_ticker(t: str) -> str:
    """全形 → 半形, 去除 $ 前綴 (DB 內 ticker 可能含全形字或 $)"""
    return unicodedata.normalize("NFKC", str(t)).lstrip("$").strip().upper()


@st.cache_data(ttl=300)  # 快取 5 分鐘
def get_price(ticker: str) -> Optional[float]:
    """取得單一股票現價"""
    try:
        ticker = clean_ticker(ticker)
        stock = yf.Ticker(ticker)
        info = stock.fast_info
        price = info.last_price
        return round(float(price), 2) if price else None
    except Exception:
        return None

_BASE_TICKERS = {
    "NVDA","TSLA","TSM","ANET","AMD","INTC","AVGO","MSFT","ORCL","MU","GOOG","GOOGL",
    "CRCL","LITE","COHR","QQQ","SPY","SMH","SOXX","IBB","AAPL","AMZN","META","NFLX",
}


@st.cache_data(ttl=86400)  # 一天刷新一次
def get_symbol_universe() -> list:
    """美股 + ETF 全部代號清單 (NASDAQ Trader symbol directory)，供下拉選擇。
    連線失敗時回傳常用代號。"""
    import urllib.request
    syms = set(_BASE_TICKERS)
    # (url, symbol_col_index, test_issue_col_index)
    sources = [
        ("https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt", 0, 3),
        ("https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt", 0, 6),
    ]
    for url, si, ti in sources:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                text = resp.read().decode("utf-8", "ignore")
            for line in text.splitlines()[1:]:
                if line.startswith("File Creation Time"):
                    continue
                parts = line.split("|")
                if len(parts) <= max(si, ti):
                    continue
                sym = parts[si].strip().upper()
                if parts[ti].strip() == "Y":          # 跳過 Test Issue
                    continue
                if sym and sym.isalpha() and len(sym) <= 5:
                    syms.add(sym)
        except Exception:
            pass
    return sorted(syms)


@st.cache_data(ttl=3600)
def get_price_on(ticker: str, trade_date: str) -> Optional[float]:
    """取得某交易日(或最接近的下一個交易日)的收盤價 — 用於自動帶入期初價"""
    try:
        from datetime import datetime, timedelta
        t = clean_ticker(ticker)
        d = datetime.strptime(str(trade_date)[:10], "%Y-%m-%d")
        hist = yf.Ticker(t).history(
            start=d.strftime("%Y-%m-%d"),
            end=(d + timedelta(days=6)).strftime("%Y-%m-%d"),
        )
        if hist is None or hist.empty:
            return None
        return round(float(hist["Close"].iloc[0]), 2)
    except Exception:
        return None


@st.cache_data(ttl=300)
def get_prices(tickers: list) -> dict:
    """批次取得多個股票現價"""
    tickers = [clean_ticker(t) for t in tickers if t and isinstance(t, str)]
    prices = {}
    if not tickers:
        return prices
    try:
        data = yf.download(tickers, period="1d", progress=False, auto_adjust=True)
        if len(tickers) == 1:
            ticker = tickers[0]
            if not data.empty and "Close" in data.columns:
                prices[ticker] = round(float(data["Close"].iloc[-1]), 2)
        else:
            if not data.empty and "Close" in data.columns:
                for ticker in tickers:
                    try:
                        prices[ticker] = round(float(data["Close"][ticker].iloc[-1]), 2)
                    except:
                        prices[ticker] = get_price(ticker)
    except Exception:
        for ticker in tickers:
            prices[ticker] = get_price(ticker)
    return prices

def get_sn_underlyings(sn: dict) -> list:
    """取得 SN 商品的所有標的股票清單"""
    underlyings = []
    for i in range(1, 6):
        ticker = sn.get(f"underlying_{i}")
        initial_price = sn.get(f"initial_price_{i}")
        if ticker and isinstance(ticker, str) and ticker.strip():
            underlyings.append({
                "ticker": clean_ticker(ticker),
                "initial_price": float(initial_price) if initial_price else None
            })
    return underlyings

def analyze_sn_status(sn: dict, current_prices: dict) -> dict:
    """
    分析 SN 商品目前狀態
    回傳: 各標的詳細狀況 + 整體評估
    """
    def _f(v):
        # Supabase NUMERIC 有時回傳字串/Decimal → 一律轉 float，避免 "str * float" TypeError
        try:
            return float(v) if v is not None and v != "" else None
        except (TypeError, ValueError):
            return None

    underlyings = get_sn_underlyings(sn)
    ko_barrier = _f(sn.get("ko_barrier"))   # 例如 1.0 = 100%
    ki_barrier = _f(sn.get("ki_barrier"))   # 例如 0.5 = 50%
    strike_pct = _f(sn.get("strike_pct"))   # 例如 0.80 = 80%

    details = []
    worst_perf = None

    for u in underlyings:
        ticker = u["ticker"]
        initial = u["initial_price"]
        current = current_prices.get(ticker)

        detail = {
            "ticker": ticker,
            "initial_price": initial,
            "current_price": current,
            "performance": None,
            "change_pct": None,
            "ko_price": round(initial * ko_barrier, 2) if (initial and ko_barrier) else None,
            "ki_price": round(initial * ki_barrier, 2) if (initial and ki_barrier) else None,
            "strike_price": round(initial * strike_pct, 2) if (initial and strike_pct) else None,
            "ko_status": "❓",
            "ki_status": "❓",
            "overall": "unknown",
        }

        if current and initial and initial > 0:
            perf = current / initial  # 1.05 = 上漲5%
            change = (perf - 1) * 100
            detail["performance"] = round(perf, 4)
            detail["change_pct"] = round(change, 2)

            # KO 狀態判斷
            if ko_barrier:
                if perf >= ko_barrier:
                    detail["ko_status"] = "🟢 已達KO"
                    detail["overall"] = "ko_triggered"
                elif perf >= ko_barrier * 0.97:
                    detail["ko_status"] = "🟡 接近KO"
                    detail["overall"] = "ko_risk"
                else:
                    detail["ko_status"] = "⚪ 未達KO"
                    detail["overall"] = "normal"
            else:
                detail["ko_status"] = "－"

            # KI 狀態判斷
            if ki_barrier:
                if perf <= ki_barrier:
                    detail["ki_status"] = "🔴 KI觸發!"
                    detail["overall"] = "ki_triggered"
                elif perf <= ki_barrier * 1.15:
                    detail["ki_status"] = "🟠 接近KI"
                    if detail["overall"] != "ki_triggered":
                        detail["overall"] = "ki_risk"
                else:
                    detail["ki_status"] = "✅ 安全"
            else:
                detail["ki_status"] = "－"

            # 追蹤最差表現 (Worst-Of 結構)
            if worst_perf is None or perf < worst_perf:
                worst_perf = perf

        details.append(detail)

    # 整體狀態 (以最差表現股票為準)
    overall_status = "normal"
    if worst_perf is not None:
        if ko_barrier and worst_perf >= ko_barrier:
            overall_status = "ko_triggered"
        elif ki_barrier and worst_perf <= ki_barrier:
            overall_status = "ki_triggered"
        elif ki_barrier and worst_perf <= ki_barrier * 1.15:
            overall_status = "ki_risk"
        elif ko_barrier and worst_perf >= ko_barrier * 0.97:
            overall_status = "ko_risk"

    status_labels = {
        "ko_triggered": ("🟢", "KO 觸發 - 即將提前贖回"),
        "ko_risk":      ("🟡", "接近 KO 水位"),
        "ki_triggered": ("🔴", "KI 觸發 - 注意風險"),
        "ki_risk":      ("🟠", "接近 KI 水位"),
        "normal":       ("✅", "正常"),
        "unknown":      ("❓", "無法取得價格"),
    }
    emoji, label = status_labels.get(overall_status, ("❓", "未知"))

    return {
        "overall_status": overall_status,
        "status_emoji": emoji,
        "status_label": label,
        "worst_performance": worst_perf,
        "details": details,
    }

def get_all_tickers_for_active_sns(sns_df: pd.DataFrame) -> list:
    """取得所有有效 SN 商品用到的股票代號"""
    tickers = set()
    for _, row in sns_df.iterrows():
        for i in range(1, 6):
            t = row.get(f"underlying_{i}")
            if t and isinstance(t, str) and t.strip():
                tickers.add(clean_ticker(t))
    return list(tickers)
