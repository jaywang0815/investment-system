"""事件行事曆 — 此租戶所有 SN 的關鍵日期 (比價日 / 出場日)，含倒數天數。"""
from datetime import date
from fastapi import APIRouter, Depends
from ..deps import repo
from ..db import Repo

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


def _d(v):
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None


@router.get("/events")
def events(r: Repo = Depends(repo)):
    # ไม่ select category ตรงๆ (เผื่อยังไม่ได้รัน SQL เพิ่มคอลัมน์) — ใช้ * แล้ว .get default
    sns = r.list("structured_notes", select="*")
    today = date.today()
    out = []
    for sn in sns:
        for field, label in (("observation_date", "比價日"), ("exit_date", "出場日")):
            d = _d(sn.get(field))
            if not d:
                continue
            out.append({
                "date": d.isoformat(),
                "type": label,
                "product_code": sn.get("product_code"),
                "category": sn.get("category") or "SN",
                "days_until": (d - today).days,
            })
    out.sort(key=lambda e: e["date"])
    upcoming = [e for e in out if e["days_until"] >= 0]
    past = [e for e in out if e["days_until"] < 0]
    return {"upcoming": upcoming, "past": past[-30:]}
