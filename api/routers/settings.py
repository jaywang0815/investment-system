"""租戶設定 — 報表品牌 (公司名稱 / 報告人 / logo)，tenant-scoped。"""
import re as _re
from fastapi import APIRouter, Depends
from ..deps import repo
from ..db import Repo

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/branding")
def get_branding(r: Repo = Depends(repo)):
    """อ่านแบรนด์ของ tenant ที่ login (fallback default ถ้ายังไม่ตั้ง/ยังไม่รัน SQL)。"""
    t = {}
    for cols in ("name,company_name,reporter,logo", "name,company_name,reporter", "name"):
        try:
            rows = r.sb.table("tenants").select(cols).eq("id", r.tenant_id).execute().data
            t = rows[0] if rows else {}
            break
        except Exception:
            continue
    return {
        "name": t.get("name"),
        "company_name": t.get("company_name") or "統一證券",
        "reporter": t.get("reporter") or "秦聖鈞",
        "logo": t.get("logo"),
    }


def _safe_update(r: Repo, payload: dict):
    """update โดยตัดคอลัมน์ที่ยังไม่มี (เผื่อ migration ยังไม่รัน)。"""
    p = dict(payload)
    for _ in range(6):
        try:
            r.sb.table("tenants").update(p).eq("id", r.tenant_id).execute()
            return
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            m = (_re.search(r"column \S*?\.?(\w+) does not exist", msg)
                 or _re.search(r"Could not find the '(\w+)' column", msg))
            if not m or m.group(1) not in p:
                raise
            p.pop(m.group(1), None)


@router.put("/branding")
def update_branding(body: dict, r: Repo = Depends(repo)):
    """แก้ชื่อบริษัท / 報告人 / logo ของ tenant ตัวเอง。logo = data URL หรือ null (ลบ)。"""
    payload = {
        "company_name": (body.get("company_name") or "").strip() or None,
        "reporter": (body.get("reporter") or "").strip() or None,
    }
    # logo: ส่งมาเมื่อต้องการเปลี่ยน/ลบ (key มีใน body)
    if "logo" in body:
        logo = body.get("logo")
        payload["logo"] = logo if (isinstance(logo, str) and logo.strip()) else None
    _safe_update(r, payload)
    return {"ok": True}
