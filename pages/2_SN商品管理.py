"""
SN 商品管理頁面
"""
import streamlit as st
import pandas as pd
from datetime import date
from utils.database import (
    get_all_sns, get_all_customers, create_sn, update_sn, delete_sn,
    get_investments_by_sn, create_investment, delete_investment
)
from utils.stock_prices import get_prices, analyze_sn_status, get_sn_underlyings, get_price_on, clean_ticker

st.set_page_config(page_title="SN商品管理", page_icon=None, layout="wide")

from utils.ui_helpers import dog_header, require_auth
dog_header("SN商品管理")
require_auth()

tab1, tab2, tab3 = st.tabs(["商品列表", "新增商品", "商品詳情"])

# ──────────────────────────────────────────────────────────────
# Tab 1: 商品列表 + 即時狀態
# ──────────────────────────────────────────────────────────────
with tab1:
    status_filter = st.selectbox(
        "篩選狀態",
        ["全部", "有效(active)", "KO觸發", "KI觸發", "已到期"],
        index=0
    )
    status_map = {
        "全部": None, "有效(active)": "active",
        "KO觸發": "ko_triggered", "KI觸發": "ki_triggered", "已到期": "expired"
    }
    sns_df = get_all_sns(status=status_map[status_filter])

    if sns_df.empty:
        st.info("尚無商品資料")
    else:
        # 取得所有標的現價
        from utils.stock_prices import get_all_tickers_for_active_sns
        all_tickers = get_all_tickers_for_active_sns(sns_df)
        prices = {}
        if all_tickers:
            with st.spinner(f"取得 {len(all_tickers)} 個股票現價..."):
                prices = get_prices(all_tickers)

        # ดึงข้อมูลการลงทุนทั้งหมดในครั้งเดียว
        from utils.database import get_all_investments
        all_inv_df = get_all_investments()
        inv_by_sn = {}
        if not all_inv_df.empty:
            for sn_id, grp in all_inv_df.groupby("sn_id"):
                inv_by_sn[sn_id] = {
                    "names": "、".join(grp["customer_name"].dropna().tolist()),
                    "total": grp["amount_usd"].sum()
                }

        def _v(val):
            """Return None if val is None, NaN, or empty string."""
            if val is None:
                return None
            try:
                import math
                if isinstance(val, float) and math.isnan(val):
                    return None
            except Exception:
                pass
            return val if val != "" else None

        def _pct(val, decimals=0):
            v = _v(val)
            return f"{v*100:.{decimals}f}%" if v is not None else "—"

        def _num(val, decimals=0):
            v = _v(val)
            return f"{v:,.{decimals}f}" if v is not None else "—"

        # 建立顯示表格
        rows = []
        for _, sn in sns_df.iterrows():
            sn_dict = sn.to_dict()
            analysis = analyze_sn_status(sn_dict, prices)

            worst = analysis.get("worst_performance")
            worst_str = f"{worst*100:.1f}%" if _v(worst) is not None else "—"

            inv_info = inv_by_sn.get(sn_dict.get("id"), {})
            total_usd = inv_info.get("total", 0)

            row = {
                "代號": sn.get("product_code", "—"),
                "執行價%": _pct(sn.get("strike_pct"), 1),
                "配息%": _pct(sn.get("coupon_pct"), 2),
                "KO": _pct(sn.get("ko_barrier")),
                "KI": _pct(sn.get("ki_barrier")),
                "比價日": str(sn.get("observation_date", ""))[:10],
                "出場日": str(_v(sn.get("exit_date")) or "")[:10] or "—",
                "暫結": _num(sn.get("temp_settlement")),
                "CHU": _v(sn.get("chu")) or "—",
                "下單金(USD)": _num(sn.get("total_order_amount")),
                "投資金額(USD)": f"{total_usd:,.0f}" if total_usd else "—",
                "投資客戶": inv_info.get("names", "—"),
                "最差表現": worst_str,
                "狀態": f"{analysis['status_emoji']} {analysis['status_label']}",
            }
            for i in range(1, 6):
                row[f"標的{i}"] = _v(sn.get(f"underlying_{i}")) or "—"
                row[f"期初{i}"] = _num(sn.get(f"initial_price_{i}"), 2)

            rows.append(row)

        result_df = pd.DataFrame(rows)
        # จัดลำดับคอลัมน์: 代號 ก่อน แล้วตาม 標的1-5 期初1-5
        col_order = ["代號",
                     "標的1","期初1","標的2","期初2","標的3","期初3","標的4","期初4","標的5","期初5",
                     "執行價%","配息%","KO","KI","比價日","出場日","暫結","CHU",
                     "下單金(USD)","投資金額(USD)","投資客戶","最差表現","狀態"]
        result_df = result_df[[c for c in col_order if c in result_df.columns]]
        styled = result_df.style.apply(
            lambda row: [
                "background-color: #f0f4fa" if row.name % 2 != 0 else "background-color: white"
                for _ in row
            ],
            axis=1
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)

        # 股票現價摘要
        st.markdown("---")
        st.subheader("標的現價摘要")
        if prices:
            price_cols = st.columns(min(len(prices), 6))
            for i, (ticker, price) in enumerate(sorted(prices.items())):
                with price_cols[i % len(price_cols)]:
                    if price:
                        st.metric(ticker, f"${price:,.2f}")
                    else:
                        st.metric(ticker, "無法取得", delta="")

