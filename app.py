"""
DOUU WORK - 主應用程式
結構型商品 (Structured Notes) 管理平台
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta

st.set_page_config(
    page_title="DOUU WORK",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── 全域 CSS  (Smart-Home inspired redesign) ─────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ── Base ─────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {
    background: #F2FAF5 !important;
    font-family: 'Inter', sans-serif !important;
}
.main .block-container {
    padding-top: 1.6rem;
    padding-bottom: 2.5rem;
    max-width: 1280px;
}

/* ── Sidebar ──────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #0F7A46 !important;
    border-right: none !important;
    box-shadow: 4px 0 24px rgba(16,90,55,0.18) !important;
}
[data-testid="stSidebar"] * { color: #D6F5E6 !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.1) !important; }

[data-testid="stSidebarNavLink"] {
    border-radius: 14px !important;
    margin: 3px 8px !important;
    padding: 10px 14px !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    transition: all 0.2s !important;
    color: #BDEBD2 !important;
}
[data-testid="stSidebarNavLink"]:hover {
    background: rgba(255,255,255,0.12) !important;
    color: #fff !important;
    transform: translateX(3px) !important;
}
[data-testid="stSidebarNavLink"][aria-selected="true"] {
    background: rgba(21,163,90,0.35) !important;
    color: #fff !important;
    box-shadow: 0 2px 12px rgba(21,163,90,0.3) !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.1) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    color: white !important;
    border-radius: 12px !important;
}

/* ── Page title ───────────────────────────────────── */
h1 {
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: #0f7a46 !important;
    padding-bottom: 0 !important;
    border-bottom: none !important;
    margin-bottom: 1.2rem !important;
    letter-spacing: -0.3px !important;
}
h2 { font-size: 1.1rem !important; font-weight: 600 !important; color: #15803D !important; }
h3 { font-size: 0.95rem !important; font-weight: 600 !important; color: #16A34A !important; }

/* ── Metric cards ─────────────────────────────────── */
[data-testid="stMetric"] {
    background: #ffffff !important;
    border: none !important;
    border-radius: 20px !important;
    padding: 1.3rem 1.5rem !important;
    box-shadow: 0 4px 20px rgba(21,163,90,0.08), 0 1px 4px rgba(0,0,0,0.04) !important;
    transition: transform 0.2s, box-shadow 0.2s !important;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px rgba(21,163,90,0.14) !important;
}
[data-testid="stMetricLabel"] {
    color: #6b7280 !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}
[data-testid="stMetricValue"] {
    color: #0f7a46 !important;
    font-weight: 700 !important;
    font-size: 1.8rem !important;
}
[data-testid="stMetricDelta"] { font-size: 0.82rem !important; font-weight: 600 !important; }

/* ── Buttons ──────────────────────────────────────── */
.stButton > button {
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    transition: all 0.2s ease !important;
    border: none !important;
    padding: 0.5rem 1.2rem !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #15A35A 0%, #2BD47E 100%) !important;
    color: white !important;
    box-shadow: 0 4px 14px rgba(21,163,90,0.35) !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(21,163,90,0.45) !important;
}
.stButton > button[kind="secondary"] {
    background: white !important;
    border: 1.5px solid #e8f7ef !important;
    color: #15A35A !important;
}
.stButton > button[kind="secondary"]:hover {
    background: #F2FAF5 !important;
    border-color: #2BD47E !important;
}

/* ── Tabs ─────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: #E8F7EF;
    padding: 5px;
    border-radius: 14px;
    gap: 4px;
    border-bottom: none !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px !important;
    padding: 7px 20px !important;
    font-weight: 500 !important;
    color: #2BD47E !important;
    background: transparent !important;
    font-size: 0.88rem !important;
}
.stTabs [aria-selected="true"] {
    background: white !important;
    color: #15803D !important;
    box-shadow: 0 2px 8px rgba(21,163,90,0.15) !important;
    font-weight: 600 !important;
}

/* ── DataFrame / Table ────────────────────────────── */
[data-testid="stDataFrame"] {
    border-radius: 16px !important;
    border: none !important;
    overflow: hidden !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06) !important;
}

/* ── Inputs ───────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
.stSelectbox > div > div,
.stTextArea textarea {
    border-radius: 12px !important;
    border: 1.5px solid #e8f7ef !important;
    background: #fff !important;
    font-size: 0.9rem !important;
    transition: border 0.2s, box-shadow 0.2s !important;
}
[data-testid="stTextInput"] input:focus,
.stTextArea textarea:focus {
    border-color: #2BD47E !important;
    box-shadow: 0 0 0 3px rgba(21,163,90,0.15) !important;
}

/* ── Expander ─────────────────────────────────────── */
[data-testid="stExpander"] {
    background: white !important;
    border: none !important;
    border-radius: 16px !important;
    overflow: hidden !important;
    margin-bottom: 8px !important;
    box-shadow: 0 2px 10px rgba(21,163,90,0.07) !important;
}
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    color: #15803D !important;
    padding: 12px 18px !important;
    font-size: 0.92rem !important;
}
[data-testid="stExpander"] summary:hover { background: #F5F3FF !important; }

/* ── Alerts ───────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 14px !important;
    border-left-width: 4px !important;
    font-size: 0.9rem !important;
}

/* ── Alert blocks ─────────────────────────────────── */
.alert-ki   { background:#FFF1F3; border-left:4px solid #F43F5E; padding:12px 16px; border-radius:14px; margin:5px 0; }
.alert-ko   { background:#ECFDF5; border-left:4px solid #10B981; padding:12px 16px; border-radius:14px; margin:5px 0; }
.alert-warn { background:#FFFBEB; border-left:4px solid #F59E0B; padding:12px 16px; border-radius:14px; margin:5px 0; }

/* ── Divider ──────────────────────────────────────── */
hr { border-color: #e8f7ef !important; margin: 1.2rem 0 !important; }

/* ── Scrollbar ────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #F2FAF5; border-radius: 4px; }
::-webkit-scrollbar-thumb { background: #D6F5E6; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #818cf8; }

/* ── Form ─────────────────────────────────────────── */
[data-testid="stForm"] {
    background: white !important;
    border-radius: 20px !important;
    padding: 1.5rem !important;
    border: none !important;
    box-shadow: 0 4px 20px rgba(21,163,90,0.08) !important;
}

/* ── Spinner ──────────────────────────────────────── */
[data-testid="stSpinner"] { color: #2BD47E !important; }

/* ── Success / Info / Warning / Error ────────────── */
.stSuccess { border-radius: 14px !important; }
.stInfo    { border-radius: 14px !important; }
.stWarning { border-radius: 14px !important; }
.stError   { border-radius: 14px !important; }

/* ── Flair: motion & micro-interactions ───────────── */
@keyframes flairRise {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes flairShimmer {
    0%   { background-position: 0% 50%; }
    100% { background-position: 200% 50%; }
}
/* metric cards: staggered entrance + lift + accent top-line glow on hover */
[data-testid="stMetric"] {
    animation: flairRise .6s cubic-bezier(.22,1,.36,1) both;
    position: relative; overflow: hidden;
}
[data-testid="column"]:nth-child(1) [data-testid="stMetric"] { animation-delay: .02s; }
[data-testid="column"]:nth-child(2) [data-testid="stMetric"] { animation-delay: .10s; }
[data-testid="column"]:nth-child(3) [data-testid="stMetric"] { animation-delay: .18s; }
[data-testid="column"]:nth-child(4) [data-testid="stMetric"] { animation-delay: .26s; }
[data-testid="stMetric"]:hover {
    transform: translateY(-4px) !important;
    box-shadow: 0 14px 34px rgba(21,163,90,0.16) !important;
}
[data-testid="stMetricValue"] {
    background: linear-gradient(90deg,#15a34a,#2bd47e,#15a34a);
    background-size: 200% auto;
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: flairShimmer 5s linear infinite;
}
/* buttons: springy press */
.stButton > button:active { transform: scale(.97) !important; }
/* expanders & alerts gently rise in */
[data-testid="stExpander"], [data-testid="stAlert"] {
    animation: flairRise .5s cubic-bezier(.22,1,.36,1) both;
}
/* dataframe lift */
[data-testid="stDataFrame"] { transition: box-shadow .2s ease, transform .2s ease; }
[data-testid="stDataFrame"]:hover { transform: translateY(-2px); box-shadow: 0 10px 28px rgba(21,163,90,.12); }
</style>
""", unsafe_allow_html=True)

