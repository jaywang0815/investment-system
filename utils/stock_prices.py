"""
股票即時價格模組 - 使用 Yahoo Finance
"""
import streamlit as st
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
    underlyings = get_sn_underlyings(sn)
    ko_barrier = sn.get("ko_barrier")   # 例如 1.0 = 100%
    ki_barrier = sn.get("ki_barrier")   # 例如 0.5 = 50%
    strike_pct = sn.get("strike_pct")   # 例如 0.80 = 80%

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
