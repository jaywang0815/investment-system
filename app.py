"""
DOUU WORK - 主應用程式
結構型商品 (Structured Notes) 管理平台
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta

st.set_page_config(
    page_title="DOUU WORK",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── 全域 CSS  (Smart-Home inspired redesign) ─────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ── Base ─────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {
    background: #EEF2FF !important;
    font-family: 'Inter', sans-serif !important;
}
.main .block-container {
    padding-top: 1.6rem;
    padding-bottom: 2.5rem;
    max-width: 1280px;
}

/* ── Sidebar ──────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #1E2E6B !important;
    border-right: none !important;
    box-shadow: 4px 0 24px rgba(30,46,107,0.18) !important;
}
[data-testid="stSidebar"] * { color: #c7d2fe !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.1) !important; }

[data-testid="stSidebarNavLink"] {
    border-radius: 14px !important;
    margin: 3px 8px !important;
    padding: 10px 14px !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    transition: all 0.2s !important;
    color: #a5b4fc !important;
}
[data-testid="stSidebarNavLink"]:hover {
    background: rgba(255,255,255,0.12) !important;
    color: #fff !important;
    transform: translateX(3px) !important;
}
[data-testid="stSidebarNavLink"][aria-selected="true"] {
    background: rgba(99,102,241,0.35) !important;
    color: #fff !important;
    box-shadow: 0 2px 12px rgba(99,102,241,0.3) !important;
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
    color: #1e2e6b !important;
    padding-bottom: 0 !important;
    border-bottom: none !important;
    margin-bottom: 1.2rem !important;
    letter-spacing: -0.3px !important;
}
h2 { font-size: 1.1rem !important; font-weight: 600 !important; color: #3730a3 !important; }
h3 { font-size: 0.95rem !important; font-weight: 600 !important; color: #4338ca !important; }

/* ── Metric cards ─────────────────────────────────── */
[data-testid="stMetric"] {
    background: #ffffff !important;
    border: none !important;
    border-radius: 20px !important;
    padding: 1.3rem 1.5rem !important;
    box-shadow: 0 4px 20px rgba(99,102,241,0.08), 0 1px 4px rgba(0,0,0,0.04) !important;
    transition: transform 0.2s, box-shadow 0.2s !important;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px rgba(99,102,241,0.14) !important;
}
[data-testid="stMetricLabel"] {
    color: #6b7280 !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}
[data-testid="stMetricValue"] {
    color: #1e2e6b !important;
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
    background: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%) !important;
    color: white !important;
    box-shadow: 0 4px 14px rgba(79,70,229,0.35) !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(79,70,229,0.45) !important;
}
.stButton > button[kind="secondary"] {
    background: white !important;
    border: 1.5px solid #e0e7ff !important;
    color: #4F46E5 !important;
}
.stButton > button[kind="secondary"]:hover {
    background: #EEF2FF !important;
    border-color: #6366F1 !important;
}

/* ── Tabs ─────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: #E0E7FF;
    padding: 5px;
    border-radius: 14px;
    gap: 4px;
    border-bottom: none !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px !important;
    padding: 7px 20px !important;
    font-weight: 500 !important;
    color: #6366F1 !important;
    background: transparent !important;
    font-size: 0.88rem !important;
}
.stTabs [aria-selected="true"] {
    background: white !important;
    color: #3730a3 !important;
    box-shadow: 0 2px 8px rgba(79,70,229,0.15) !important;
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
    border: 1.5px solid #e0e7ff !important;
    background: #fff !important;
    font-size: 0.9rem !important;
    transition: border 0.2s, box-shadow 0.2s !important;
}
[data-testid="stTextInput"] input:focus,
.stTextArea textarea:focus {
    border-color: #6366F1 !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
}

/* ── Expander ─────────────────────────────────────── */
[data-testid="stExpander"] {
    background: white !important;
    border: none !important;
    border-radius: 16px !important;
    overflow: hidden !important;
    margin-bottom: 8px !important;
    box-shadow: 0 2px 10px rgba(99,102,241,0.07) !important;
}
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    color: #3730a3 !important;
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
hr { border-color: #e0e7ff !important; margin: 1.2rem 0 !important; }

/* ── Scrollbar ────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #EEF2FF; border-radius: 4px; }
::-webkit-scrollbar-thumb { background: #c7d2fe; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #818cf8; }

/* ── Form ─────────────────────────────────────────── */
[data-testid="stForm"] {
    background: white !important;
    border-radius: 20px !important;
    padding: 1.5rem !important;
    border: none !important;
    box-shadow: 0 4px 20px rgba(99,102,241,0.08) !important;
}

/* ── Spinner ──────────────────────────────────────── */
[data-testid="stSpinner"] { color: #6366F1 !important; }

/* ── Success / Info / Warning / Error ────────────── */
.stSuccess { border-radius: 14px !important; }
.stInfo    { border-radius: 14px !important; }
.stWarning { border-radius: 14px !important; }
.stError   { border-radius: 14px !important; }
</style>
""", unsafe_allow_html=True)