# ── gear icon + hide settings from sidebar ────────────────
st.markdown("""
<style>
.gear-fab {
    position: fixed;
    top: 0.6rem;
    right: 5.2rem;
    z-index: 9999999;
    background: rgba(255,255,255,0.92);
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.28rem 0.55rem;
    font-size: 1.2rem;
    text-decoration: none !important;
    color: #475569 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1);
    transition: all 0.15s;
}
.gear-fab:hover { background:#1E3A8A; color:white !important; border-color:#1E3A8A; }
</style>
<a href="/系統設定" target="_self" class="gear-fab" title="系統設定"></a>
<script>
(function() {
    function hide() {
        var links = document.querySelectorAll('[data-testid="stSidebarNavLink"]');
        links.forEach(function(a) {
            if (a.textContent.indexOf('系統設定') !== -1) {
                var li = a.closest('li');
                if (li) li.style.cssText = 'display:none!important';
            }
        });
    }
    hide();
    new MutationObserver(hide).observe(document.documentElement, {childList:true, subtree:true});
})();
</script>
""", unsafe_allow_html=True)

# ── 檢查設定是否完成 ─────────────────────────────────────────
try:
    _setup_complete = bool(st.secrets.get("SUPABASE_URL") and st.secrets.get("SUPABASE_KEY"))
