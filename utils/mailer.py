"""ส่งอีเมลผ่าน Resend (ถ้าตั้ง RESEND_API_KEY)。ไม่ตั้ง = no-op (คืน False) — ระบบยังใช้ลิงก์ก็อปเองได้。
ใช้ urllib (stdlib) ไม่ต้องเพิ่ม dependency。"""
import os
import json
import urllib.request


def mail_enabled() -> bool:
    return bool(os.environ.get("RESEND_API_KEY"))


def send_email(to: str, subject: str, html: str) -> bool:
    key = os.environ.get("RESEND_API_KEY")
    if not key or not to:
        return False
    sender = os.environ.get("MAIL_FROM", "onboarding@resend.dev")
    try:
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=json.dumps({"from": sender, "to": [to], "subject": subject, "html": html}).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def app_base_url() -> str:
    return os.environ.get("APP_BASE_URL", "https://office.justinvestment.co").rstrip("/")


def send_invite_email(to: str, company: str, invite_path: str) -> bool:
    url = app_base_url() + invite_path
    html = f"""
    <div style="font-family:system-ui,sans-serif;max-width:480px;margin:0 auto">
      <h2 style="color:#1E3A8A">Justinvestment 邀請</h2>
      <p>您好，您受邀加入 <b>{company or 'Justinvestment'}</b> 投資管理平台。</p>
      <p>請點以下連結設定密碼並開始使用：</p>
      <p><a href="{url}" style="display:inline-block;background:#1E3A8A;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none">設定密碼 · 開始使用</a></p>
      <p style="color:#888;font-size:13px">或複製此連結：<br>{url}</p>
    </div>
    """
    return send_email(to, "Justinvestment 邀請 — 設定您的密碼", html)
