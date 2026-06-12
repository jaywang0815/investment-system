"""事件行事曆 — SN 關鍵日期 (比價日/出場日) + 顧問自訂事件 (含 LINE 提醒)。"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
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
    today = date.today()
    out = []

    # SN 關鍵日期 (比價/出場) — แก้ไม่ได้ (มาจากข้อมูลสินค้า)
    for sn in r.list("structured_notes", select="*"):
        for field, label in (("observation_date", "比價日"), ("exit_date", "出場日")):
            d = _d(sn.get(field))
            if not d:
                continue
            out.append({
                "kind": "sn",
                "date": d.isoformat(),
                "type": label,
                "title": f"{sn.get('product_code')} {label}",
                "product_code": sn.get("product_code"),
                "category": sn.get("category") or "SN",
                "days_until": (d - today).days,
            })

    # 顧問自訂事件 (แก้/ลบได้) — เผื่อยังไม่ได้รัน SQL 07 ก็ไม่พัง
    try:
        for e in r.list("calendar_events", order="event_date"):
            d = _d(e.get("event_date"))
            if not d:
                continue
            out.append({
                "kind": "custom",
                "id": e["id"],
                "date": d.isoformat(),
                "type": "自訂",
                "title": e.get("title"),
                "notes": e.get("notes"),
                "remind_1day": e.get("remind_1day"),
                "remind_sameday": e.get("remind_sameday"),
                "done": e.get("done"),
                "days_until": (d - today).days,
            })
    except Exception:
        pass

    out.sort(key=lambda e: e["date"])
    return {
        "upcoming": [e for e in out if e["days_until"] >= 0],
        "past": [e for e in out if e["days_until"] < 0][-30:],
    }


@router.post("/events")
def create_event(body: dict, r: Repo = Depends(repo)):
    title = (body.get("title") or "").strip()
    d = _d(body.get("event_date"))
    if not title or not d:
        raise HTTPException(status_code=422, detail="缺少標題或日期")
    payload = {
        "title": title,
        "event_date": d.isoformat(),
        "notes": (body.get("notes") or "").strip() or None,
        "remind_1day": bool(body.get("remind_1day", True)),
        "remind_sameday": bool(body.get("remind_sameday", True)),
    }
    try:
        return r.create("calendar_events", payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"建立失敗（請先在 Supabase 執行 SQL 07）: {getattr(e, 'message', None) or e}")


@router.patch("/events/{eid}")
def update_event(eid: str, body: dict, r: Repo = Depends(repo)):
    payload = {k: body[k] for k in ("title", "event_date", "notes", "remind_1day", "remind_sameday", "done") if k in body}
    if "event_date" in payload:
        d = _d(payload["event_date"])
        if not d:
            raise HTTPException(status_code=422, detail="日期格式錯誤")
        payload["event_date"] = d.isoformat()
    r.update("calendar_events", eid, payload)
    return {"updated": eid}


@router.delete("/events/{eid}")
def delete_event(eid: str, r: Repo = Depends(repo)):
    r.delete("calendar_events", eid)
    return {"deleted": eid}