except Exception:
    _setup_complete = False

if not _setup_complete:
    st.markdown("## DOUU WORK")
    st.markdown("---")
    st.warning("**系統尚未完成設定**")
    st.markdown("請先前往「**系統設定**」頁面完成初始設定（約 5-10 分鐘）")
    st.page_link("pages/0_系統設定.py", label="→ 前往系統設定")
    st.markdown("""
    **需要準備的帳號:**
    1. [Supabase](https://supabase.com) 帳號 (免費)
    2. [Google Cloud](https://console.cloud.google.com) 帳號 (免費)
    3. [LINE Notify](https://notify-bot.line.me/my/) Token
    """)
    st.stop()

# ── 登入系統 (支援兩種模式) ──────────────────────────────────
# 模式 1: 簡單密碼 (預設，不需要 Google Cloud 設定)
# 模式 2: Gmail OAuth (在 secrets.toml 設定 Google credentials 後啟用)

import hashlib
import base64
from pathlib import Path

def _img_b64(filename: str) -> str:
    p = Path(__file__).parent / "assets" / filename
    if p.exists():
        return base64.b64encode(p.read_bytes()).decode()
    return ""

def _check_password(pw: str, stored_hash: str) -> bool:
    return hashlib.sha256(pw.encode()).hexdigest() == stored_hash

_use_google_auth = bool(
    st.secrets.get("auth", {}).get("google", {}).get("client_id")
)
_admin_password_hash = st.secrets.get("ADMIN_PASSWORD_HASH", "")
_admin_password_plain = st.secrets.get("ADMIN_PASSWORD", "")

# ── Cookie 管理 (記住登入狀態 30 天) ─────────────────────────
_COOKIE_SECRET = st.secrets.get("COOKIE_SECRET", "inv2024secret")

def _cookie_token():
    src = f"{_admin_password_plain or _admin_password_hash}:{_COOKIE_SECRET}"
    return hashlib.sha256(src.encode()).hexdigest()[:24]

try:
    from streamlit_cookies_controller import CookieController
    _cc = CookieController()

    def _set_cookie():
        _cc.set("inv_auth", _cookie_token(), max_age=365 * 24 * 3600)  # 記住 1 年

    def _del_cookie():
        try:
            _cc.remove("inv_auth")
        except Exception:
            pass

    def _cookie_ok():
        try:
            return _cc.get("inv_auth") == _cookie_token()
        except Exception:
            return False

    _cookie_available = True
except Exception:
    _cookie_available = False
    def _set_cookie(): pass
    def _del_cookie(): pass
    def _cookie_ok(): return False

# session 登入狀態
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# ถ้า cookie ยังดี → ข้ามหน้า login ไปเลย
# (รอบแรกของ session ใหม่ cookie ยังโหลดไม่ทัน → rerun หนึ่งครั้งให้ JS ส่ง cookie มาก่อน
#  ไม่งั้นจะเด้งหน้า PIN ทั้งที่ยังจำ login อยู่)
if _cookie_available and not st.session_state.authenticated:
    try:
        _cv = _cc.get("inv_auth")
    except Exception:
        _cv = None
    if _cv == _cookie_token():
        st.session_state.authenticated = True
        st.session_state.pop("_auth_cookie_tried", None)
    elif _cv is None and not st.session_state.get("_auth_cookie_tried"):
        st.session_state["_auth_cookie_tried"] = True
        st.rerun()

# 已登入 → 繼續
_google_logged_in = False
if _use_google_auth:
    try:
        _google_logged_in = st.user.is_logged_in
    except Exception:
        pass

