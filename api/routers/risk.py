"""KO/KI Risk Radar — 此租戶每檔有效 SN 距離 KO/KI 的狀態 (reuse analyze_sn_status)。"""
from fastapi import APIRouter, Depends
from ..deps import repo
from ..db import Repo

router = APIRouter(prefix="/api/risk", tags=["risk"])

_ORDER = {"ki_triggered": 0, "ki_risk": 1, "ko_triggered": 2, "ko_risk": 3, "normal": 4, "unknown": 5}


@router.get("")
def risk(r: Repo = Depends(repo)):
    from utils.stock_prices import get_prices, analyze_sn_status

    sns = r.find("structured_notes", status="active")
    tickers = set()
    for sn in sns:
        for i in range(1, 6):
            t = sn.get(f"underlying_{i}")
            if isinstance(t, str) and t.strip():
                tickers.add(t)
    prices = get_prices(list(tickers)) if tickers else {}

    items = []
    for sn in sns:
        a = analyze_sn_status(sn, prices)
        dets = a.get("details", [])
        worst = None
        ko_gaps, ki_gaps = [], []
        for d in dets:
            cur = d.get("current_price")
            cp = d.get("change_pct")
            if cp is not None and (worst is None or cp < worst.get("change_pct", 1e9)):
                worst = d
            if cur and d.get("ko_price"):
                ko_gaps.append(round((d["ko_price"] - cur) / cur * 100, 2))
            if cur and d.get("ki_price"):
                ki_gaps.append(round((cur - d["ki_price"]) / cur * 100, 2))
        items.append({
            "product_code": sn.get("product_code"),
            "status": a.get("overall_status"),
            "label": a.get("status_label"),
            "observation_date": (sn.get("observation_date") or "")[:10] or None,
            "underlyings": [d["ticker"] for d in dets],
            "worst_ticker": worst.get("ticker") if worst else None,
            "worst_change_pct": worst.get("change_pct") if worst else None,
            "ko_gap_pct": min(ko_gaps) if ko_gaps else None,   # % ที่ต้องขึ้นถึง KO (น้อย=ใกล้ autocall)
            "ki_gap_pct": min(ki_gaps) if ki_gaps else None,   # buffer เหนือ KI (น้อย=เสี่ยง)
        })

    items.sort(key=lambda x: (_ORDER.get(x["status"], 9),
                              x["ki_gap_pct"] if x["ki_gap_pct"] is not None else 9999))
    counts = {}
    for it in items:
        counts[it["status"]] = counts.get(it["status"], 0) + 1
    return {"items": items, "counts": counts}
