"""
即時圖表 - TradingView 嵌入
"""
import unicodedata
import streamlit as st
import streamlit.components.v1 as components
from utils.database import get_all_sns, get_all_customers, get_investments_by_customer


def _clean(t: str) -> str:
    return unicodedata.normalize("NFKC", t).lstrip("$").strip().upper()

st.set_page_config(page_title="即時圖表", page_icon="📈", layout="wide")

def _is_logged_in():
    if st.session_state.get("authenticated"):
        return True
    try:
        return st.user.is_logged_in
    except Exception:
        return False

if not _is_logged_in():
    st.error("請先登入")
    st.page_link("app.py", label="回到登入頁面", icon="🔑")
    st.stop()

from utils.ui_helpers import dog_header
dog_header("即時圖表")
st.caption("資料來源: TradingView · 即時報價")

# ── 建立客戶 → 標的 mapping ──────────────────────────────────────
@st.cache_data(ttl=300)
def _build_customer_ticker_map():
    customers = get_all_customers()
    result = {}
    all_tickers_set = []
    sn_info = {}

    sns_df = get_all_sns(status="active")

    for _, row in customers.iterrows():
        cid = str(row["id"])
        cname = row["name"]
        invs = get_investments_by_customer(cid)
        tickers = []
        for inv in invs:
            sn = inv.get("structured_notes") or {}
            if not sn or sn.get("status") != "active":
                continue
            ko = sn.get("ko_barrier")
            ki = sn.get("ki_barrier")
            code = sn.get("product_code", "")
            for i in range(1, 6):
                t = sn.get(f"underlying_{i}")
                if t and isinstance(t, str):
                    t = _clean(t)
                    if t not in tickers:
                        tickers.append(t)
                    if t not in sn_info:
                        sn_info[t] = {"ko": ko, "ki": ki, "product_code": code}
        if tickers:
            result[cname] = tickers
            for t in tickers:
                if t not in all_tickers_set:
                    all_tickers_set.append(t)

    return result, sorted(all_tickers_set), sn_info

customer_ticker_map, all_tickers, sn_info_map = _build_customer_ticker_map()

# ── PPT Export ───────────────────────────────────────────────────
with st.expander("📥 匯出 PowerPoint 簡報"):
    from utils.ppt_export import build_ppt

    # Customer selector for PPT
    customer_names = list(customer_ticker_map.keys())
    if customer_names:
        st.markdown("**依客戶選擇標的**")
        col_cust, col_mode = st.columns([3, 1])
        with col_mode:
            sel_mode = st.radio("模式", ["全部標的", "依客戶篩選"], horizontal=False)
        with col_cust:
            if sel_mode == "依客戶篩選":
                selected_customers_ppt = st.multiselect(
                    "選擇客戶 (可多選)",
                    options=customer_names,
                    placeholder="選擇客戶...",
                )
                if selected_customers_ppt:
                    auto_tickers = []
                    for c in selected_customers_ppt:
                        for t in customer_ticker_map.get(c, []):
                            if t not in auto_tickers:
                                auto_tickers.append(t)
                    st.caption(f"自動帶入標的: {', '.join(auto_tickers)}")
                else:
                    auto_tickers = all_tickers
            else:
                auto_tickers = all_tickers

    else:
        auto_tickers = all_tickers

    if not all_tickers:
        st.warning("目前無持倉標的")
    else:
        col_sel, col_per = st.columns([3, 1])
        with col_sel:
            selected_tickers = st.multiselect(
                "選擇要匯出的標的",
                options=sorted(all_tickers),
                default=sorted(auto_tickers),
                placeholder="選擇標的...",
            )
        with col_per:
            period_map = {
                "1個月": "1mo", "3個月": "3mo", "6個月": "6mo",
                "1年": "1y", "2年": "2y",
            }
            period_label = st.selectbox("圖表區間", list(period_map.keys()), index=2)
            selected_period = period_map[period_label]

        col_a, col_b = st.columns([2, 3])
        with col_a:
            if st.button("🐾 產生 PPT", type="primary", disabled=not selected_tickers):
                with st.spinner(f"正在產生 {len(selected_tickers)} 個標的圖表..."):
                    ppt_bytes = build_ppt(selected_tickers, sn_info_map, period=selected_period)
                st.session_state["ppt_bytes"] = ppt_bytes
                st.session_state["ppt_count"] = len(selected_tickers)

        if st.session_state.get("ppt_bytes"):
            fname = f"DOUU_WORK_{__import__('datetime').date.today().strftime('%Y%m%d')}.pptx"
            with col_b:
                st.download_button(
                    label=f"⬇️ 下載 PPT ({st.session_state['ppt_count']} 張投影片)",
                    data=st.session_state["ppt_bytes"],
                    file_name=fname,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    type="primary",
                )

