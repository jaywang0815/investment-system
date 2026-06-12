"""邀請開通 (公開, 無需登入) — 新客戶/advisor 開連結自設密碼。"""
from fastapi import APIRouter, HTTPException
from ..db import get_sb
from ..security import create_token

router = APIRouter(prefix="/api/invite", tags=["invite"])


def _valid_invite(sb, token: str):
    try:
        rows = sb.table("invites").select("*").eq("token", token).eq("used", False).execute().data or []
    except Exception:
        return None
    return rows[0] if rows else None


@router.get("/{token}")
def get_invite(token: str):
    sb = get_sb()
    inv = _valid_invite(sb, token)
    if not inv:
        raise HTTPException(status_code=404, detail="邀請連結無效或已使用")
    return {"email": inv["email"], "company_name": inv.get("company_name"), "valid": True}


@router.post("/{token}/accept")
def accept(token: str, body: dict):
    sb = get_sb()
    inv = _valid_invite(sb, token)
    if not inv:
        raise HTTPException(status_code=400, detail="邀請連結無效或已使用")
    pw = body.get("password") or ""
    if len(pw) < 6:
        raise HTTPException(status_code=422, detail="密碼至少 6 碼")

    from utils.auth import create_user, authenticate
    if sb.table("app_users").select("id").eq("email", inv["email"]).execute().data:
        raise HTTPException(status_code=400, detail="此帳號已註冊，請直接登入")

    create_user(sb, inv["email"], pw, inv["tenant_id"], role="admin")
    sb.table("invites").update({"used": True}).eq("id", inv["id"]).execute()

    user = authenticate(sb, inv["email"], pw)  # auto-login
    return {
        "token": create_token(user),
        "user": {"email": user["email"], "tenant_id": user["tenant_id"], "role": user["role"]},
    }
