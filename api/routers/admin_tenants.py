"""平台管理 — 超級管理員建立租戶 (客戶/advisor) + 發送邀請。"""
import secrets
from fastapi import APIRouter, Depends, HTTPException
from ..deps import require_superadmin
from ..db import get_sb

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/tenants")
def list_tenants(user=Depends(require_superadmin)):
    """รายชื่อ "รายคน" + บทบาท：Owner(พี่) / Co-worker(tenant เดียวกัน) / Member(ลูกค้าจ่ายเงิน คนละ tenant)。"""
    sb = get_sb()
    my_tid = user.get("tenant_id")
    tenants = {t["id"]: (t.get("company_name") or t.get("name"))
               for t in (sb.table("tenants").select("id,name,company_name").execute().data or [])}
    users = sb.table("app_users").select("id,email,tenant_id,role,active").execute().data or []
    try:
        invites = sb.table("invites").select("token,email,tenant_id,used").execute().data or []
    except Exception:
        invites = []

    def role_of(tid, is_super=False):
        if is_super:
            return "owner"
        return "coworker" if tid == my_tid else "member"

    people = []
    for u in users:
        is_super = u.get("role") == "superadmin"
        people.append({
            "email": u["email"],
            "role": role_of(u["tenant_id"], is_super),
            "status": "active" if u.get("active", True) else "disabled",
            "tenant_id": u["tenant_id"],
            "company": tenants.get(u["tenant_id"]),
            "user_id": u["id"],
            "invite_path": None,
        })
    for iv in invites:
        if iv.get("used"):
            continue
        people.append({
            "email": iv["email"],
            "role": role_of(iv["tenant_id"]),
            "status": "pending",
            "tenant_id": iv["tenant_id"],
            "company": tenants.get(iv["tenant_id"]),
            "user_id": None,
            "invite_path": f"/invite/{iv['token']}",
        })

    rank = {"owner": 0, "coworker": 1, "member": 2}
    people.sort(key=lambda p: (rank.get(p["role"], 9), 0 if p["status"] == "active" else 1, p["email"]))
    return {"people": people, "my_tenant_id": my_tid}


def _existing_pending(sb, email, tid=None):
    """คืน token ของคำเชิญที่ยังไม่ใช้สำหรับ email นี้ (กันสร้างซ้ำ)。"""
    try:
        q = sb.table("invites").select("token,tenant_id,used").eq("email", email).eq("used", False)
        rows = q.execute().data or []
    except Exception:
        return None
    if tid is not None:
        rows = [x for x in rows if x.get("tenant_id") == tid]
    return rows[0]["token"] if rows else None


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
    if _existing_pending(sb, email):
        raise HTTPException(status_code=400, detail="此 email 已有待開通的邀請")

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


# 租戶資料表 (依 FK 依賴排序：子表先刪，最後刪 tenants 本身)
_TENANT_TABLES = [
    "alerts", "investments", "daily_prices", "structured_notes",
    "customers", "articles", "app_settings", "invites", "app_users",
]


@router.delete("/tenants/{tid}")
def delete_tenant(tid: str, user=Depends(require_superadmin)):
    """刪除整個會員 (含其所有資料)。不可刪除自己所屬租戶。"""
    if tid == user.get("tenant_id"):
        raise HTTPException(status_code=400, detail="不能刪除自己所屬的會員")
    sb = get_sb()
    rows = sb.table("tenants").select("id").eq("id", tid).execute().data or []
    if not rows:
        raise HTTPException(status_code=404, detail="找不到此會員")
    for tbl in _TENANT_TABLES:
        try:
            sb.table(tbl).delete().eq("tenant_id", tid).execute()
        except Exception:
            pass  # 表不存在或無此欄位 → 略過
    sb.table("tenants").delete().eq("id", tid).execute()
    return {"deleted": tid}


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
    # กันเชิญซ้ำ → ใช้ลิงก์เดิม
    token = _existing_pending(sb, email, tid)
    if not token:
        token = secrets.token_urlsafe(24)
        try:
            sb.table("invites").insert({
                "token": token, "email": email, "tenant_id": tid,
                "company_name": t.get("company_name") or t.get("name"), "reporter": t.get("reporter"),
            }).execute()
        except Exception:
            raise HTTPException(status_code=500, detail="invites 表不存在，請先執行 migration 06")
    return {"tenant_id": tid, "email": email, "invite_token": token, "invite_path": f"/invite/{token}"}


@router.delete("/invites")
def revoke_invite(email: str, user=Depends(require_superadmin)):
    """ยกเลิกคำเชิญที่ยังไม่เปิดใช้ (ลบออกจาก 待開通)。"""
    sb = get_sb()
    em = (email or "").strip().lower()
    try:
        sb.table("invites").delete().eq("email", em).eq("used", False).execute()
    except Exception:
        pass
    return {"revoked": em}
