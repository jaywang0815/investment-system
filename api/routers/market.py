"""行情 — 此租戶所有 SN 標的的即時報價 (yfinance)。前端每 ~15s 輪詢。"""
import unicodedata
from fastapi import APIRouter, Depends
from ..deps import repo
from ..db import Repo

router = APIRouter(prefix="/api/market", tags=["market"])


def _clean(t: str) -> str:
    return unicodedata.normalize("NFKC", str(t)).lstrip("$").strip().upper()


def _quote(ticker: str):
    """回傳 (price, prev_close)。失敗回 (None, None)。"""
    try:
        import yfinance as yf
        fi = yf.Ticker(ticker).fast_info
        price = float(fi.last_price) if fi.last_price else None
        prev = float(fi.previous_close) if getattr(fi, "previous_close", None) else None
        if price and not prev:
            h = yf.Ticker(ticker).history(period="5d")
            if len(h) >= 2:
                prev = float(h["Close"].iloc[-2])
        return price, prev
    except Exception:
        return None, None


@router.get("/quotes")
def quotes(r: Repo = Depends(repo)):
    sns = r.find("structured_notes", select="product_code,underlying_1,underlying_2,underlying_3,underlying_4,underlying_5", status="active")

    # ticker → 用到它的商品代號
    used: dict[str, list] = {}
    for sn in sns:
        for i in range(1, 6):
            t = sn.get(f"underlying_{i}")
            if isinstance(t, str) and t.strip():
                tk = _clean(t)
                used.setdefault(tk, [])
                if sn.get("product_code"):
                    used[tk].append(sn["product_code"])

    rows = []
    for tk in sorted(used.keys()):
        price, prev = _quote(tk)
        change = (price - prev) if (price is not None and prev) else None
        change_pct = (change / prev * 100) if (change is not None and prev) else None
        rows.append({
            "ticker": tk,
            "price": round(price, 2) if price is not None else None,
            "change": round(change, 2) if change is not None else None,
            "change_pct": round(change_pct, 2) if change_pct is not None else None,
            "in_products": len(used[tk]),
        })
    return {"quotes": rows}
