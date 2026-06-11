"""登入：email + 密碼 → 驗證 (utils.auth) → 簽發 JWT (含 tenant_id)。"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from ..db import get_sb
from ..security import create_token
from ..deps import current_user
from utils.auth import authenticate

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