if not st.session_state.authenticated and not _google_logged_in:
    if "pin_input" not in st.session_state:
        st.session_state.pin_input = ""
    if "pin_error" not in st.session_state:
        st.session_state.pin_error = False

    correct_pin = _admin_password_plain or ""
    pin_len = len(correct_pin) if correct_pin else 4
    entered = st.session_state.pin_input

    st.markdown(f"""
    <style>
    .main .block-container {{
        max-width: 380px !important;
        margin: 0 auto !important;
        padding-top: 3rem !important;
    }}
    .pin-mark {{
        width:72px; height:72px; margin:0 auto 1rem; border-radius:22px;
        display:flex; align-items:center; justify-content:center;
        font-size:1.6rem; font-weight:800; color:#fff; letter-spacing:.02em;
        background:linear-gradient(135deg,#15a34a 0%,#2bd47e 100%);
        box-shadow:0 10px 30px rgba(21,163,90,.35);
        animation: pinpop .6s cubic-bezier(.22,1,.36,1) both;
    }}
    @keyframes pinpop {{ from {{opacity:0; transform:translateY(10px) scale(.92);}} to {{opacity:1; transform:none;}} }}
    .pin-title    {{ font-size:1.7rem; font-weight:800; color:#0b0f0d; text-align:center; display:block; margin-bottom:0.15rem; letter-spacing:0.04em; }}
    .pin-title span {{ color:#15a34a; }}
    .pin-subtitle {{ font-size:0.88rem; color:#94a3b8; text-align:center; display:block; margin-bottom:1.6rem; }}
    .pin-error    {{ color:#ef4444; font-size:0.85rem; text-align:center; display:block; margin-top:0.5rem; }}
    </style>
    <div class="pin-mark">DW</div>
    <div class="pin-title">DOUU WORK<span>.</span></div>
    <div class="pin-subtitle">輸入 PIN 碼解鎖</div>
    """, unsafe_allow_html=True)

    if st.session_state.pin_error:
        st.markdown('<div class="pin-error">PIN 不正確，請重試</div>', unsafe_allow_html=True)

    typed = st.text_input("PIN", value="", max_chars=pin_len,
                          type="password", placeholder="輸入 PIN 後按 Enter",
                          label_visibility="collapsed",
                          key="pin_keyboard")
    if typed:
        if typed == correct_pin:
            st.session_state.authenticated = True
            st.session_state.pin_error = False
            _set_cookie()
            import time as _t
            _t.sleep(0.6)   # ให้ component เขียน cookie ลง browser ให้เสร็จก่อน rerun (ไม่งั้น cookie ไม่ติด)
            st.rerun()
        elif len(typed) >= pin_len:
            st.session_state.pin_error = True
            st.rerun()

    st.stop()

# ── 權限檢查 ──────────────────────────────────────────────────
if _use_google_auth and _google_logged_in:
    try:
        allowed = st.secrets.get("allowed_emails", [])
        if allowed and st.user.email not in allowed:
            st.error(f"帳號 **{st.user.email}** 無存取權限")
            if st.button("登出"):
                st.logout()
            st.stop()
    except Exception:
        pass

