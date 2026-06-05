"""
投資管理系統 - 主應用程式
結構型商品 (Structured Notes) 管理平台
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta

st.set_page_config(
    page_title="投資管理系統",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── 自訂 CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1E3A8A, #3B82F6);
        color: white;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin: 5px;
    }
    .metric-card .number { font-size: 2em; font-weight: bold; }
    .metric-card .label { font-size: 0.9em; opacity: 0.85; margin-top: 4px; }
    .alert-ki { background: #FEF2F2; border-left: 4px solid #DC2626; padding: 8px 12px; border-radius: 4px; margin: 4px 0; }
    .alert-ko { background: #F0FDF4; border-left: 4px solid #16A34A; padding: 8px 12px; border-radius: 4px; margin: 4px 0; }
    .alert-warn { background: #FFF7ED; border-left: 4px solid #EA580C; padding: 8px 12px; border-radius: 4px; margin: 4px 0; }
    [data-testid="stSidebarNav"] { font-size: 1.05em; }
</style>
""", unsafe_allow_html=True)

# ── 檢查設定是否完成 ─────────────────────────────────────────
try:
    _setup_complete = bool(st.secrets.get("SUPABASE_URL") and st.secrets.get("SUPABASE_KEY"))
except Exception:
    _setup_complete = False

if not _setup_complete:
    st.markdown("## 🏦 投資管理系統")
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

def _check_password(pw: str, stored_hash: str) -> bool:
    return hashlib.sha256(pw.encode()).hexdigest() == stored_hash

_use_google_auth = bool(
    st.secrets.get("auth", {}).get("google", {}).get("client_id")
)
_admin_password_hash = st.secrets.get("ADMIN_PASSWORD_HASH", "")
_admin_password_plain = st.secrets.get("ADMIN_PASSWORD", "")

# ── Cookie 管理 (記住登入狀態 7 天) ──────────────────────────
try:
    import extra_streamlit_components as stx
    _cm = stx.CookieManager(key="__inv_cm")
    _COOKIE_NAME = "inv_auth"
    _COOKIE_SECRET = st.secrets.get("COOKIE_SECRET", "inv2024secret")

    def _cookie_token():
        src = f"{_admin_password_plain or _admin_password_hash}:{_COOKIE_SECRET}"
        return hashlib.sha256(src.encode()).hexdigest()[:24]

    def _set_cookie():
        _cm.set(_COOKIE_NAME, _cookie_token(), max_age=7 * 24 * 3600)

    def _del_cookie():
        try:
            _cm.delete(_COOKIE_NAME)
        except Exception:
            pass

    def _cookie_ok():
        try:
            return _cm.get(_COOKIE_NAME) == _cookie_token()
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
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.image("https://img.icons8.com/color/96/bank-building.png", width=80)
        st.markdown("## 結構型商品投資管理系統")
        st.markdown("---")

        if _use_google_auth:
            st.info("請使用授權的 Gmail 帳號登入")
            if st.button("🔐 使用 Gmail 登入", use_container_width=True, type="primary"):
                st.login("google")
        else:
            st.info("請輸入管理員密碼")
            pw_input = st.text_input("密碼", type="password", placeholder="輸入密碼後按 Enter")
            if st.button("🔑 登入", use_container_width=True, type="primary") or pw_input:
                if pw_input:
                    correct = False
                    if _admin_password_plain and pw_input == _admin_password_plain:
                        correct = True
                    elif _admin_password_hash and _check_password(pw_input, _admin_password_hash):
                        correct = True
                    elif not _admin_password_plain and not _admin_password_hash:
                        correct = True

                    if correct:
                        st.session_state.authenticated = True
                        _set_cookie()
                        st.rerun()
                    else:
                        st.error("❌ 密碼錯誤")

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("本系統僅供授權人員使用")
    st.stop()

# ── Gmail 權限檢查 (只在 Google 模式下檢查) ───────────────────
if _use_google_auth and _google_logged_in:
    try:
        allowed = st.secrets.get("allowed_emails", [])
        user_email = st.user.email
        if allowed and user_email not in allowed:
            st.error(f"❌ 帳號 **{user_email}** 無存取權限")
            if st.button("登出"):
                st.logout()
            st.stop()
    except Exception:
        pass

# ── 側邊欄 ────────────────────────────────────────────────────
with st.sidebar:
    if _use_google_auth and _google_logged_in:
        try:
            st.markdown(f"👤 **{st.user.name}**")
            st.caption(st.user.email)
        except Exception:
            st.markdown("👤 **已登入**")
        if st.button("🚪 登出", use_container_width=True):
            st.logout()
    else:
        st.markdown("👤 **管理員**")
        if st.button("🚪 登出", use_container_width=True):
            st.session_state.authenticated = False
            _del_cookie()
            st.rerun()
    st.markdown("---")

# ── 主頁面 ────────────────────────────────────────────────────
st.title("🏦 投資管理系統 - 首頁總覽")
st.caption(f"今日: {date.today().strftime('%Y年%m月%d日')}")

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
