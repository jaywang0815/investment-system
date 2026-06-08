import base64
import hashlib
import streamlit as st
from pathlib import Path


def require_auth():
    """Check session state + cookie. Sets authenticated=True and returns True if valid.
    Calls st.stop() if not authenticated so the page shows nothing else."""
    if st.session_state.get("authenticated"):
        return True

    # Try to restore from cookie
    try:
        from streamlit_cookies_controller import CookieController
        _cc = CookieController()
        _pw   = st.secrets.get("ADMIN_PASSWORD", "")
        _hash = st.secrets.get("ADMIN_PASSWORD_HASH", "")
        _secret = st.secrets.get("COOKIE_SECRET", "inv2024secret")
        src = f"{_pw or _hash}:{_secret}"
        expected = hashlib.sha256(src.encode()).hexdigest()[:24]
        if _cc.get("inv_auth") == expected:
            st.session_state.authenticated = True
            return True
    except Exception:
        pass

    st.error("請先登入")
    st.page_link("app.py", label="回到登入頁面", icon="🔑")
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
    """Page title with an animal icon instead of an emoji."""
    img_file = dog_img or _PAGE_DOGS.get(title, "logo.png")
    b64 = _img_b64(img_file)
    if b64:
        icon = f'<img src="data:image/png;base64,{b64}" style="width:72px;height:72px;object-fit:contain;vertical-align:middle;margin-right:12px;flex-shrink:0;">'
    else:
        icon = "🐾 "
    st.markdown(f"""
<h1 style="display:flex;align-items:center;font-size:1.55rem;font-weight:700;
           color:#1E3A8A;padding-bottom:0.3rem;border-bottom:2px solid #e2e8f0;
           margin-bottom:1rem;">
    {icon}{title}
</h1>
""", unsafe_allow_html=True)