# ── ซ่อน 系統設定 สำหรับ non-admin ──────────────────────────────
_ADMIN_EMAIL = "pmjatu1508@gmail.com"
_is_admin = (
    st.session_state.get("authenticated") or
    getattr(getattr(st, "user", None), "email", "") == _ADMIN_EMAIL
)
if not _is_admin:
    st.markdown("""
    <style>
    [data-testid="stSidebarNav"] ul li:first-child { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

# ── 側邊欄 ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding: 8px 6px 4px;'>
        <div style='font-size:1.25rem; font-weight:800; letter-spacing:0.04em; color:white;'>
            DOUU&nbsp;WORK<span style='color:#2bd47e;'>.</span>
        </div>
        <div style='font-size:0.66rem; letter-spacing:0.2em; text-transform:uppercase;
                    color:rgba(255,255,255,0.55); margin-top:3px;'>Structured Notes</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    if _use_google_auth and _google_logged_in:
        try:
            st.markdown(f"&nbsp;**{st.user.name}**")
            st.caption(st.user.email)
        except Exception:
            st.markdown("&nbsp;**已登入**")
        if st.button("登出", use_container_width=True):
            st.logout()
    else:
        st.markdown(f"&nbsp;**{st.session_state.get('admin_name', 'Douu小幫手')}**")
        if st.button("登出", use_container_width=True):
            st.session_state.authenticated = False
            _del_cookie()
            st.rerun()
    st.markdown("---")

# ── 主頁面 ────────────────────────────────────────────────────
from utils.ui_helpers import dog_header
from datetime import datetime

# 引入工具模組
try:
    from utils.database import get_dashboard_stats, get_all_sns, get_all_customers
    from utils.stock_prices import get_prices, get_all_tickers_for_active_sns, analyze_sn_status
except ImportError as e:
    st.error(f"模組載入失敗: {e}\n請確認已執行 pip install -r requirements.txt")
    st.stop()

# 資料庫連線
try:
    stats = get_dashboard_stats()
    db_ok = True
except Exception as e:
    st.error(f"資料庫連線失敗: {e}")
    st.info("請確認 .streamlit/secrets.toml 中的 Supabase 設定正確")
    db_ok = False

if not db_ok:
    st.stop()

# ── Dashboard CSS ──────────────────────────────────────────────
st.markdown("""<style>
.hero-banner {
    background: linear-gradient(115deg, #0c7a45 0%, #15a34a 38%, #1fae8a 68%, #2bd47e 100%);
    background-size: 220% 220%;
    animation: heroFlow 14s ease infinite, flairRise .7s cubic-bezier(.22,1,.36,1) both;
    border-radius: 24px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 14px 44px rgba(21,163,90,0.30);
    position: relative;
    overflow: hidden;
}
@keyframes heroFlow { 0%{background-position:0% 50%;} 50%{background-position:100% 50%;} 100%{background-position:0% 50%;} }
@keyframes heroFloat { 0%,100%{transform:translate(0,0);} 50%{transform:translate(-14px,12px);} }
.hero-banner::before {
    content: '';
    position: absolute;
    width: 240px; height: 240px;
    background: rgba(255,255,255,0.08);
    border-radius: 50%;
    top: -80px; right: -50px;
    animation: heroFloat 11s ease-in-out infinite;
}
.hero-banner::after {
    content: '';
    position: absolute;
    width: 120px; height: 120px;
    background: rgba(255,255,255,0.04);
    border-radius: 50%;
    bottom: -40px; right: 140px;
}
.hero-greeting {
    font-size: 1.85rem;
    font-weight: 800;
    color: white;
    margin: 0 0 0.3rem 0;
    letter-spacing: -0.5px;
    line-height: 1.2;
}
.hero-sub { color: rgba(255,255,255,0.58); font-size: 0.88rem; margin: 0; }
.hero-right { text-align: right; z-index: 1; }
.hero-clock {
    font-size: 2.5rem;
    font-weight: 800;
    color: white;
    letter-spacing: -1.5px;
    line-height: 1;
}
.hero-datestr { color: rgba(255,255,255,0.5); font-size: 0.8rem; margin-top: 5px; }

/* gradient blob backdrop so the frosted glass reads in 3D */
[data-testid="stAppViewContainer"]::before {
    content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background:
      radial-gradient(38% 32% at 10% 6%, rgba(43,212,126,0.22), transparent 70%),
      radial-gradient(34% 30% at 90% 10%, rgba(16,185,129,0.18), transparent 70%),
      radial-gradient(46% 40% at 78% 92%, rgba(20,184,166,0.16), transparent 72%),
      radial-gradient(40% 38% at 25% 95%, rgba(124,92,246,0.10), transparent 72%);
}
[data-testid="stAppViewContainer"] > .main { position: relative; z-index: 1; }

.scard {
    background: rgba(255,255,255,0.55);
    -webkit-backdrop-filter: blur(18px) saturate(160%);
    backdrop-filter: blur(18px) saturate(160%);
    border: 1px solid rgba(255,255,255,0.65);
    border-radius: 22px;
    padding: 1.4rem 1.6rem;
    box-shadow: 0 10px 32px rgba(20,80,55,0.12), inset 0 1px 0 rgba(255,255,255,0.75);
    position: relative;
    overflow: hidden;
    transition: transform 0.25s cubic-bezier(.22,1,.36,1), box-shadow 0.25s;
}
.scard:hover { transform: translateY(-5px); box-shadow: 0 20px 44px rgba(21,163,90,0.20), inset 0 1px 0 rgba(255,255,255,0.8); }
.scard-icon {
    width: 46px; height: 46px;
    border-radius: 15px;
    display: flex; align-items: center; justify-content: center;
    margin-bottom: 0.9rem;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.9), 0 4px 12px rgba(20,80,55,0.10);
}
.scard-val {
    font-size: 2.1rem;
    font-weight: 800;
    line-height: 1;
    margin-bottom: 0.3rem;
    letter-spacing: -1px;
}
.scard-label {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: #94a3b8;
}

.sec-head {
    display: flex; align-items: center; gap: 9px;
    margin: 1.6rem 0 0.85rem 0;
}
.sec-head-icon {
    width: 32px; height: 32px;
    border-radius: 9px;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.92rem; flex-shrink: 0;
}
.sec-head-title { font-size: 0.95rem; font-weight: 700; color: #0f7a46; margin: 0; }

.alert-card-ki   { background:#FFF1F3; border-left:4px solid #F43F5E; padding:11px 14px; border-radius:14px; margin:6px 0; font-size:0.87rem; }
.alert-card-ko   { background:#ECFDF5; border-left:4px solid #10B981; padding:11px 14px; border-radius:14px; margin:6px 0; font-size:0.87rem; }
.alert-card-warn { background:#FFFBEB; border-left:4px solid #F59E0B; padding:11px 14px; border-radius:14px; margin:6px 0; font-size:0.87rem; }

.obs-row {
    display: flex; align-items: center; gap: 9px;
    padding: 0.6rem 0.85rem;
    border-radius: 12px; margin: 5px 0;
    font-size: 0.84rem; background: #F8F9FF;
}
.obs-row:hover { background: #F2FAF5; }
.obs-code { font-weight: 700; color: #0f7a46; flex: 1; min-width: 0; }
.obs-meta { color: #64748b; font-size: 0.76rem; text-align: right; flex-shrink: 0; }
.obs-chip {
    font-size: 0.72rem; font-weight: 700;
    border-radius: 8px; padding: 2px 8px;
    white-space: nowrap; flex-shrink: 0;
}

.px-grid { display: flex; flex-wrap: wrap; gap: 0.7rem; }
.px-card {
    background: rgba(255,255,255,0.5);
    -webkit-backdrop-filter: blur(14px) saturate(150%);
    backdrop-filter: blur(14px) saturate(150%);
    border: 1px solid rgba(255,255,255,0.6);
    border-radius: 18px;
    padding: 0.9rem 1.2rem 0.75rem;
    min-width: 120px; flex: 1;
    box-shadow: 0 8px 24px rgba(20,80,55,0.10), inset 0 1px 0 rgba(255,255,255,0.7);
    transition: transform 0.2s cubic-bezier(.22,1,.36,1);
}
.px-card:hover { transform: translateY(-3px); }
.px-sym { font-size: 0.72rem; font-weight: 700; color: #64748b; letter-spacing: 0.5px; }
.px-price { font-size: 1.3rem; font-weight: 800; color: #0f7a46; letter-spacing: -0.5px; margin-top: 3px; }
.px-na { font-size: 0.8rem; color: #94a3b8; font-style: italic; margin-top: 3px; }
</style>""", unsafe_allow_html=True)

# ── Hero Banner ────────────────────────────────────────────────
if "admin_name" not in st.session_state:
    try:
        from utils.database import get_setting
        st.session_state["admin_name"] = get_setting("admin_name", "Douu小幫手")
    except Exception:
        st.session_state["admin_name"] = "Douu小幫手"
_admin_name = st.session_state["admin_name"]

from zoneinfo import ZoneInfo
_now = datetime.now(ZoneInfo("Asia/Taipei"))   # 伺服器在 UTC，固定用台北時間顯示
_wd = ["一","二","三","四","五","六","日"][_now.weekday()]
_date_str = _now.strftime(f"%Y年%m月%d日 · 週{_wd}")
_time_str = _now.strftime("%H:%M")

st.markdown(f"""
<div class="hero-banner">
  <div>
    <div class="hero-greeting">Hello, {_admin_name} </div>
    <div class="hero-sub">DOUU WORK &nbsp;·&nbsp; 結構型商品管理平台</div>
  </div>
  <div class="hero-right">
    <div class="hero-clock">{_time_str}</div>
    <div class="hero-datestr">{_date_str}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Stat Cards ─────────────────────────────────────────────────
total_usd = stats.get('total_investment_usd', 0)
total_str = f"${total_usd/1_000_000:.2f}M" if total_usd >= 1_000_000 else f"${total_usd:,.0f}"

# finance line-icons (inherit colour from .scard-icon)
_SVG = lambda body: (f'<svg width="22" height="22" viewBox="0 0 24 24" fill="none" '
                     f'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
                     f'stroke-linejoin="round">{body}</svg>')
_IC_CUSTOMERS = _SVG('<circle cx="9" cy="8" r="3.1"/><path d="M3.6 19c0-3 2.4-5 5.4-5s5.4 2 5.4 5"/>'
                     '<path d="M16.2 7.6a3 3 0 0 1 0 5.4"/><path d="M18.6 19c0-2-.9-3.7-2.4-4.5"/>')
_IC_PRODUCTS  = _SVG('<path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4"/>'
                     '<path d="M10 17l1.8-2.2 1.6 1.4L16 13"/>')
_IC_MONEY     = _SVG('<ellipse cx="12" cy="6.4" rx="6.4" ry="2.7"/>'
                     '<path d="M5.6 6.4v5c0 1.5 2.9 2.7 6.4 2.7s6.4-1.2 6.4-2.7v-5"/>'
                     '<path d="M5.6 11.4v3c0 1.5 2.9 2.7 6.4 2.7s6.4-1.2 6.4-2.7v-3"/>')
_IC_CALENDAR  = _SVG('<rect x="3.6" y="5" width="16.8" height="15" rx="2.6"/>'
                     '<path d="M3.6 9.5h16.8M8 3v3M16 3v3"/>')

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""<div class="scard" style="border-top:4px solid #2BD47E;">
      <div class="scard-icon" style="background:#F2FAF5;color:#2BD47E;">{_IC_CUSTOMERS}</div>
      <div class="scard-val" style="color:#15A35A;">{stats['total_customers']}</div>
      <div class="scard-label">客戶總數</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="scard" style="border-top:4px solid #10B981;">
      <div class="scard-icon" style="background:#ECFDF5;color:#10B981;">{_IC_PRODUCTS}</div>
      <div class="scard-val" style="color:#059669;">{stats['active_sns']}</div>
      <div class="scard-label">有效商品</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="scard" style="border-top:4px solid #F59E0B;">
      <div class="scard-icon" style="background:#FFFBEB;color:#F59E0B;">{_IC_MONEY}</div>
      <div class="scard-val" style="color:#D97706;font-size:1.55rem;">{total_str}</div>
      <div class="scard-label">總投資金額 (USD)</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""<div class="scard" style="border-top:4px solid #8B5CF6;">
      <div class="scard-icon" style="background:#F5F3FF;color:#8B5CF6;">{_IC_CALENDAR}</div>
      <div class="scard-val" style="color:#7C3AED;font-size:1.45rem;">{_now.strftime("%m/%d")}</div>
      <div class="scard-label">今日日期</div>
    </div>""", unsafe_allow_html=True)

# ── KO/KI 警示 + 近期比價 ─────────────────────────────────────
col_left, col_right = st.columns([3, 2])

prices = {}

with col_left:
    st.markdown("""<div class="sec-head">
      <div class="sec-head-icon" style="background:#FFF1F3;color:#F43F5E;"></div>
      <span class="sec-head-title">KO / KI 警示總覽</span>
    </div>""", unsafe_allow_html=True)

    with st.spinner("讀取即時股價中..."):
        sns_df = get_all_sns(status="active")

    if sns_df.empty:
        st.info("目前無有效商品資料")
    else:
        all_tickers = get_all_tickers_for_active_sns(sns_df)
        with st.spinner(f"取得 {len(all_tickers)} 個股票價格..."):
            prices = get_prices(all_tickers) if all_tickers else {}

        alerts_found = []
        for _, sn_row in sns_df.iterrows():
            sn = sn_row.to_dict()
            analysis = analyze_sn_status(sn, prices)
            if analysis["overall_status"] in ("ki_triggered", "ki_risk", "ko_triggered", "ko_risk"):
                alerts_found.append((sn, analysis))

        if not alerts_found:
            st.success("目前所有商品狀態正常，無警示")
        else:
            for sn, analysis in alerts_found:
                code = sn.get("product_code", "—")
                tickers = " / ".join([sn.get(f"underlying_{i}") for i in range(1, 6)
                                      if isinstance(sn.get(f"underlying_{i}"), str)])
                obs = str(sn.get("observation_date", ""))[:10]
                status = analysis["overall_status"]
                css_class = ("alert-card-ki" if status == "ki_triggered"
                             else "alert-card-ko" if status == "ko_triggered"
                             else "alert-card-warn")
                st.markdown(f"""<div class="{css_class}">
                    <strong>{analysis['status_emoji']} {code}</strong> &nbsp; {tickers}<br>
                    <span style="opacity:0.72;font-size:0.8rem">比價日: {obs} &nbsp;|&nbsp; {analysis['status_label']}</span>
                </div>""", unsafe_allow_html=True)

with col_right:
    st.markdown("""<div class="sec-head">
      <div class="sec-head-icon" style="background:#F2FAF5;color:#2BD47E;"></div>
      <span class="sec-head-title">近期比價日</span>
    </div>""", unsafe_allow_html=True)

    sns_df2 = get_all_sns(status="active")
    if not sns_df2.empty and "observation_date" in sns_df2.columns:
        today = _now.date()
        upcoming = sns_df2[
            pd.to_datetime(sns_df2["observation_date"]).dt.date >= today
        ].sort_values("observation_date").head(8)

        if upcoming.empty:
            st.info("近期無比價日")
        else:
            for _, row in upcoming.iterrows():
                obs = str(row.get("observation_date", ""))[:10]
                code = row.get("product_code", "—")
                t1 = row.get("underlying_1", "")
                t2 = row.get("underlying_2", "")
                tstr = f"{t1}/{t2}" if t2 else t1
                obs_date = pd.to_datetime(obs).date()
                days_left = (obs_date - today).days
                if days_left <= 3:
                    badge, chip_css = "", "background:#FFF1F3;color:#F43F5E;"
                elif days_left <= 7:
                    badge, chip_css = "", "background:#FFFBEB;color:#D97706;"
                else:
                    badge, chip_css = "", "background:#ECFDF5;color:#059669;"
                st.markdown(f"""<div class="obs-row">
                  <span>{badge}</span>
                  <span class="obs-code">{code}<br><span style="font-weight:400;color:#94a3b8;font-size:0.76rem">{tstr}</span></span>
                  <span class="obs-meta">{obs}</span>
                  <span class="obs-chip" style="{chip_css}">剩 {days_left} 天</span>
                </div>""", unsafe_allow_html=True)
    else:
        st.info("無資料")

# ── 主要標的現價 ──────────────────────────────────────────────
st.markdown("""<div class="sec-head">
  <div class="sec-head-icon" style="background:#ECFDF5;color:#10B981;"></div>
  <span class="sec-head-title">主要標的現價</span>
</div>""", unsafe_allow_html=True)

if not sns_df.empty and prices:
    unique_tickers = sorted(set(k for k, v in prices.items() if v is not None))
    if unique_tickers:
        px_html = '<div class="px-grid">'
        for ticker in unique_tickers[:12]:
            price = prices.get(ticker)
            if price:
                px_html += f"""<div class="px-card">
                  <div class="px-sym">{ticker}</div>
                  <div class="px-price">${price:,.2f}</div>
                </div>"""
            else:
                px_html += f"""<div class="px-card">
                  <div class="px-sym">{ticker}</div>
                  <div class="px-na">無法取得</div>
                </div>"""
        px_html += '</div>'
        st.markdown(px_html, unsafe_allow_html=True)
    else:
        st.info("暫無標的資料")
else:
    st.info("請先新增 SN 商品資料")

# ── 近期 SN 商品 ──────────────────────────────────────────────
st.markdown("""<div class="sec-head">
  <div class="sec-head-icon" style="background:#F5F3FF;color:#8B5CF6;"></div>
  <span class="sec-head-title">近期 SN 商品</span>
</div>""", unsafe_allow_html=True)

if not sns_df.empty:
    display_cols = ["product_code", "underlying_1", "underlying_2", "underlying_3",
                    "strike_pct", "coupon_pct", "observation_date", "status"]
    display_cols = [c for c in display_cols if c in sns_df.columns]
    df_show = sns_df[display_cols].copy()
    df_show = df_show.rename(columns={
        "product_code": "商品代號", "underlying_1": "標的1",
        "underlying_2": "標的2", "underlying_3": "標的3",
        "strike_pct": "執行價%", "coupon_pct": "配息%",
        "observation_date": "比價日", "status": "狀態"
    })
    for col in ["執行價%", "配息%"]:
        if col in df_show.columns:
            df_show[col] = df_show[col].apply(lambda x: f"{x*100:.2f}%" if pd.notna(x) else "—")
    df_show["狀態"] = df_show.get("狀態", "").map({
        "active": "有效", "ko_triggered": "KO觸發",
        "ki_triggered": "KI觸發", "expired": "到期", "matured": "結算"
    }).fillna("—")
    st.dataframe(df_show.head(10), use_container_width=True, hide_index=True)
else:
    st.info("尚無商品資料，請至「SN商品管理」新增")
