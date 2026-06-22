"""租戶設定 — 報表品牌 + 修改密碼 + LINE 管理員 + LINE Bot 憑證，tenant-scoped。"""
import os
import re as _re
from fastapi import APIRouter, Depends, HTTPException
from ..deps import repo, current_user
from ..db import Repo, get_sb

router = APIRouter(prefix="/api/settings", tags=["settings"])

# โฮสต์ของ LINE bot service (คนละ service กับ api นี้) — ใช้สร้าง webhook URL ให้ advisor ก๊อปไปตั้ง
_BOT_BASE_URL = os.environ.get("LINE_BOT_BASE_URL", "https://investment-line-bot.onrender.com").rstrip("/")


def _mask(s):
    """โชว์แค่ 4 ตัวท้าย กันหลุด secret กลับไป frontend。"""
    s = (s or "").strip()
    return ("•••• " + s[-4:]) if len(s) >= 4 else ("••••" if s else "")


@router.get("/branding")
def get_branding(r: Repo = Depends(repo)):
    """อ่านแบรนด์ของ tenant ที่ login (fallback default ถ้ายังไม่ตั้ง/ยังไม่รัน SQL)。"""
    t = {}
    for cols in ("name,company_name,reporter,logo", "name,company_name,reporter", "name"):
        try:
            rows = r.sb.table("tenants").select(cols).eq("id", r.tenant_id).execute().data
            t = rows[0] if rows else {}
            break
        except Exception:
            continue
    return {
        "name": t.get("name"),
        "company_name": t.get("company_name") or "統一證券",
        "reporter": t.get("reporter") or "秦聖鈞",
        "logo": t.get("logo"),
    }


def _safe_update(r: Repo, payload: dict):
    """update โดยตัดคอลัมน์ที่ยังไม่มี (เผื่อ migration ยังไม่รัน)。"""
    p = dict(payload)
    for _ in range(6):
        try:
            r.sb.table("tenants").update(p).eq("id", r.tenant_id).execute()
            return
        except Exception as e:
            msg = getattr(e, "message", None) or str(e)
            m = (_re.search(r"column \S*?\.?(\w+) does not exist", msg)
                 or _re.search(r"Could not find the '(\w+)' column", msg))
            if not m or m.group(1) not in p:
                raise
            p.pop(m.group(1), None)


@router.put("/branding")
def update_branding(body: dict, r: Repo = Depends(repo)):
    """แก้ชื่อบริษัท / 報告人 / logo ของ tenant ตัวเอง。logo = data URL หรือ null (ลบ)。"""
    payload = {
        "company_name": (body.get("company_name") or "").strip() or None,
        "reporter": (body.get("reporter") or "").strip() or None,
    }
    # logo: ส่งมาเมื่อต้องการเปลี่ยน/ลบ (key มีใน body)
    if "logo" in body:
        logo = body.get("logo")
        payload["logo"] = logo if (isinstance(logo, str) and logo.strip()) else None
    _safe_update(r, payload)
    return {"ok": True}


# ---------- 修改密碼 ----------
@router.post("/password")
def change_password(body: dict, user=Depends(current_user)):
    from utils.auth import verify_password, hash_password
    old = body.get("old_password") or ""
    new = body.get("new_password") or ""
    if len(new) < 6:
        raise HTTPException(status_code=422, detail="新密碼至少 6 碼")
    sb = get_sb()
    rows = sb.table("app_users").select("id,password_hash").eq("id", user["sub"]).execute().data or []
    if not rows:
        raise HTTPException(status_code=404, detail="找不到使用者")
    if not verify_password(old, rows[0].get("password_hash", "")):
        raise HTTPException(status_code=400, detail="舊密碼不正確")
    sb.table("app_users").update({"password_hash": hash_password(new)}).eq("id", user["sub"]).execute()
    return {"ok": True}


# ---------- LINE 管理員 (接收 LINE 通知的人) ----------
@router.get("/line-admins")
def list_line_admins(r: Repo = Depends(repo)):
    try:
        return {"admins": r.list("admins", select="*")}
    except Exception:
        return {"admins": []}


@router.post("/line-admins")
def add_line_admin(body: dict, r: Repo = Depends(repo)):
    uid = (body.get("line_user_id") or "").strip()
    name = (body.get("name") or "").strip() or None
    if not uid:
        raise HTTPException(status_code=422, detail="缺少 LINE User ID")
    try:
        existing = [a for a in r.list("admins", select="*") if a.get("line_user_id") == uid]
        if existing:
            return existing[0]
    except Exception:
        pass
    try:
        return r.create("admins", {"line_user_id": uid, "name": name})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"新增失敗: {getattr(e, 'message', None) or e}")


@router.delete("/line-admins")
def del_line_admin(line_user_id: str, r: Repo = Depends(repo)):
    try:
        r.sb.table("admins").delete().eq("tenant_id", r.tenant_id).eq("line_user_id", line_user_id).execute()
    except Exception:
        pass
    return {"deleted": line_user_id}


# ---------- LINE Bot 憑證 (per-tenant bot：advisor 連自己的 LINE bot) ----------
@router.get("/linebot")
def get_linebot(r: Repo = Depends(repo)):
    """อ่านสถานะบอตของ tenant ตัวเอง + webhook URL ที่ต้องเอาไปตั้งใน LINE Console。
    ไม่คืน secret/token เต็ม (โชว์แค่ masked)。"""
    t = {}
    try:
        rows = r.sb.table("tenants").select(
            "line_channel_secret,line_channel_access_token").eq("id", r.tenant_id).execute().data
        t = rows[0] if rows else {}
    except Exception:
        t = {}
    secret = t.get("line_channel_secret") or ""
    token = t.get("line_channel_access_token") or ""
    return {
        "configured": bool(secret and token),
        "secret_masked": _mask(secret),
        "token_masked": _mask(token),
        "webhook_url": f"{_BOT_BASE_URL}/webhook/{r.tenant_id}",
    }


@router.put("/linebot")
def update_linebot(body: dict, r: Repo = Depends(repo)):
    """บันทึก channel secret + access token ของ tenant。
    ส่งค่าว่าง/null = ล้าง (ปิดบอต)。ส่ง key มาเฉพาะที่ต้องการแก้。"""
    payload = {}
    if "line_channel_secret" in body:
        v = (body.get("line_channel_secret") or "").strip()
        payload["line_channel_secret"] = v or None
    if "line_channel_access_token" in body:
        v = (body.get("line_channel_access_token") or "").strip()
        payload["line_channel_access_token"] = v or None
    if not payload:
        raise HTTPException(status_code=422, detail="無可更新欄位")
    _safe_update(r, payload)
    return {"ok": True}
