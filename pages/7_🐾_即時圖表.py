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

@st.cache_data(ttl=300)
def _fetch_ohlcv(ticker: str, period: str):
    import yfinance as yf
    from datetime import datetime, timedelta
    tk = yf.Ticker(ticker)
    if period == "18mo":
        start = (datetime.today() - timedelta(days=548)).strftime("%Y-%m-%d")
        hist = tk.history(start=start)
    else:
        hist = tk.history(period=period)
    if hist.index.tz is not None:
        hist.index = hist.index.tz_convert(None)
    return hist


def _render_plotly_chart(ticker: str, period: str, info: dict | None):
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        hist = _fetch_ohlcv(ticker, period)
        if hist.empty:
            st.warning(f"無法取得 {ticker} 資料")
            return

        # resample to weekly for long periods so candles are readable
        use_weekly = period in ("1y", "18mo", "2y", "3y", "4y", "5y")
        if use_weekly:
            agg = {
                "Open": "first", "High": "max",
                "Low": "min",  "Close": "last", "Volume": "sum",
            }
            hist = hist.resample("W").agg(agg).dropna()
        freq_label = "週線" if use_weekly else "日線"

        close = hist["Close"]
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rsi   = 100 - (100 / (1 + gain / loss))

        ema12     = close.ewm(span=12, adjust=False).mean()
        ema26     = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        sig_line  = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - sig_line

        up   = hist["Close"] >= hist["Open"]
        c_up = "#26a69a"
        c_dn = "#ef5350"
        bg   = "#131722"
        grid = "#1e2535"

        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            row_heights=[0.62, 0.19, 0.19],
            vertical_spacing=0.02,
        )

        fig.add_trace(go.Candlestick(
            x=hist.index,
            open=hist["Open"], high=hist["High"],
            low=hist["Low"],   close=hist["Close"],
            name=ticker,
            increasing=dict(line=dict(color=c_up, width=1), fillcolor=c_up),
            decreasing=dict(line=dict(color=c_dn, width=1), fillcolor=c_dn),
            showlegend=False,
            whiskerwidth=0.5,
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=hist.index, y=rsi,
            line=dict(color="#a78bfa", width=1.5),
            name="RSI", showlegend=False,
        ), row=2, col=1)
        for lvl, col in [(70, "#ef5350"), (30, "#26a69a")]:
            fig.add_hline(y=lvl, line_dash="dash", line_color=col,
                          line_width=0.8, opacity=0.5, row=2, col=1)
        fig.add_annotation(x=0, xref="x2 domain", y=75, yref="y2",
                           text="RSI 14", showarrow=False,
                           font=dict(color="#a78bfa", size=10), xanchor="left")

        bar_cols = [c_up if v >= 0 else c_dn for v in macd_hist]
        fig.add_trace(go.Bar(
            x=hist.index, y=macd_hist,
            marker_color=bar_cols, opacity=0.7,
            showlegend=False, name="Hist",
        ), row=3, col=1)
        fig.add_trace(go.Scatter(
            x=hist.index, y=macd_line,
            line=dict(color="#60a5fa", width=1.5),
            showlegend=False, name="MACD",
        ), row=3, col=1)
        fig.add_trace(go.Scatter(
            x=hist.index, y=sig_line,
            line=dict(color="#fb923c", width=1.5),
            showlegend=False, name="Signal",
        ), row=3, col=1)
        fig.add_annotation(x=0, xref="x3 domain", y=1, yref="y3 domain",
                           text="MACD 12/26/9", showarrow=False,
                           font=dict(color="#94a3b8", size=10), xanchor="left", yanchor="top")

        # ── 期初 / KO / KI reference lines ─────────────────────
        if info and info.get("initial_price"):
            init_p = float(info["initial_price"])
            ko     = info.get("ko")
            ki     = info.get("ki")

            ko_p = round(init_p * float(ko), 2) if ko else None
            ki_p = round(init_p * float(ki), 2) if ki else None

            ko_eq_init = ko_p is not None and abs(ko_p - init_p) < 0.01

            if ko_eq_init:
                fig.add_hline(
                    y=init_p, line_dash="dash", line_color="#4ade80", line_width=2,
                    annotation_text=f"KO = 期初 ${init_p:,.2f}  ",
                    annotation_font=dict(color="#4ade80", size=10),
                    annotation_position="top right", row=1, col=1,
                )
            else:
                fig.add_hline(
                    y=init_p, line_dash="dot", line_color="#FFD700", line_width=1.5,
                    annotation_text=f"  期初 ${init_p:,.2f}",
                    annotation_font=dict(color="#FFD700", size=10),
                    annotation_position="top left", row=1, col=1,
                )
                if ko_p:
                    fig.add_hline(
                        y=ko_p, line_dash="dash", line_color="#4ade80", line_width=1.5,
                        annotation_text=f"KO ${ko_p:,.2f}  ",
                        annotation_font=dict(color="#4ade80", size=10),
                        annotation_position="top right", row=1, col=1,
                    )
            if ki_p and (ki_p is None or abs(ki_p - init_p) >= 0.01):
                fig.add_hline(
                    y=ki_p, line_dash="dash", line_color="#f87171", line_width=1.5,
                    annotation_text=f"KI ${ki_p:,.2f}  ",
                    annotation_font=dict(color="#f87171", size=10),
                    annotation_position="bottom right", row=1, col=1,
                )

        fig.add_annotation(
            x=0, xref="x domain", y=1.02, yref="y domain",
            text=f"<b>{ticker}</b>  ({freq_label})",
            showarrow=False, font=dict(color="white", size=13),
            xanchor="left", yanchor="bottom",
        )

        fig.update_layout(
            height=700,
            paper_bgcolor=bg,
            plot_bgcolor=bg,
            xaxis_rangeslider_visible=False,
            margin=dict(l=10, r=90, t=40, b=10),
            font=dict(color="#94a3b8", size=11),
        )
        for i in range(1, 4):
            fig.update_xaxes(showgrid=True, gridcolor=grid, zeroline=False,
                             showticklabels=(i == 3), row=i, col=1,
                             tickfont=dict(color="#64748b"))
            fig.update_yaxes(showgrid=True, gridcolor=grid, zeroline=False,
                             side="right", row=i, col=1,
                             tickfont=dict(color="#64748b"))

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"無法產生圖表: {e}")


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
                init_p = sn.get(f"initial_price_{i}")
                if t and isinstance(t, str):
                    t = _clean(t)
                    if t not in tickers:
                        tickers.append(t)
                    if t not in sn_info:
                        sn_info[t] = {
                            "ko": ko, "ki": ki,
                            "product_code": code,
                            "initial_price": float(init_p) if init_p else None,
                        }
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
                "1年": "1y", "1年半": "18mo", "2年": "2y",
                "3年": "3y", "4年": "4y", "5年": "5y",
            }
            period_label = st.selectbox("圖表區間", list(period_map.keys()), index=2, key="ppt_period")
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
    chart_mode = st.radio(
        "圖表模式",
        ["📡 即時 (TradingView)", "📊 分析模式 (期初/KO/KI)"],
        index=0,
    )
    use_plotly = chart_mode.startswith("📊")
    interval = "D"
    theme = "light"

    if use_plotly:
        period_map_ui = {
            "1個月":"1mo","3個月":"3mo","6個月":"6mo",
            "1年":"1y","1年半":"18mo","2年":"2y",
            "3年":"3y","4年":"4y","5年":"5y",
        }
        period_label = st.selectbox("圖表區間", list(period_map_ui.keys()), index=2, key="chart_period")
        chart_period = period_map_ui[period_label]
    else:
        interval = st.selectbox("時間週期", ["D","W","M","60","30","15"], index=0,
            format_func=lambda x: {"D":"日線","W":"週線","M":"月線",
                                    "60":"60分鐘","30":"30分鐘","15":"15分鐘"}[x])
        theme = st.radio("主題", ["light","dark"], horizontal=True,
                         format_func=lambda x: "淺色" if x=="light" else "深色")

