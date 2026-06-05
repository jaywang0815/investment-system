"""
即時圖表 - TradingView 嵌入
"""
import unicodedata
import streamlit as st
import streamlit.components.v1 as components
from utils.database import get_all_sns


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

# ── PPT Export ───────────────────────────────────────────────────
with st.expander("📥 匯出 PowerPoint 簡報"):
    from utils.ppt_export import build_ppt

    # Build ticker → sn_info map
    _sns_df = get_all_sns(status="active")
    _all_tickers = []
    _sn_info = {}
    if not _sns_df.empty:
        for _, row in _sns_df.iterrows():
            ko = row.get("ko_barrier")
            ki = row.get("ki_barrier")
            code = row.get("product_code", "")
            for i in range(1, 6):
                t = row.get(f"underlying_{i}")
                if t and isinstance(t, str):
                    t = _clean(t)
                    if t not in _all_tickers:
                        _all_tickers.append(t)
                    if t not in _sn_info:
                        _sn_info[t] = {"ko": ko, "ki": ki, "product_code": code}

    if not _all_tickers:
        st.warning("目前無持倉標的")
    else:
        col_sel, col_per = st.columns([3, 1])
        with col_sel:
            selected_tickers = st.multiselect(
                "選擇要匯出的標的",
                options=sorted(_all_tickers),
                default=sorted(_all_tickers),
                placeholder="選擇標的...",
            )
        with col_per:
            period_map = {
                "1個月": "1mo",
                "3個月": "3mo",
                "6個月": "6mo",
                "1年":   "1y",
                "2年":   "2y",
            }
            period_label = st.selectbox("圖表區間", list(period_map.keys()), index=2)
            selected_period = period_map[period_label]

        col_a, col_b = st.columns([2, 3])
        with col_a:
            if st.button("🐾 產生 PPT", type="primary",
                         disabled=not selected_tickers):
                with st.spinner(f"正在產生 {len(selected_tickers)} 個標的圖表..."):
                    ppt_bytes = build_ppt(selected_tickers, _sn_info,
                                          period=selected_period)
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

# ── 從 SN 自動抓出所有標的股票 ──────────────────────────────
sns_df = get_all_sns(status="active")
tickers_from_sn = []
if not sns_df.empty:
    for i in range(1, 6):
        col = f"underlying_{i}"
        if col in sns_df.columns:
            vals = sns_df[col].dropna().tolist()
            tickers_from_sn += [_clean(v) for v in vals
                    if isinstance(v, str) and v.strip()]
tickers_from_sn = sorted(set(tickers_from_sn))

st.markdown("---")

col_left, col_right = st.columns([1, 3])

with col_left:
    st.subheader("選擇標的")

    if tickers_from_sn:
        st.caption("目前持倉標的")
        selected = st.radio("股票代號", tickers_from_sn, label_visibility="collapsed")
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

# ── 多圖同時顯示 ────────────────────────────────────────────
if tickers_from_sn and len(tickers_from_sn) > 1:
    st.markdown("---")
    st.subheader("📊 所有持倉標的總覽")
    st.caption("點選右上角可放大個別圖表")

    cols = st.columns(min(len(tickers_from_sn), 2))
    for i, ticker in enumerate(tickers_from_sn):
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