# ──────────────────────────────────────────────────────────────
# Tab 2: 新增 SN 商品
# ──────────────────────────────────────────────────────────────
with tab2:
    # ── 乾淨、現代的版面樣式 ───────────────────────────────────
    st.markdown("""
    <style>
      .sn-sec{font-size:14px;font-weight:700;color:#1E3A8A;letter-spacing:.3px;
              margin:22px 0 10px;padding-left:10px;border-left:4px solid #1E3A8A;}
      .sn-tk{font-size:19px;font-weight:800;color:#1E3A8A;text-align:center;
             margin:2px 0 -4px;min-height:24px;line-height:1.2;}
      .sn-tk-empty{font-size:12px;color:#cbd5e1;text-align:center;
                   margin:2px 0 -4px;min-height:24px;}
      div[data-testid="stNumberInput"] input,
      div[data-testid="stTextInput"] input{border-radius:8px;}
      div[data-baseweb="select"]>div{border-radius:8px;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("#### 新增結構型商品")
    st.caption("欄位順序與 Excel 相同；標的可從清單選擇 (全美股+ETF) 或自訂，填好交易日可一鍵帶入期初價")

    NEW_TICKER = "自訂…"

    @st.cache_data(ttl=600)
    def _known_tickers():
        from utils.stock_prices import get_symbol_universe
        s = set(get_symbol_universe())
        try:
            from utils.database import get_supabase
            sb = get_supabase()
            rows = sb.table("structured_notes").select(
                "underlying_1,underlying_2,underlying_3,underlying_4,underlying_5"
            ).execute().data or []
            for r in rows:
                for i in range(1, 6):
                    t = r.get(f"underlying_{i}")
                    if t and isinstance(t, str):
                        s.add(clean_ticker(t))
        except Exception:
            pass
        return sorted(s)

    known = _known_tickers()

    def _picked(i):
        sel = st.session_state.get(f"sel{i}", "")
        if sel == NEW_TICKER:
            sel = st.session_state.get(f"cust{i}", "")
        return clean_ticker(sel) if sel else None

    def _autofill_prices():
        td = str(st.session_state.get("f_trade", date.today()))
        for i in range(1, 6):
            t = _picked(i)
            if t:
                pr = get_price_on(t, td)
                if pr is not None:
                    st.session_state[f"p{i}"] = float(pr)

    # ── 基本資料 (日期 / 代號 / 比價 / 月份) ──────────────────────
    st.markdown('<div class="sn-sec">基本資料</div>', unsafe_allow_html=True)
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        trade_date = st.date_input("日期 (交易日)", value=date.today(), key="f_trade")
    with b2:
        product_code = st.text_input("代號 *", placeholder="EQDS05027345", key="f_code")
    with b3:
        observation_date = st.date_input("比價 (觀察日)", key="f_obs")
    with b4:
        month_label = st.selectbox("所屬月份",
            ["5月","6月","7月","8月","9月","10月","11月","12月","1月","2月","3月","4月"], key="f_month")

    # ── 標的股票 (標的1-5 + 期初價) ─────────────────────────────
    st.markdown('<div class="sn-sec">標的股票 (最多 5 檔，可日後再補)</div>', unsafe_allow_html=True)
    cols_u = st.columns(5)
    for i, col in enumerate(cols_u, 1):
        with col:
            sel = st.selectbox(f"標的{i}", [""] + known + [NEW_TICKER], key=f"sel{i}")
            if sel == NEW_TICKER:
                st.text_input("自訂代號", key=f"cust{i}", placeholder="e.g. PLTR",
                              label_visibility="collapsed")
            tk = _picked(i)
            if tk:
                st.markdown(f'<div class="sn-tk">{tk}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="sn-tk-empty">—</div>', unsafe_allow_html=True)
            st.number_input("期初價", min_value=0.0, step=0.01, format="%.2f", key=f"p{i}")
    st.button("依交易日自動帶入期初價", on_click=_autofill_prices, use_container_width=True)

    # ── 商品條件 (執行價 / 配息 / KO / KI) ───────────────────────
    st.markdown('<div class="sn-sec">商品條件</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        strike_pct = st.number_input("執行價 (%)", min_value=0.0, max_value=200.0,
                                      value=80.0, step=0.5, key="f_strike")
    with c2:
        coupon_pct = st.number_input("配息 (%)", min_value=0.0, max_value=200.0,
                                      value=15.0, step=0.5, key="f_coupon")
    with c3:
        ko_barrier = st.number_input("KO提前 (%)", min_value=0.0, max_value=200.0,
                                      value=100.0, step=1.0, key="f_ko", help="填 0 表示無 KO")
    with c4:
        ki_barrier = st.number_input("KI下限 (%)", min_value=0.0, max_value=200.0,
                                      value=0.0, step=1.0, key="f_ki", help="填 0 表示無 KI")

    # ── 其他 (出場 / 暫結 / CHU / 下單金) ───────────────────────
    st.markdown('<div class="sn-sec">其他 (選填)</div>', unsafe_allow_html=True)
    o1, o2, o3, o4 = st.columns(4)
    with o1:
        has_exit = st.checkbox("有出場日", key="f_has_exit")
        exit_date = st.date_input("出場日", key="f_exit") if has_exit else None
    with o2:
        temp_settlement = st.number_input("暫結", min_value=0.0, step=1000.0,
                                           value=0.0, format="%.0f", key="f_temp")
    with o3:
        chu = st.text_input("CHU", key="f_chu", placeholder="—")
    with o4:
        total_order = st.number_input("下單金 (USD)", min_value=0, step=10000, value=0, key="f_order")

    st.markdown("")
    if st.button("新增商品", type="primary", use_container_width=True):
        underlyings = [_picked(i) for i in range(1, 6)]
        initial_prices = [st.session_state.get(f"p{i}") or None for i in range(1, 6)]
        if not product_code.strip():
            st.error("請填寫代號")
        elif not any(underlyings):
            st.error("請至少選擇一個標的")
        elif any(underlyings[i] and not initial_prices[i] for i in range(5)):
            st.error("有標的缺少期初價 — 可按「自動帶入期初價」或手動填寫")
        else:
            # 驗證自訂代號是否查得到報價 (避免打錯)
            bad = [underlyings[i] for i in range(5)
                   if underlyings[i] and underlyings[i] not in known and get_price_on(underlyings[i], str(trade_date)) is None]
            if bad:
                st.error(f"查不到報價的代號: {', '.join(bad)} — 請確認拼字")
            else:
                sn_data = {
                    "product_code": product_code.strip(),
                    "trade_date": str(trade_date),
                    "observation_date": str(observation_date),
                    "month_label": month_label,
                    "strike_pct": strike_pct / 100,
                    "coupon_pct": coupon_pct / 100,
                    "ko_barrier": ko_barrier / 100 if ko_barrier > 0 else None,
                    "ki_barrier": ki_barrier / 100 if ki_barrier > 0 else None,
                    "exit_date": str(exit_date) if exit_date else None,
                    "temp_settlement": temp_settlement or None,
                    "chu": chu.strip() or None,
                    "total_order_amount": total_order or None,
                    "status": "active",
                }
                for i in range(5):
                    sn_data[f"underlying_{i+1}"] = underlyings[i]
                    sn_data[f"initial_price_{i+1}"] = initial_prices[i]

                result = create_sn(sn_data)
                if result:
                    for i in range(1, 6):
                        st.session_state.pop(f"sel{i}", None)
                        st.session_state.pop(f"cust{i}", None)
                        st.session_state.pop(f"p{i}", None)
                    st.session_state.pop("f_code", None)
                    st.success(f"商品 **{product_code}** 新增成功！客戶持倉可到「商品詳情」分頁逐筆加入。")
                    st.rerun()
                else:
                    st.error("新增失敗")

# ──────────────────────────────────────────────────────────────
# Tab 3: 商品詳情 + 客戶投資管理
# ──────────────────────────────────────────────────────────────
with tab3:
    sns_df = get_all_sns()

    if sns_df.empty:
        st.info("尚無商品資料")
    else:
        product_codes = sns_df["product_code"].tolist()
        selected_code = st.selectbox("選擇商品", product_codes)

        sn_row = sns_df[sns_df["product_code"] == selected_code].iloc[0]
        sn_dict = sn_row.to_dict()
        sn_id = sn_dict["id"]

        # 取得現價
        underlyings = get_sn_underlyings(sn_dict)
        tickers = [u["ticker"] for u in underlyings]
        prices = {}
        if tickers:
            with st.spinner("取得現價..."):
                prices = get_prices(tickers)

        analysis = analyze_sn_status(sn_dict, prices)

        # 商品概覽
        col_info, col_status = st.columns([2, 1])
        with col_info:
            st.markdown(f"### {selected_code}")
            ticker_str = " / ".join(tickers)
            st.markdown(f"**標的:** {ticker_str}")
            st.markdown(f"**比價日:** {str(sn_dict.get('observation_date',''))[:10]}")
            strike = sn_dict.get("strike_pct")
            coupon = sn_dict.get("coupon_pct")
            ko = sn_dict.get("ko_barrier")
            ki = sn_dict.get("ki_barrier")
            col_a, col_b = st.columns(2)
            with col_a:
                if strike:
                    st.markdown(f"**執行價:** {strike*100:.2f}%")
                if coupon:
                    st.markdown(f"**配息率:** {coupon*100:.2f}%")
            with col_b:
                if ko:
                    st.markdown(f"**KO水位:** {ko*100:.0f}%")
                if ki:
                    st.markdown(f"**KI水位:** {ki*100:.0f}%")

        with col_status:
            st.markdown(f"## {analysis['status_emoji']}")
            st.markdown(f"**{analysis['status_label']}**")
            worst = analysis.get("worst_performance")
            if worst:
                st.markdown(f"最差表現: **{worst*100:.1f}%**")

        # 各標的現價
        st.markdown("---")
        st.subheader("各標的現況")
        for d in analysis.get("details", []):
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.markdown(f"**{d['ticker']}**")
            with col2:
                if d.get("initial_price"):
                    st.markdown(f"期初: ${d['initial_price']:,.2f}")
            with col3:
                curr = d.get("current_price")
                if curr:
                    st.markdown(f"現價: **${curr:,.2f}**")
                else:
                    st.markdown("現價: 取得中")
            with col4:
                chg = d.get("change_pct")
                if chg is not None:
                    color = "" if chg >= 0 else ""
                    st.markdown(f"{color} {chg:+.2f}%")
            with col5:
                st.markdown(f"{d.get('ko_status','—')} {d.get('ki_status','—')}")

        # 客戶投資列表
        st.markdown("---")
        st.subheader("客戶投資列表")
        investments = get_investments_by_sn(sn_id)
        if not investments:
            st.info("此商品尚無客戶投資記錄")
        else:
            inv_total = sum(i.get("amount_usd", 0) or 0 for i in investments)
            st.metric("投資客戶數", f"{len(investments)} 人",
                      delta=f"合計 USD {inv_total:,.0f}")

            inv_df = pd.DataFrame([{
                "客戶": i.get("customers", {}).get("name", "—"),
                "投資金額 (USD)": f"${i.get('amount_usd', 0):,.0f}",
                "投資記錄ID": i.get("id")
            } for i in investments])
            st.dataframe(inv_df[["客戶", "投資金額 (USD)"]], use_container_width=True, hide_index=True)

        # 新增客戶投資
        st.markdown("---")
        st.subheader("新增客戶投資")
        customers_df = get_all_customers()
        if not customers_df.empty:
            with st.form(f"add_inv_{sn_id}"):
                existing_customer_ids = {i.get("customers", {}).get("id") for i in investments}
                available = customers_df[~customers_df["id"].isin(existing_customer_ids)]

                if available.empty:
                    st.info("所有客戶均已加入此商品")
                else:
                    inv_customer = st.selectbox("選擇客戶", available["name"].tolist())
                    inv_amount = st.number_input("投資金額 (USD)", min_value=1000, step=10000, value=100000)

                    if st.form_submit_button("新增投資記錄"):
                        cid = available[available["name"] == inv_customer]["id"].iloc[0]
                        result = create_investment(cid, sn_id, inv_amount)
                        if result:
                            st.success(f"已新增 {inv_customer} 投資 USD {inv_amount:,.0f}")
                            st.rerun()
                        else:
                            st.error("新增失敗")

        # 更新商品狀態
        st.markdown("---")
        with st.expander("更新商品狀態"):
            new_status = st.selectbox("狀態", [
                "active", "ko_triggered", "ki_triggered", "expired", "matured"
            ], index=["active","ko_triggered","ki_triggered","expired","matured"].index(
                sn_dict.get("status", "active")
            ))
            status_labels = {
                "active": "有效", "ko_triggered": "KO觸發",
                "ki_triggered": "KI觸發", "expired": "到期", "matured": "結算"
            }
            if st.button(f"更新為: {status_labels[new_status]}"):
                update_sn(sn_id, {"status": new_status})
                st.success("狀態已更新")
                st.rerun()
