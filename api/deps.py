"""FastAPI 相依：從 Authorization: Bearer <jwt> 取出登入者 + 建立租戶限定的 Repo。"""
from fastapi import Header, HTTPException, Depends
from .security import decode_token
from .db import get_sb, Repo


def current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    try:
        return decode_token(authorization.split(" ", 1)[1])
    except Exception:
        raise HTTPException(status_code=401, detail="invalid or expired token")


def repo(user: dict = Depends(current_user),
         x_act_as_tenant: str = Header(None)) -> Repo:
    """สร้าง Repo จำกัด tenant ของผู้ login。
    superadmin ส่ง header X-Act-As-Tenant ได้ เพื่อ 'เข้าไปตรวจสอบบ้าน' ของ tenant อื่น (เวลามีปัญหา)。
    คนทั่วไปส่ง header นี้มาก็ถูกเพิกเฉย (ใช้ tenant ตัวเองเสมอ)。"""
    tid = user["tenant_id"]
    if x_act_as_tenant and user.get("role") == "superadmin":
        tid = x_act_as_tenant
    return Repo(get_sb(), tid)


def require_superadmin(user: dict = Depends(current_user)) -> dict:
    """เฉพาะเจ้าของแพลตฟอร์ม (สร้าง/เชิญ tenant)。"""
    if user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="需要平台管理員權限")
    return user
