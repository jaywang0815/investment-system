"""
多租戶後台帳號驗證 (app_users)。
- 密碼以 pbkdf2_sha256 雜湊 (Python 標準庫，無需額外套件)
- authenticate() 回傳 user dict (含 tenant_id) 或 None
此模組為新增、獨立檔；尚未接入現有流程前，不影響線上系統。
"""
import os
import hmac
import base64
import hashlib

_ITER = 200_000


def hash_password(pw: str, iterations: int = _ITER) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, iterations)
    return f"pbkdf2${iterations}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        algo, iters, salt_b64, hash_b64 = stored.split("$")
        if algo != "pbkdf2":
            return False
        salt = base64.b64decode(salt_b64)
        dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, int(iters))
        return hmac.compare_digest(base64.b64encode(dk).decode(), hash_b64)
    except Exception:
        return False


def authenticate(sb, email: str, pw: str):
    """回傳 {id, email, tenant_id, role} 或 None。"""
    email = (email or "").strip().lower()
    if not email or not pw:
        return None
    try:
        rows = sb.table("app_users").select("*").eq("email", email).eq("active", True).execute().data or []
    except Exception:
        return None
    if not rows:
        return None
    u = rows[0]
    if verify_password(pw, u.get("password_hash", "")):
        return {"id": u["id"], "email": u["email"], "tenant_id": u["tenant_id"], "role": u.get("role", "admin")}
    return None


def create_user(sb, email: str, pw: str, tenant_id: str, role: str = "admin") -> dict:
    payload = {
        "email": email.strip().lower(),
        "password_hash": hash_password(pw),
        "tenant_id": tenant_id,
        "role": role,
    }
    return sb.table("app_users").insert(payload).execute().data[0]


def first_tenant_id(sb):
    rows = sb.table("tenants").select("id").order("created_at").limit(1).execute().data or []
    return rows[0]["id"] if rows else None
