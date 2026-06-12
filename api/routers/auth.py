"""登入：email + 密碼 → 驗證 (utils.auth) → 簽發 JWT。+ 忘記密碼 (email reset)。"""
import secrets
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from ..db import get_sb
from ..security import create_token
from ..deps import current_user
from utils.auth import authenticate, hash_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(body: LoginIn):
    user = authenticate(get_sb(), body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    return {
        "token": create_token(user),
        "user": {"email": user["email"], "tenant_id": user["tenant_id"], "role": user["role"]},
    }


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return {"email": user.get("email"), "tenant_id": user.get("tenant_id"), "role": user.get("role")}


# ---------- 忘記密碼 (ผ่านอีเมล Resend; reuse invites เป็น reset token) ----------
@router.post("/forgot")
def forgot(body: dict):
    email = (body.get("email") or "").strip().lower()
    sb = get_sb()
    # ตอบ ok เสมอ (กัน email enumeration)
    if email:
        users = sb.table("app_users").select("id,tenant_id").eq("email", email).execute().data or []
        if users:
            token = secrets.token_urlsafe(24)
            try:
                sb.table("invites").insert({"token": token, "email": email,
                                            "tenant_id": users[0]["tenant_id"], "used": False}).execute()
                from utils.mailer import send_email, app_base_url
                url = f"{app_base_url()}/reset/{token}"
                send_email(email, "Justinvestment 重設密碼",
                           f'<div style="font-family:system-ui"><p>點此重設密碼（10 分鐘內有效）：</p>'
                           f'<p><a href="{url}">{url}</a></p></div>')
            except Exception:
                pass
    return {"ok": True}


@router.get("/reset/{token}")
def reset_info(token: str):
    sb = get_sb()
    rows = sb.table("invites").select("email,used").eq("token", token).eq("used", False).execute().data or []
    if not rows:
        raise HTTPException(status_code=400, detail="連結無效或已使用")
    return {"email": rows[0]["email"], "valid": True}


@router.post("/reset/{token}")
def reset(token: str, body: dict):
    pw = body.get("password") or ""
    if len(pw) < 6:
        raise HTTPException(status_code=422, detail="密碼至少 6 碼")
    sb = get_sb()
    rows = sb.table("invites").select("id,email").eq("token", token).eq("used", False).execute().data or []
    if not rows:
        raise HTTPException(status_code=400, detail="連結無效或已使用")
    email = rows[0]["email"]
    users = sb.table("app_users").select("id").eq("email", email).execute().data or []
    if not users:
        raise HTTPException(status_code=404, detail="找不到使用者")
    sb.table("app_users").update({"password_hash": hash_password(pw)}).eq("id", users[0]["id"]).execute()
    sb.table("invites").update({"used": True}).eq("id", rows[0]["id"]).execute()
    user = authenticate(sb, email, pw)
    return {"token": create_token(user),
            "user": {"email": user["email"], "tenant_id": user["tenant_id"], "role": user["role"]}}