st.markdown("---")

col_left, col_right = st.columns([1, 3])

with col_left:
    st.subheader("選擇標的")

    # Customer filter for chart
    if customer_ticker_map:
        filter_customer = st.selectbox(
            "依客戶篩選",
            options=["全部標的"] + list(customer_ticker_map.keys()),
            index=0,
        )
        if filter_customer != "全部標的":
            display_tickers = customer_ticker_map.get(filter_customer, all_tickers)
            st.caption(f"**{filter_customer}** 的標的")
        else:
            display_tickers = all_tickers
    else:
        display_tickers = all_tickers

    if display_tickers:
        selected = st.radio("股票代號", display_tickers, label_visibility="collapsed")
    else:
        selected = "NVDA"

    st.markdown("---")
    custom = st.text_input("自訂股票代號", placeholder="例: TSLA、2330.TW")
    if custom.strip():
        selected = custom.strip().upper()

    st.markdown("---")
    interval = st.selectbox("時間週期", ["D", "W", "M", "60", "30", "15"], index=0,
        format_func=lambda x: {"D": "日線", "W": "週線", "M": "月線",
                                "60": "60分鐘", "30": "30分鐘", "15": "15分鐘"}[x])
    theme = st.radio("主題", ["light", "dark"], horizontal=True,
                     format_func=lambda x: "淺色" if x == "light" else "深色")

with col_right:
    st.subheader(f"{selected} 走勢圖")

    tv_html = f"""
    <div class="tradingview-widget-container" style="height:550px">
      <div id="tv_chart" style="height:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true,
        "symbol": "{selected}",
        "interval": "{interval}",
        "timezone": "Asia/Taipei",
        "theme": "{theme}",
        "style": "1",
        "locale": "zh_TW",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "studies": ["RSI@tv-basicstudies", "MACD@tv-basicstudies"],
        "container_id": "tv_chart"
      }});
      </script>
    </div>
    """
    components.html(tv_html, height=570)

# ── 多圖同時顯示 ────────────────────────────────────────────────
if display_tickers and len(display_tickers) > 1:
    st.markdown("---")
    label = f"**{filter_customer}** 標的總覽" if (customer_ticker_map and filter_customer != "全部標的") else "📊 所有持倉標的總覽"
    st.subheader(label)
    st.caption("點選右上角可放大個別圖表")

    cols = st.columns(min(len(display_tickers), 2))
    for i, ticker in enumerate(display_tickers):
        with cols[i % 2]:
            mini_html = f"""
            <div class="tradingview-widget-container" style="height:320px">
              <div id="tv_mini_{i}" style="height:100%"></div>
              <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
              <script type="text/javascript">
              new TradingView.widget({{
                "autosize": true,
                "symbol": "{ticker}",
                "interval": "{interval}",
                "timezone": "Asia/Taipei",
                "theme": "{theme}",
                "style": "1",
                "locale": "zh_TW",
                "toolbar_bg": "#f1f3f6",
                "enable_publishing": false,
                "allow_symbol_change": false,
                "hide_top_toolbar": false,
                "hide_legend": true,
                "container_id": "tv_mini_{i}"
              }});
              </script>
            </div>
            """
            st.caption(f"**{ticker}**")
            components.html(mini_html, height=330)