with col_right:
    st.subheader(f"{selected} 走勢圖")

    # ── 期初/KO/KI info card ────────────────────────────────────
    info = sn_info_map.get(selected)
    if info and info.get("initial_price"):
        from utils.stock_prices import get_price
        curr = get_price(selected)
        init_p = info["initial_price"]
        ko = info.get("ko")
        ki = info.get("ki")

        cols_info = st.columns(4)
        with cols_info[0]:
            st.metric("期初價格", f"${init_p:,.2f}")
        with cols_info[1]:
            if curr:
                perf = (curr / init_p - 1) * 100
                st.metric("現價", f"${curr:,.2f}", f"{perf:+.1f}%")
        with cols_info[2]:
            if ko and init_p:
                ko_price = init_p * ko
                if curr:
                    gap = (ko_price / curr - 1) * 100
                    st.metric("KO水位", f"${ko_price:,.2f}", f"距離 {gap:+.1f}%")
                else:
                    st.metric("KO水位", f"${ko_price:,.2f}", f"{ko*100:.0f}%")
        with cols_info[3]:
            if ki and init_p:
                ki_price = init_p * ki
                if curr:
                    gap = (curr / ki_price - 1) * 100
                    st.metric("KI水位", f"${ki_price:,.2f}", f"距離 {gap:+.1f}%")
                else:
                    st.metric("KI水位", f"${ki_price:,.2f}", f"{ki*100:.0f}%")
        st.divider()

    if use_plotly:
        _render_plotly_chart(selected, chart_period, info)
    else:
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
