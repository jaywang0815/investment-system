"""
系統設定精靈 - 一步一步完成所有設定
不需要手動編輯任何設定檔
"""
import streamlit as st
import os
import secrets
import toml
import json
from pathlib import Path

st.set_page_config(page_title="系統設定", page_icon="⚙️", layout="wide")

# ── Admin only ─────────────────────────────────────────────────
_ADMIN_EMAIL = "pmjatu1508@gmail.com"

def _is_admin() -> bool:
    # password login → admin
    if st.session_state.get("authenticated"):
        return True
    # Google login → check email
    try:
        return st.user.is_logged_in and st.user.email == _ADMIN_EMAIL
    except Exception:
        return False

if not _is_admin():
    st.error("⛔ 此頁面僅限管理員存取")
    st.stop()

SECRETS_PATH = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"


def load_existing_secrets() -> dict:
    if SECRETS_PATH.exists():
        try:
            return toml.load(str(SECRETS_PATH))
        except Exception:
            return {}
    return {}


def save_secrets(data: dict) -> bool:
    try:
        SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SECRETS_PATH, "w", encoding="utf-8") as f:
            toml.dump(data, f)
        return True
    except Exception as e:
        st.error(f"儲存失敗: {e}")
        return False


def test_supabase(url: str, key: str) -> tuple[bool, str]:
    try:
        from supabase import create_client
        sb = create_client(url, key)
        sb.table("customers").select("id", count="exact").execute()
        return True, "連線成功 ✅"
    except Exception as e:
        msg = str(e)
        if "relation" in msg and "does not exist" in msg:
            return False, "連線成功，但資料表尚未建立 → 請先執行 schema.sql ⚠️"
        return False, f"連線失敗: {msg}"


def test_line_notify(token: str) -> tuple[bool, str]:
    try:
        import requests
        resp = requests.get(
            "https://notify-api.line.me/api/status",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8
        )
        if resp.status_code == 200:
            return True, f"Token 有效 ✅ ({resp.json().get('targetType', '')})"
        return False, f"Token 無效 (HTTP {resp.status_code})"
    except Exception as e:
        return False, f"測試失敗: {e}"


# ── 頁面開始 ──────────────────────────────────────────────────
st.title("⚙️ 系統設定精靈")
st.caption("在這裡完成所有設定，不需要手動修改任何檔案")

existing = load_existing_secrets()
setup_done = SECRETS_PATH.exists()

if setup_done:
    st.success(f"✅ 設定檔已存在: `{SECRETS_PATH}`")
else:
    st.warning("⚠️ 尚未設定，請填寫下方所有必填欄位")

# ── 設定狀態總覽 ──────────────────────────────────────────────
st.markdown("---")
st.subheader("📊 設定狀態")

c1, c2, c3, c4 = st.columns(4)
with c1:
    has_db = bool(existing.get("SUPABASE_URL"))
    st.metric("資料庫 (Supabase)", "✅ 已設定" if has_db else "❌ 未設定")
with c2:
    has_auth = bool(existing.get("auth", {}).get("google", {}).get("client_id"))
    st.metric("Gmail 登入", "✅ 已設定" if has_auth else "❌ 未設定")
with c3:
    has_line = bool(existing.get("LINE_NOTIFY_TOKEN"))
    st.metric("LINE Notify", "✅ 已設定" if has_line else "❌ 未設定")
with c4:
    has_email = bool(existing.get("allowed_emails"))
    st.metric("授權帳號", "✅ 已設定" if has_email else "❌ 未設定")

st.markdown("---")

# ── 設定表單 ──────────────────────────────────────────────────
st.subheader("🔧 填寫設定")

