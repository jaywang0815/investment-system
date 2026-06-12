"""租戶設定 — 報表品牌 (公司名稱 / 報告人)，tenant-scoped。"""
from fastapi import APIRouter, Depends
from ..deps import repo
from ..db import Repo

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/branding")
def get_branding(r: Repo = Depends(repo)):
    """อ่านแบรนด์ของ tenant ที่ login (fallback ค่า default ถ้ายังไม่ตั้ง/ยังไม่รัน SQL)。"""
    t = {}
    try:
        rows = r.sb.table("tenants").select("name,company_name,reporter").eq("id", r.tenant_id).execute().data
        t = rows[0] if rows else {}
    except Exception:
        # คอลัมน์ยังไม่มี (ยังไม่รัน migration) → ใช้ default
        try:
            rows = r.sb.table("tenants").select("name").eq("id", r.tenant_id).execute().data
            t = rows[0] if rows else {}
        except Exception:
            t = {}
    return {
        "name": t.get("name"),
        "company_name": t.get("company_name") or "統一證券",
        "reporter": t.get("reporter") or "秦聖鈞",
    }


@router.put("/branding")
def update_branding(body: dict, r: Repo = Depends(repo)):
    """แก้ชื่อบริษัท / 報告人 ของ tenant ตัวเอง。"""
    payload = {
        "company_name": (body.get("company_name") or "").strip() or None,
        "reporter": (body.get("reporter") or "").strip() or None,
    }
    r.sb.table("tenants").update(payload).eq("id", r.tenant_id).execute()
    return {"ok": True, **payload}
