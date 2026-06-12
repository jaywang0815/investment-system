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
                "time": (str(e.get("event_time"))[:5] if e.get("event_time") else None),
                "type": "自訂",
                "title": e.get("title"),
                "notes": e.get("notes"),
                "remind_offsets": e.get("remind_offsets") or "",
                "color": e.get("color"),
                "location": e.get("location"),
                "url": e.get("url"),
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


def _clean_time(v):
    """'HH:MM' → 'HH:MM' ; ว่าง/None → None (= all-day)。"""
    if not v:
        return None
    s = str(v).strip()
    return s[:5] if len(s) >= 4 else None


def _clean_offsets(v):
    """รับ list/str ของนาที → 'a,b' (เรียง, ไม่ซ้ำ)。"""
    if v is None:
        return "0"
    if isinstance(v, list):
        parts = v
    else:
        parts = str(v).split(",")
    nums = sorted({int(str(p).strip()) for p in parts if str(p).strip().lstrip("-").isdigit()})
    return ",".join(str(n) for n in nums)


@router.post("/events")
def create_event(body: dict, r: Repo = Depends(repo)):
    title = (body.get("title") or "").strip()
    d = _d(body.get("event_date"))
    if not title or not d:
        raise HTTPException(status_code=422, detail="缺少標題或日期")
    payload = {
        "title": title,
        "event_date": d.isoformat(),
        "event_time": _clean_time(body.get("event_time")),
        "notes": (body.get("notes") or "").strip() or None,
        "remind_offsets": _clean_offsets(body.get("remind_offsets")),
        "color": (body.get("color") or "").strip() or None,
        "location": (body.get("location") or "").strip() or None,
        "url": (body.get("url") or "").strip() or None,
    }
    try:
        return r.create("calendar_events", payload)
    except Exception:
        # เผื่อยังไม่ได้รัน SQL เพิ่มคอลัมน์ใหม่ (color/location/url) → ลองใหม่โดยไม่มีคอลัมน์ optional
        for k in ("color", "location", "url"):
            payload.pop(k, None)
        try:
            return r.create("calendar_events", payload)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"建立失敗（請先在 Supabase 執行 SQL 07）: {getattr(e, 'message', None) or e}")


@router.patch("/events/{eid}")
def update_event(eid: str, body: dict, r: Repo = Depends(repo)):
    payload = {}
    for k in ("title", "notes", "done", "color", "location", "url"):
        if k in body:
            payload[k] = body[k]
    if "event_date" in body:
        d = _d(body["event_date"])
        if not d:
            raise HTTPException(status_code=422, detail="日期格式錯誤")
        payload["event_date"] = d.isoformat()
    if "event_time" in body:
        payload["event_time"] = _clean_time(body["event_time"])
    if "remind_offsets" in body:
        payload["remind_offsets"] = _clean_offsets(body["remind_offsets"])
    try:
        r.update("calendar_events", eid, payload)
    except Exception:
        for k in ("color", "location", "url"):
            payload.pop(k, None)
        r.update("calendar_events", eid, payload)
    return {"updated": eid}


@router.delete("/events/{eid}")
def delete_event(eid: str, r: Repo = Depends(repo)):
    r.delete("calendar_events", eid)
    return {"deleted": eid}
