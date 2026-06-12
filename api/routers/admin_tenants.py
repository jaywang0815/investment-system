"""平台管理 — 超級管理員建立租戶 (客戶/advisor) + 發送邀請。"""
import secrets
from fastapi import APIRouter, Depends, HTTPException
from ..deps import require_superadmin
from ..db import get_sb

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/tenants")
def list_tenants(_=Depends(require_superadmin)):
    sb = get_sb()
    tenants = sb.table("tenants").select("id,name,company_name,reporter,created_at").order("created_at").execute().data or []
    users = sb.table("app_users").select("tenant_id,email,active").execute().data or []
    try:
        invites = sb.table("invites").select("tenant_id,email,used").execute().data or []
    except Exception:
        invites = []
    by_tenant_users: dict = {}
    for u in users:
        by_tenant_users.setdefault(u["tenant_id"], []).append(u["email"])
    pending: dict = {}
    for iv in invites:
        if not iv.get("used"):
            pending.setdefault(iv["tenant_id"], []).append(iv["email"])
    out = []
    for t in tenants:
        out.append({
            "id": t["id"],
            "name": t.get("company_name") or t.get("name"),
            "reporter": t.get("reporter"),
            "users": by_tenant_users.get(t["id"], []),
            "pending_invites": pending.get(t["id"], []),
            "created_at": t.get("created_at"),
        })
    return {"tenants": out}


@router.post("/tenants")
def create_tenant(body: dict, _=Depends(require_superadmin)):
    """สร้าง tenant ใหม่ + invite (ลูกค้า/advisor ตั้งรหัสเอง)。"""
    company = (body.get("company_name") or "").strip()
    email = (body.get("email") or "").strip().lower()
    reporter = (body.get("reporter") or "").strip()
    if not company:
        raise HTTPException(status_code=422, detail="缺少公司名稱")
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="email 格式不正確")
    sb = get_sb()
    if sb.table("app_users").select("id").eq("email", email).execute().data:
        raise HTTPException(status_code=400, detail="此 email 已是使用者")

    t = sb.table("tenants").insert({
        "name": company, "company_name": company, "reporter": reporter or None,
    }).execute().data[0]

    token = secrets.token_urlsafe(24)
    try:
        sb.table("invites").insert({
            "token": token, "email": email, "tenant_id": t["id"],
            "company_name": company, "reporter": reporter or None,
        }).execute()
    except Exception:
        raise HTTPException(status_code=500, detail="invites 表不存在，請先執行 migration 06")

    return {"tenant_id": t["id"], "email": email, "invite_token": token,
            "invite_path": f"/invite/{token}"}


@router.post("/tenants/{tid}/invite")
def invite_user_to_tenant(tid: str, body: dict, _=Depends(require_superadmin)):
    """เชิญ user เข้า tenant ที่มีอยู่แล้ว (เห็นข้อมูลชุดเดิม ไม่สร้างใหม่)。"""
    email = (body.get("email") or "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="email 格式不正確")
    sb = get_sb()
    rows = sb.table("tenants").select("id,name,company_name,reporter").eq("id", tid).execute().data or []
    if not rows:
        raise HTTPException(status_code=404, detail="找不到此會員")
    t = rows[0]
    if sb.table("app_users").select("id").eq("email", email).execute().data:
        raise HTTPException(status_code=400, detail="此 email 已是使用者")
    token = secrets.token_urlsafe(24)
    try:
        sb.table("invites").insert({
            "token": token, "email": email, "tenant_id": tid,
            "company_name": t.get("company_name") or t.get("name"), "reporter": t.get("reporter"),
        }).execute()
    except Exception:
        raise HTTPException(status_code=500, detail="invites 表不存在，請先執行 migration 06")
    return {"tenant_id": tid, "email": email, "invite_token": token, "invite_path": f"/invite/{token}"}