# ── ⚙️ gear icon + hide settings from sidebar ────────────────
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
<a href="/系統設定" target="_self" class="gear-fab" title="系統設定">⚙️</a>
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
    st.markdown("## 🏦 DOUU WORK")
    st.markdown("---")
    st.warning("⚙️ **系統尚未完成設定**")
    st.markdown("請先前往「**系統設定**」頁面完成初始設定（約 5-10 分鐘）")
    st.page_link("pages/0_⚙️_系統設定.py", label="→ 前往系統設定", icon="⚙️")
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
        _cc.set("inv_auth", _cookie_token(), max_age=30 * 24 * 3600)

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
if _cookie_available and not st.session_state.authenticated and _cookie_ok():
    st.session_state.authenticated = True

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

    _logo = _img_b64("logo.png")
    logo_html = f'<img src="data:image/png;base64,{_logo}" style="width:88px;height:88px;">' if _logo else "🐾"

    st.markdown(f"""
    <style>
    .main .block-container {{
        max-width: 380px !important;
        margin: 0 auto !important;
        padding-top: 2.5rem !important;
    }}
    .pin-logo     {{ text-align:center; margin-bottom:0.4rem; }}
    .pin-title    {{ font-size:1.7rem; font-weight:800; color:#1E3A8A; text-align:center; display:block; margin-bottom:0.15rem; letter-spacing:0.04em; }}
    .pin-subtitle {{ font-size:0.88rem; color:#94a3b8; text-align:center; display:block; margin-bottom:1.6rem; }}
    .pin-error    {{ color:#ef4444; font-size:0.85rem; text-align:center; display:block; margin-top:0.5rem; }}
    </style>
    <div class="pin-logo">{logo_html}</div>
    <div class="pin-title">DOUU WORK</div>
    <div class="pin-subtitle">輸入 PIN 碼解鎖 🔐</div>
    """, unsafe_allow_html=True)

    if st.session_state.pin_error:
        st.markdown('<div class="pin-error">❌ PIN 不正確，請重試</div>', unsafe_allow_html=True)

    typed = st.text_input("PIN", value="", max_chars=pin_len,
                          type="password", placeholder="輸入 PIN 後按 Enter",
                          label_visibility="collapsed",
                          key="pin_keyboard")
    if typed:
        if typed == correct_pin:
            st.session_state.authenticated = True
            st.session_state.pin_error = False
            _set_cookie()
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
            st.error(f"❌ 帳號 **{st.user.email}** 無存取權限")
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
    _sb_logo = _img_b64("logo.png")
    _sb_dog  = _img_b64("dog_bw.png")
    logo_img = f'<img src="data:image/png;base64,{_sb_logo}" style="width:64px;height:64px;">' if _sb_logo else "🐾"
    dog_img  = f'<img src="data:image/png;base64,{_sb_dog}" style="width:100%;max-width:140px;opacity:0.75;margin-top:4px;">' if _sb_dog else ""
    st.markdown(f"""
    <div style='text-align:center; padding: 10px 0 6px 0;'>
        {logo_img}
        <div style='font-size:1.05rem; font-weight:800; color:white; margin-top:5px; letter-spacing:0.05em;'>DOUU WORK</div>
        <div style='font-size:0.7rem; color:rgba(255,255,255,0.5); margin-top:2px;'>Structured Notes</div>
        {dog_img}
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    if _use_google_auth and _google_logged_in:
        try:
            st.markdown(f"👤 &nbsp;**{st.user.name}**")
            st.caption(st.user.email)
        except Exception:
            st.markdown("👤 &nbsp;**已登入**")
        if st.button("登出", use_container_width=True):
            st.logout()
    else:
        st.markdown("👤 &nbsp;**管理員**")
        if st.button("登出", use_container_width=True):
            st.session_state.authenticated = False
            _del_cookie()
            st.rerun()
    st.markdown("---")

# ── 主頁面 ────────────────────────────────────────────────────
from utils.ui_helpers import dog_header
col_title, col_date = st.columns([4, 1])
with col_title:
    dog_header("首頁總覽")
with col_date:
    st.markdown(f"<div style='text-align:right; color:#64748b; padding-top:14px; font-size:0.85rem;'>📅 {date.today().strftime('%Y / %m / %d')}</div>", unsafe_allow_html=True)

# 引入工具模組
try:
    from utils.database import get_dashboard_stats, get_all_sns, get_all_customers
    from utils.stock_prices import get_prices, get_all_tickers_for_active_sns, analyze_sn_status
except ImportError as e:
    st.error(f"模組載入失敗: {e}\n請確認已執行 pip install -r requirements.txt")
    st.stop()

# 資料庫連線測試
try:
    stats = get_dashboard_stats()
    db_ok = True
except Exception as e:
    st.error(f"❌ 資料庫連線失敗: {e}")
    st.info("請確認 .streamlit/secrets.toml 中的 Supabase 設定正確")
    db_ok = False

if not db_ok:
    st.stop()

# ── 數字卡片 ──────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("👥 客戶總數", f"{stats['total_customers']} 人")
with c2:
    st.metric("📊 有效商品", f"{stats['active_sns']} 筆")
with c3:
    total_usd = stats.get('total_investment_usd', 0)
    st.metric("💰 總投資金額", f"USD {total_usd/1_000_000:.2f}M" if total_usd >= 1_000_000 else f"USD {total_usd:,.0f}")
with c4:
    st.metric("📅 今日日期", date.today().strftime("%m/%d"))

st.markdown("---")

# ── KO/KI 警示總覽 ────────────────────────────────────────────
col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("⚠️ KO / KI 警示")

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
            st.success("✅ 目前所有商品狀態正常，無警示")
        else:
            for sn, analysis in alerts_found:
                code = sn.get("product_code", "—")
                tickers = " / ".join([sn.get(f"underlying_{i}") for i in range(1, 6) if isinstance(sn.get(f"underlying_{i}"), str)])
                obs = str(sn.get("observation_date", ""))[:10]
                status = analysis["overall_status"]

                if status == "ki_triggered":
                    css_class = "alert-ki"
                elif status == "ko_triggered":
                    css_class = "alert-ko"
                else:
                    css_class = "alert-warn"

                st.markdown(f"""
                <div class="{css_class}">
                    <strong>{analysis['status_emoji']} {code}</strong> &nbsp; {tickers}<br>
                    比價日: {obs} &nbsp;|&nbsp; {analysis['status_label']}
                </div>
                """, unsafe_allow_html=True)

with col_right:
    st.subheader("📅 近期比價日")
    sns_df2 = get_all_sns(status="active")
    if not sns_df2.empty and "observation_date" in sns_df2.columns:
        today = date.today()
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
                    badge = "🔴"
                elif days_left <= 7:
                    badge = "🟡"
                else:
                    badge = "🟢"

                st.markdown(f"{badge} **{obs}** &nbsp; `{code}`")
                st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;{tstr} · 剩 {days_left} 天")
    else:
        st.info("無資料")

# ── 各標的股票現價 ────────────────────────────────────────────
st.markdown("---")
st.subheader("💹 主要標的現價")

if not sns_df.empty and prices:
    unique_tickers = sorted(set(k for k, v in prices.items() if v is not None))
    if unique_tickers:
        cols = st.columns(min(len(unique_tickers), 6))
        for i, ticker in enumerate(unique_tickers[:12]):
            price = prices.get(ticker)
            with cols[i % len(cols)]:
                if price:
                    st.metric(ticker, f"${price:,.2f}")
                else:
                    st.metric(ticker, "無法取得")
else:
    st.info("請先新增 SN 商品資料")

# ── 最新活動 ─────────────────────────────────────────────────
st.markdown("---")
st.subheader("📋 近期 SN 商品")
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
        "active": "✅ 有效", "ko_triggered": "🟢 KO觸發",
        "ki_triggered": "🔴 KI觸發", "expired": "⏹ 到期", "matured": "✓ 結算"
    }).fillna("—")
    st.dataframe(df_show.head(10), use_container_width=True, hide_index=True)
else:
    st.info("尚無商品資料，請至「SN商品管理」新增")
