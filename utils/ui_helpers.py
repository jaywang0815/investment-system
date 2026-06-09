import base64
import hashlib
import streamlit as st
from pathlib import Path


def require_auth():
    """Check session state + cookie. If not authenticated, show inline login form."""
    if st.session_state.get("authenticated"):
        return True

    _pw     = st.secrets.get("ADMIN_PASSWORD", "")
    _hash   = st.secrets.get("ADMIN_PASSWORD_HASH", "")
    _secret = st.secrets.get("COOKIE_SECRET", "inv2024secret")
    src      = f"{_pw or _hash}:{_secret}"
    expected = hashlib.sha256(src.encode()).hexdigest()[:24]

    # Try cookie auth — keep rerun OUTSIDE try/except so it isn't swallowed
    _cc = None
    cookie_val = None
    try:
        from streamlit_cookies_controller import CookieController
        _cc = CookieController()
        cookie_val = _cc.get("inv_auth")
    except Exception:
        pass

    if cookie_val is None and not st.session_state.get("_auth_cookie_tried"):
        # First render — JS not ready yet; rerun once so cookie loads
        st.session_state["_auth_cookie_tried"] = True
        st.rerun()

    if cookie_val == expected:
        st.session_state.authenticated = True
        st.session_state.pop("_auth_cookie_tried", None)
        return True

    # Show inline login form on this page (no redirect needed)
    st.warning("請輸入密碼以繼續")
    with st.form("inline_auth_form"):
        pwd = st.text_input("密碼", type="password", placeholder="輸入密碼...")
        submitted = st.form_submit_button("🔑 登入", use_container_width=True)

    if submitted:
        if pwd == (_pw or "") or hashlib.sha256(pwd.encode()).hexdigest() == _hash:
            st.session_state.authenticated = True
            st.session_state.pop("_auth_cookie_tried", None)
            if _cc is not None:
                try:
                    _cc.set("inv_auth", expected, max_age=30 * 24 * 3600)
                except Exception:
                    pass
            st.rerun()
        else:
            st.error("密碼錯誤")

    st.stop()

def _img_b64(filename: str) -> str:
    p = Path(__file__).parent.parent / "assets" / filename
    if p.exists():
        return base64.b64encode(p.read_bytes()).decode()
    return ""

# homepage keeps the French bulldog logo; other pages get animals from the collection
_PAGE_DOGS = {
    "首頁總覽":   "logo.png",
    "客戶管理":   "animals/beagle.png",
    "SN商品管理": "animals/golden.png",
    "KO KI警示":  "animals/schnauzer.png",
    "系統設定":   "animals/samoyed.png",
    "報表匯出":   "animals/corgi.png",
    "資料匯入":   "animals/dalmatian.png",
    "月份管理":   "animals/shiba.png",
    "即時圖表":   "animals/frenchie.png",
}

def dog_header(title: str, dog_img: str = ""):
    """Page title card with an animal icon + applies the global theme (light/dark)."""
    # 全站主題 + 外觀切換 (每頁的統一入口)
    try:
        from utils.theme import apply_theme, theme_toggle
        theme_toggle()
        apply_theme()
    except Exception:
        pass

    img_file = dog_img or _PAGE_DOGS.get(title, "logo.png")
    b64 = _img_b64(img_file)
    if b64:
        icon = (f'<img src="data:image/png;base64,{b64}" '
                f'style="width:60px;height:60px;object-fit:contain;flex-shrink:0;">')
    else:
        icon = '<span style="font-size:36px;">◆</span>'
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:14px;
            background:linear-gradient(135deg,var(--surface,#fff) 0%,var(--surface-soft,#f4fbf7) 100%);
            border:1px solid var(--border,#dcefe4);border-radius:22px;
            padding:14px 22px;margin-bottom:1.3rem;
            box-shadow:0 3px 14px var(--shadow,rgba(20,80,55,.10));">
    {icon}
    <span style="font-size:1.55rem;font-weight:800;letter-spacing:.3px;
                 color:var(--text,#173029);">{title}</span>
</div>
""", unsafe_allow_html=True)
