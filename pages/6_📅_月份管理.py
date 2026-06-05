"""
月份管理頁面 - 直接在 App 新增/管理每月 SN 商品
不需要 Excel，直接在這裡操作
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime
from utils.database import (
    get_all_sns, get_all_customers, create_sn, update_sn, delete_sn,
    get_investments_by_sn, create_investment, delete_investment, get_supabase
)
from utils.stock_prices import get_prices, analyze_sn_status

st.set_page_config(page_title="月份管理", page_icon="📅", layout="wide")

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

st.title("📅 月份管理")
st.caption("直接在這裡新增每月 SN 商品，不需要 Excel")

# ── 初始化 session state ───────────────────────────────────────
if "selected_month" not in st.session_state:
    st.session_state.selected_month = None
if "show_add_sn" not in st.session_state:
    st.session_state.show_add_sn = False

# ── 取得所有月份 ───────────────────────────────────────────────
try:
    sns_df = get_all_sns()
except Exception:
    st.error("資料庫連線失敗，請確認設定")
    st.stop()

# 取得已有的月份清單
existing_months = []
if not sns_df.empty and "month_label" in sns_df.columns:
    existing_months = sorted(sns_df["month_label"].dropna().unique().tolist(),
                             key=lambda x: int(x.replace("月", "")) if x.replace("月", "").isdigit() else 99)

all_months = [f"{i}月" for i in range(1, 13)]

# ─────────────────────────────────────────────────────────────
# 上半區: 月份選擇列
# ─────────────────────────────────────────────────────────────
st.markdown("### 選擇月份")

month_cols = st.columns(13)

# 已有月份顯示為藍色按鈕，沒有的顯示灰色 +
for i, month in enumerate(all_months):
    with month_cols[i]:
        has_data = month in existing_months
        count = len(sns_df[sns_df["month_label"] == month]) if has_data and not sns_df.empty else 0

        if has_data:
            label = f"**{month}**\n{count}筆"
            btn_type = "primary" if st.session_state.selected_month == month else "secondary"
        else:
            label = f"{month}\n＋"
            btn_type = "secondary"

        if st.button(label, key=f"month_{month}", type=btn_type, use_container_width=True):
            st.session_state.selected_month = month
            st.session_state.show_add_sn = False
            st.rerun()

# 最後一格: 自訂月份
with month_cols[12]:
    if st.button("其他月份", use_container_width=True):
        st.session_state.show_custom_month = True

if st.session_state.get("show_custom_month"):
    custom = st.text_input("輸入月份 (例: 13月 或 Q1)", key="custom_month_input")
    if custom and st.button("確認"):
        st.session_state.selected_month = custom
        st.session_state.show_custom_month = False
        st.session_state.show_add_sn = False
        st.rerun()

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# 如果沒選月份
# ─────────────────────────────────────────────────────────────
if not st.session_state.selected_month:
    st.info("👆 請點選上方月份按鈕來查看或新增資料")

    if existing_months:
        st.markdown("**目前已有資料的月份:**")
        for m in existing_months:
            count = len(sns_df[sns_df["month_label"] == m])
            total_amt = 0
            try:
                month_sn_ids = sns_df[sns_df["month_label"] == m]["id"].tolist()
                for sid in month_sn_ids:
                    invs = get_investments_by_sn(sid)
                    total_amt += sum(i.get("amount_usd", 0) or 0 for i in invs)
            except Exception:
                pass
            st.markdown(f"- **{m}**: {count} 筆 SN" + (f" · 合計 USD {total_amt:,.0f}" if total_amt else ""))
    st.stop()

# ─────────────────────────────────────────────────────────────
# 已選月份 → 顯示該月資料
# ─────────────────────────────────────────────────────────────
selected = st.session_state.selected_month
has_data = selected in existing_months

# 該月的 SN 清單
if has_data and not sns_df.empty:
    month_sns = sns_df[sns_df["month_label"] == selected].copy()
else:
    month_sns = pd.DataFrame()

# 標題列
col_title, col_btn, col_del_all = st.columns([4, 1, 1])
with col_title:
    st.markdown(f"## {selected} SN 商品")
    if not month_sns.empty:
        st.caption(f"共 {len(month_sns)} 筆商品")
with col_btn:
    if st.button("➕ 新增 SN 商品", type="primary", use_container_width=True):
        st.session_state.show_add_sn = not st.session_state.show_add_sn
with col_del_all:
    if not month_sns.empty:
        if st.button("🗑️ 刪除整月", type="secondary", use_container_width=True):
            st.session_state[f"confirm_del_month_{selected}"] = True

if st.session_state.get(f"confirm_del_month_{selected}"):
    st.warning(f"⚠️ 確定刪除 **{selected}** 全部 {len(month_sns)} 筆 SN 商品？此動作不可復原！")
    dc1, dc2 = st.columns(2)
    with dc1:
        if st.button("✅ 確認刪除整月", type="primary", use_container_width=True):
            for sn_id in month_sns["id"].tolist():
                delete_sn(sn_id)
            st.session_state.pop(f"confirm_del_month_{selected}", None)
            st.session_state.selected_month = None
            st.success(f"✅ 已刪除 {selected} 全部資料")
            st.rerun()
    with dc2:
        if st.button("❌ 取消", use_container_width=True):
            st.session_state.pop(f"confirm_del_month_{selected}", None)
            st.rerun()

# ─────────────────────────────────────────────────────────────
# 新增 SN 表單 (內嵌)
# ─────────────────────────────────────────────────────────────
if st.session_state.show_add_sn:
    with st.container(border=True):
        st.markdown(f"### ➕ 新增 {selected} SN 商品")

        with st.form("add_sn_inline", clear_on_submit=True):
            # 基本資料
            col1, col2, col3 = st.columns(3)
            with col1:
                product_code = st.text_input("商品代號 *", placeholder="例: EQDS0602001")
            with col2:
                trade_date = st.date_input("交易日期", value=date.today())
            with col3:
                observation_date = st.date_input("比價日期 *")

            # 條件設定
            col4, col5, col6, col7 = st.columns(4)
            with col4:
                strike_pct = st.number_input("執行價 (%)", 0.0, 200.0, 80.0, 0.5,
                                              help="例: 填 80 → 執行價為期初價格的 80%")
            with col5:
                coupon_pct = st.number_input("配息率 (%/年)", 0.0, 200.0, 15.0, 0.5)
            with col6:
                ko_barrier = st.number_input("KO 水位 (%)", 0.0, 200.0, 100.0, 1.0,
                                              help="填 0 表示無 KO 條件")
            with col7:
                ki_barrier = st.number_input("KI 水位 (%)", 0.0, 200.0, 0.0, 1.0,
                                              help="填 0 表示無 KI 條件")

            # 標的股票 (5 欄)
            st.markdown("**標的股票及期初價格**")
            ucols = st.columns(5)
            underlyings = []
            init_prices = []
            for i, col in enumerate(ucols, 1):
                with col:
                    u = st.text_input(f"標的{i}", placeholder="NVDA", key=f"u_new_{i}")
                    p = st.number_input(f"期初價{i}", min_value=0.0, step=0.01,
                                        key=f"p_new_{i}", format="%.2f")
                    underlyings.append(u.strip().upper() if u.strip() else None)
                    init_prices.append(p if p > 0 else None)

            # 自動抓期初價格
            auto_fetch = st.checkbox("🔄 自動從 Yahoo Finance 抓取期初價格",
                                      help="勾選後送出時自動抓取，若有填入則以填入為準")

            # 客戶投資 (直接在同一個表單填)
            st.markdown("**客戶投資 (可新增多筆)**")
            customers_df = get_all_customers()
            customer_names = [""] + (customers_df["name"].tolist() if not customers_df.empty else [])

            inv_count = st.number_input("客戶筆數", min_value=0, max_value=20, value=1, step=1)
            inv_data = []
            if inv_count > 0:
                inv_cols_header = st.columns([3, 2])
                with inv_cols_header[0]:
                    st.caption("客戶姓名")
                with inv_cols_header[1]:
                    st.caption("投資金額 (USD)")

                for j in range(int(inv_count)):
                    inv_row = st.columns([3, 2])
                    with inv_row[0]:
                        cname = st.selectbox(f"客戶{j+1}", customer_names,
                                              key=f"inv_name_{j}")
                    with inv_row[1]:
                        camount = st.number_input(f"金額{j+1}", min_value=0,
                                                   step=10000, value=100000,
                                                   key=f"inv_amt_{j}")
                    if cname:
                        inv_data.append({"name": cname, "amount": camount})

            submitted = st.form_submit_button("✅ 新增此 SN 商品", type="primary",
                                               use_container_width=True)

            if submitted:
                if not product_code.strip():
                    st.error("請填寫商品代號")
                elif not observation_date:
                    st.error("請填寫比價日期")
                elif not any(underlyings):
                    st.error("請填寫至少一個標的股票")
                else:
                    # 自動抓期初價格
                    if auto_fetch:
                        tickers_to_fetch = [u for u in underlyings if u]
                        if tickers_to_fetch:
                            with st.spinner("抓取股票現價..."):
                                fetched = get_prices(tickers_to_fetch)
                            for idx, u in enumerate(underlyings):
                                if u and init_prices[idx] is None:
                                    init_prices[idx] = fetched.get(u)

                    # 建立 SN 資料
                    sn_data = {
                        "product_code": product_code.strip(),
                        "trade_date": str(trade_date),
                        "observation_date": str(observation_date),
                        "month_label": selected,
                        "strike_pct": strike_pct / 100,
                        "coupon_pct": coupon_pct / 100,
                        "ko_barrier": ko_barrier / 100 if ko_barrier > 0 else None,
                        "ki_barrier": ki_barrier / 100 if ki_barrier > 0 else None,
                        "status": "active",
                    }
                    for i in range(5):
                        sn_data[f"underlying_{i+1}"] = underlyings[i]
                        sn_data[f"initial_price_{i+1}"] = init_prices[i]

                    result = create_sn(sn_data)
                    if result:
                        sn_id = result["id"]
                        # 新增投資記錄
                        inv_ok = 0
                        for inv in inv_data:
                            cid_row = customers_df[customers_df["name"] == inv["name"]]
                            if not cid_row.empty:
                                create_investment(cid_row.iloc[0]["id"], sn_id, inv["amount"])
                                inv_ok += 1
                        st.success(f"✅ {product_code} 新增成功！投資記錄: {inv_ok} 筆")
                        st.session_state.show_add_sn = False
                        st.rerun()
                    else:
                        st.error("新增失敗，可能商品代號重複")

# ─────────────────────────────────────────────────────────────
# 該月 SN 清單
# ─────────────────────────────────────────────────────────────
if month_sns.empty:
    st.info(f"📭 {selected} 目前沒有 SN 商品，點選上方「新增 SN 商品」按鈕開始新增")
else:
    # 取得所有標的現價
    all_tickers = set()
    for _, row in month_sns.iterrows():
        for i in range(1, 6):
            t = row.get(f"underlying_{i}")
            if t and isinstance(t, str):
                all_tickers.add(t.strip().upper())

    prices = {}
    if all_tickers:
        with st.spinner("取得即時股價..."):
            prices = get_prices(list(all_tickers))

    # 計算該月總計
    total_month_amt = 0

    for _, sn_row in month_sns.iterrows():
        sn = sn_row.to_dict()
        sn_id = sn["id"]
        code = sn.get("product_code", "—")

        # 取得客戶投資
        investments = get_investments_by_sn(sn_id)
        inv_total = sum(i.get("amount_usd", 0) or 0 for i in investments)
        total_month_amt += inv_total
        inv_names = [i.get("customers", {}).get("name", "—") for i in investments]

        # 分析狀態
        analysis = analyze_sn_status(sn, prices)
        status_emoji = analysis.get("status_emoji", "❓")
        status_label = analysis.get("status_label", "")

        # 標的清單
        underlyings_list = []
        for i in range(1, 6):
            t = sn.get(f"underlying_{i}")
            ip = sn.get(f"initial_price_{i}")
            if t and isinstance(t, str):
                curr = prices.get(t.upper())
                if curr and ip and ip > 0:
                    perf = curr / ip * 100
                    underlyings_list.append(f"{t} ({perf:.1f}%)")
                else:
                    underlyings_list.append(t)

        # 卡片式顯示
        with st.container(border=True):
            col_main, col_status, col_action = st.columns([5, 2, 1])

            with col_main:
                # 標題行
                st.markdown(f"**{code}**")
                st.caption(f"標的: {'  /  '.join(underlyings_list)}")

                detail_cols = st.columns(4)
                with detail_cols[0]:
                    strike = sn.get("strike_pct")
                    st.markdown(f"執行價: **{strike*100:.1f}%**" if strike else "執行價: —")
                with detail_cols[1]:
                    coupon = sn.get("coupon_pct")
                    st.markdown(f"配息: **{coupon*100:.2f}%**" if coupon else "配息: —")
                with detail_cols[2]:
                    ko = sn.get("ko_barrier")
                    ki = sn.get("ki_barrier")
                    ko_str = f"KO {ko*100:.0f}%" if ko else "KO 無"
                    ki_str = f"KI {ki*100:.0f}%" if ki else "KI 無"
                    st.markdown(f"{ko_str}  ·  {ki_str}")
                with detail_cols[3]:
                    obs = str(sn.get("observation_date", ""))[:10]
                    st.markdown(f"比價日: **{obs}**")

                # 客戶投資
                if investments:
                    inv_strs = [f"{n} ${i.get('amount_usd', 0):,.0f}"
                                for n, i in zip(inv_names, investments)]
                    st.caption("客戶: " + "  ·  ".join(inv_strs))
                else:
                    st.caption("尚無客戶投資")

            with col_status:
                st.markdown(f"### {status_emoji}")
                st.caption(status_label)
                if inv_total:
                    st.markdown(f"**USD {inv_total:,.0f}**")

            with col_action:
                # 快速新增客戶投資
                if st.button("👤＋", key=f"add_inv_{sn_id}",
                              help="快速新增客戶投資", use_container_width=True):
                    st.session_state[f"expand_inv_{sn_id}"] = not st.session_state.get(f"expand_inv_{sn_id}", False)

                # 刪除
                if st.button("🗑️", key=f"del_{sn_id}",
                              help="刪除此商品", use_container_width=True):
                    st.session_state[f"confirm_del_{sn_id}"] = True

            # 快速新增客戶投資 (展開)
            if st.session_state.get(f"expand_inv_{sn_id}"):
                with st.form(f"quick_inv_{sn_id}"):
                    customers_df2 = get_all_customers()
                    existing_cids = {i.get("customers", {}).get("id") for i in investments}
                    available = customers_df2[~customers_df2["id"].isin(existing_cids)] if not customers_df2.empty else pd.DataFrame()

                    if available.empty:
                        st.info("所有客戶已加入此商品")
                        st.form_submit_button("關閉")
                    else:
                        qcol1, qcol2 = st.columns(2)
                        with qcol1:
                            q_name = st.selectbox("客戶", available["name"].tolist(), key=f"qname_{sn_id}")
                        with qcol2:
                            q_amt = st.number_input("金額 (USD)", min_value=1000,
                                                     step=10000, value=100000, key=f"qamt_{sn_id}")
                        if st.form_submit_button("✅ 新增", type="primary"):
                            cid = available[available["name"] == q_name]["id"].iloc[0]
                            create_investment(cid, sn_id, q_amt)
                            st.session_state[f"expand_inv_{sn_id}"] = False
                            st.rerun()

            # 確認刪除
            if st.session_state.get(f"confirm_del_{sn_id}"):
                st.warning(f"⚠️ 確定刪除 {code}？此動作不可復原")
                dc1, dc2 = st.columns(2)
                with dc1:
                    if st.button("✅ 確認刪除", key=f"yes_del_{sn_id}", type="primary"):
                        delete_sn(sn_id)
                        st.session_state.pop(f"confirm_del_{sn_id}", None)
                        st.rerun()
                with dc2:
                    if st.button("❌ 取消", key=f"no_del_{sn_id}"):
                        st.session_state.pop(f"confirm_del_{sn_id}", None)
                        st.rerun()

    # 月份合計
    st.markdown("---")
    col_sum1, col_sum2, col_sum3 = st.columns(3)
    with col_sum1:
        st.metric(f"{selected} 合計", f"USD {total_month_amt:,.0f}")
    with col_sum2:
        st.metric("商品數量", f"{len(month_sns)} 筆")
    with col_sum3:
        # 下個比價日
        future_obs = month_sns[
            pd.to_datetime(month_sns["observation_date"], errors="coerce").dt.date >= date.today()
        ].sort_values("observation_date")
        if not future_obs.empty:
            next_obs = str(future_obs.iloc[0]["observation_date"])[:10]
            st.metric("最近比價日", next_obs)
