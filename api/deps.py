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


def repo(user: dict = Depends(current_user)) -> Repo:
    return Repo(get_sb(), user["tenant_id"])