with st.expander("📖 取得各項設定的說明", expanded=not setup_done):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **Supabase (資料庫):**
        1. 前往 [supabase.com](https://supabase.com) → 免費註冊
        2. 建立新專案 (任意名稱)
        3. Settings → API → 複製 Project URL 和 **service_role** key
        4. SQL Editor → 貼上 `scripts/schema.sql` 內容 → 執行

        **Google OAuth:**
        1. 前往 [console.cloud.google.com](https://console.cloud.google.com)
        2. 建立新專案 → 啟用 **Google+ API**
        3. APIs → Credentials → OAuth 2.0 Client ID
        4. Type: **Web application**
        5. Redirect URI: `http://localhost:8501/oauth2callback`
        6. 複製 Client ID 和 Secret
        """)
    with col2:
        st.markdown("""
        **LINE Notify:**
        1. 前往 [notify-bot.line.me/my](https://notify-bot.line.me/my/)
        2. Generate token → 選擇群組或 1:1 聊天
        3. 複製 token

        **LINE Bot (選填):**
        1. 前往 [developers.line.biz](https://developers.line.biz)
        2. 建立 Messaging API channel
        3. 複製 Channel Secret 和 Access Token
        4. Webhook URL: `https://你的伺服器/webhook`
        """)

# ── Section 1: Supabase ───────────────────────────────────────
st.markdown("### 1️⃣ Supabase 資料庫")
col1, col2 = st.columns(2)
with col1:
    supabase_url = st.text_input(
        "Supabase Project URL *",
        value=existing.get("SUPABASE_URL", ""),
        placeholder="https://xxxxxxxxxx.supabase.co",
        type="default"
    )
with col2:
    supabase_key = st.text_input(
        "Supabase Service Role Key *",
        value=existing.get("SUPABASE_KEY", ""),
        placeholder="eyJhbGci...",
        type="password"
    )

if supabase_url and supabase_key:
    if st.button("🧪 測試資料庫連線"):
        with st.spinner("測試中..."):
            ok, msg = test_supabase(supabase_url, supabase_key)
        if ok:
            st.success(msg)
        else:
            st.warning(msg)

# ── Section 2: Gmail OAuth ────────────────────────────────────
st.markdown("### 2️⃣ Gmail 登入 (Google OAuth)")
auth_existing = existing.get("auth", {})
google_existing = auth_existing.get("google", {})

col1, col2 = st.columns(2)
with col1:
    google_client_id = st.text_input(
        "Google Client ID *",
        value=google_existing.get("client_id", ""),
        placeholder="xxxxxxxxxx.apps.googleusercontent.com"
    )
with col2:
    google_client_secret = st.text_input(
        "Google Client Secret *",
        value=google_existing.get("client_secret", ""),
        placeholder="GOCSPX-xxxxxxxxxx",
        type="password"
    )

allowed_emails_list = existing.get("allowed_emails", [])
allowed_emails_str = st.text_input(
    "授權 Gmail 帳號 * (多個帳號用逗號分隔)",
    value=", ".join(allowed_emails_list) if isinstance(allowed_emails_list, list) else str(allowed_emails_list),
    placeholder="your@gmail.com, another@gmail.com"
)

cookie_secret_existing = auth_existing.get("cookie_secret", "")
if not cookie_secret_existing:
    cookie_secret_existing = secrets.token_urlsafe(32)

cookie_secret = st.text_input(
    "Cookie Secret (隨機字串，不要修改)",
    value=cookie_secret_existing,
    type="password"
)

# ── Section 3: LINE ───────────────────────────────────────────
st.markdown("### 3️⃣ LINE 通知設定")
col1, col2 = st.columns(2)
with col1:
    line_notify_token = st.text_input(
        "LINE Notify Token",
        value=existing.get("LINE_NOTIFY_TOKEN", ""),
        type="password",
        placeholder="每日報告通知用 (必填)"
    )
    if line_notify_token:
        if st.button("🧪 測試 LINE Notify"):
            with st.spinner("測試中..."):
                ok, msg = test_line_notify(line_notify_token)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

with col2:
    line_channel_secret = st.text_input(
        "LINE Channel Secret",
        value=existing.get("LINE_CHANNEL_SECRET", ""),
        type="password",
        placeholder="LINE Bot 用 (選填)"
    )
    line_channel_token = st.text_input(
        "LINE Channel Access Token",
        value=existing.get("LINE_CHANNEL_ACCESS_TOKEN", ""),
        type="password",
        placeholder="LINE Bot 用 (選填)"
    )

# ── Section 4: Google Sheets (optional) ──────────────────────
st.markdown("### 4️⃣ Google Sheets 同步 (選填)")
google_sheet_id = st.text_input(
    "Google Sheet ID",
    value=existing.get("GOOGLE_SHEET_ID", ""),
    placeholder="從 Sheet 網址取得 .../d/[這裡]/edit"
)

# ── 儲存設定 ──────────────────────────────────────────────────
st.markdown("---")
col_save, col_reset = st.columns([3, 1])

with col_save:
    if st.button("💾 儲存所有設定", type="primary", use_container_width=True):
        # 驗證必填
        errors = []
        if not supabase_url:
            errors.append("請填寫 Supabase URL")
        if not supabase_key:
            errors.append("請填寫 Supabase Key")
        if not allowed_emails_str:
            errors.append("請填寫授權 Gmail 帳號")

        if errors:
            for e in errors:
                st.error(f"❌ {e}")
        else:
            # 建構設定 dict
            emails = [e.strip() for e in allowed_emails_str.split(",") if e.strip()]

            new_secrets = {
                "SUPABASE_URL": supabase_url,
                "SUPABASE_KEY": supabase_key,
                "allowed_emails": emails,
                "auth": {
                    "redirect_uri": "http://localhost:8501/oauth2callback",
                    "cookie_secret": cookie_secret,
                    "google": {
                        "client_id": google_client_id,
                        "client_secret": google_client_secret,
                        "server_metadata_url": "https://accounts.google.com/.well-known/openid-configuration"
                    }
                }
            }

            if line_notify_token:
                new_secrets["LINE_NOTIFY_TOKEN"] = line_notify_token
            if line_channel_secret:
                new_secrets["LINE_CHANNEL_SECRET"] = line_channel_secret
            if line_channel_token:
                new_secrets["LINE_CHANNEL_ACCESS_TOKEN"] = line_channel_token
            if google_sheet_id:
                new_secrets["GOOGLE_SHEET_ID"] = google_sheet_id

            if save_secrets(new_secrets):
                st.success("✅ 設定已儲存！請重新啟動程式讓設定生效。")
                st.info("重新啟動方式: 在 Terminal 按 Ctrl+C，再執行 `python3 -m streamlit run app.py`")
                st.balloons()

with col_reset:
    if st.button("🔄 重置設定", use_container_width=True):
        if SECRETS_PATH.exists():
            SECRETS_PATH.unlink()
            st.warning("設定已清除，請重新啟動程式")

# ── 設定檔預覽 ────────────────────────────────────────────────
if setup_done:
    with st.expander("📄 查看目前設定檔內容"):
        safe_preview = existing.copy()
        for key in ["SUPABASE_KEY", "LINE_NOTIFY_TOKEN", "LINE_CHANNEL_SECRET",
                    "LINE_CHANNEL_ACCESS_TOKEN"]:
            if key in safe_preview:
                val = str(safe_preview[key])
                safe_preview[key] = val[:8] + "..." if len(val) > 8 else "***"
        if "auth" in safe_preview and "google" in safe_preview["auth"]:
            cs = str(safe_preview["auth"].get("cookie_secret", ""))
            safe_preview["auth"]["cookie_secret"] = cs[:8] + "..." if cs else "***"
            gcr = safe_preview["auth"]["google"].get("client_secret", "")
            safe_preview["auth"]["google"]["client_secret"] = str(gcr)[:8] + "..."
        st.json(safe_preview)

# ── 管理員 LINE 通知管理 ──────────────────────────────────────
st.markdown("---")
st.subheader("👥 管理員 LINE 通知設定")
st.caption("在這裡加入要接收每日報告和價格警示的管理員 LINE User ID（讓對方在 LINE Bot 傳送 myid 即可取得）")

try:
    from supabase import create_client as _create_client
    _sb = _create_client(existing.get("SUPABASE_URL", "") or st.secrets.get("SUPABASE_URL", ""),
                         existing.get("SUPABASE_KEY", "") or st.secrets.get("SUPABASE_KEY", ""))

    # แสดงรายการ admin ปัจจุบัน
    _admins_resp = _sb.table("admins").select("*").order("created_at").execute()
    _admins = _admins_resp.data or []

    if _admins:
        st.markdown(f"**目前已設定 {len(_admins)} 位管理員：**")
        for adm in _admins:
            col_name, col_id, col_del = st.columns([2, 3, 1])
            with col_name:
                st.write(f"**{adm['name']}**")
            with col_id:
                lid = adm.get("line_user_id", "")
                st.code(f"{lid[:12]}..." if len(lid) > 12 else lid, language=None)
            with col_del:
                if st.button("🗑️", key=f"del_admin_{adm['id']}", help="刪除此管理員"):
                    _sb.table("admins").delete().eq("id", adm["id"]).execute()
                    st.rerun()
    else:
        st.info("尚未設定任何管理員")

    # ฟอร์มเพิ่ม admin ใหม่
    st.markdown("**新增管理員：**")
    with st.form("add_admin_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            new_admin_name = st.text_input("姓名", placeholder="例: 游家順")
        with col_b:
            new_admin_line = st.text_input("LINE User ID", placeholder="Uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        if st.form_submit_button("➕ 新增管理員", type="primary"):
            if not new_admin_name.strip() or not new_admin_line.strip():
                st.error("請填寫姓名和 LINE User ID")
            elif not new_admin_line.strip().startswith("U"):
                st.error("LINE User ID 必須以 U 開頭")
            else:
                try:
                    _sb.table("admins").insert({
                        "name": new_admin_name.strip(),
                        "line_user_id": new_admin_line.strip()
                    }).execute()
                    st.success(f"✅ 已新增管理員 {new_admin_name.strip()}")
                    st.rerun()
                except Exception as _e:
                    st.error(f"新增失敗: {_e}")

except Exception as _err:
    st.warning(f"無法連線資料庫，請先完成上方 Supabase 設定 ({_err})")

# ── 執行 Schema SQL 說明 ───────────────────────────────────────
st.markdown("---")
st.subheader("🗄️ 建立資料庫結構")
st.markdown("設定完 Supabase 後，需要建立資料表。請複製下方 SQL 到 Supabase Dashboard → SQL Editor → 執行")

try:
    schema_path = Path(__file__).parent.parent / "scripts" / "schema.sql"
    with open(schema_path, "r") as f:
        sql_content = f.read()
    st.code(sql_content, language="sql")

    st.download_button(
        "⬇️ 下載 schema.sql",
        data=sql_content,
        file_name="schema.sql",
        mime="text/plain"
    )
except Exception:
    st.info("schema.sql 位於 scripts/schema.sql")
