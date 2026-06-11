"""JWT 簽發/驗證 (HS256)。Token 內含 tenant_id → 之後所有查詢據此限定範圍。"""
import os
import datetime
import jwt

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-prod")
ALGO = "HS256"
TTL_DAYS = int(os.environ.get("JWT_TTL_DAYS", "7"))


def create_token(user: dict) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": user["id"],
        "tenant_id": user["tenant_id"],
        "email": user["email"],
        "role": user.get("role", "admin"),
        "iat": now,
        "exp": now + datetime.timedelta(days=TTL_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGO)


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[ALGO])
