"""
客戶管理頁面
"""
import streamlit as st
import pandas as pd
import io
from datetime import date
from utils.database import (
    get_all_customers, get_customer, create_customer,
    update_customer, delete_customer, get_investments_by_customer,
    get_investments_by_sn, get_all_sns, get_all_investments
)
from utils.stock_prices import get_prices, analyze_sn_status, get_sn_underlyings

st.set_page_config(page_title="客戶管理", page_icon="👥", layout="wide")

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

st.title("👥 客戶管理")

# ── 標籤頁 ─────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📋 客戶列表", "➕ 新增客戶", "🔍 客戶詳情", "📤 匯出資料"])

# ──────────────────────────────────────────────────────────────
# Tab 1: 客戶列表
# ──────────────────────────────────────────────────────────────
with tab1:
    customers_df = get_all_customers()

    if customers_df.empty:
        st.info("尚無客戶資料，請至「新增客戶」頁面新增")
    else:
        # 搜尋
        search = st.text_input("🔍 搜尋客戶姓名", placeholder="輸入姓名...")
        if search:
            customers_df = customers_df[
                customers_df["name"].str.contains(search, na=False)
            ]

        # 顯示統計
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("客戶總數", len(customers_df))
        with col2:
            ordered = customers_df["ordered"].sum() if "ordered" in customers_df.columns else 0
            st.metric("已下單", int(ordered))
        with col3:
            total_usd = customers_df["usd_amount"].sum() if "usd_amount" in customers_df.columns else 0
            st.metric("USD 總額度", f"${total_usd:,.0f}")

        st.markdown("---")

        # 客戶表格
        display_df = customers_df.copy()
        bool_cols = ["unified_account", "pi_signed", "ordered"]
        for col in bool_cols:
            if col in display_df.columns:
                display_df[col] = display_df[col].map({True: "✅", False: "❌", None: "—"})

        col_names = {
            "name": "姓名", "unified_account": "統一開戶",
            "pi_signed": "PI見簽", "ordered": "已下單",
            "usd_amount": "USD額度", "ctbc_position": "中信部位",
            "fund_amount": "FUND"
        }
        show_cols = [c for c in col_names if c in display_df.columns]
        display_df = display_df[show_cols].rename(columns=col_names)

        if "USD額度" in display_df.columns:
            display_df["USD額度"] = display_df["USD額度"].apply(
                lambda x: f"${x:,.0f}" if pd.notna(x) and x else "—"
            )
        if "中信部位" in display_df.columns:
            display_df["中信部位"] = display_df["中信部位"].apply(
                lambda x: f"${x:,.0f}" if pd.notna(x) and x else "—"
            )

        st.dataframe(display_df, use_container_width=True, hide_index=True)


# ──────────────────────────────────────────────────────────────
# Tab 2: 新增客戶
# ──────────────────────────────────────────────────────────────
with tab2:
    st.subheader("新增客戶資料")

    with st.form("add_customer_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("客戶姓名 *", placeholder="例: 游家順")
            usd_amount = st.number_input("USD 額度", min_value=0, step=10000, value=0)
            ctbc_position = st.number_input("中信部位 (USD)", min_value=0, step=10000, value=0)

        with col2:
            unified_account = st.checkbox("統一開戶")
            pi_signed = st.checkbox("PI 見簽")
            ordered = st.checkbox("已下單")
            fund_amount = st.number_input("FUND 金額", min_value=0, step=100000, value=0)

        notes = st.text_area("備註", placeholder="輸入備註...")

        submitted = st.form_submit_button("➕ 新增客戶", type="primary")

        if submitted:
            if not name.strip():
                st.error("請填寫客戶姓名")
            else:
                data = {
                    "name": name.strip(),
                    "unified_account": unified_account,
                    "pi_signed": pi_signed,
                    "ordered": ordered,
                    "usd_amount": usd_amount or None,
                    "ctbc_position": ctbc_position or None,
                    "fund_amount": fund_amount or None,
                    "notes": notes.strip() or None,
                }
                result = create_customer(data)
                if result:
                    st.success(f"✅ 客戶 **{name}** 新增成功！")
                    st.rerun()
                else:
                    st.error("新增失敗，請確認資料庫連線")

# ──────────────────────────────────────────────────────────────
# Tab 3: 客戶詳情
# ──────────────────────────────────────────────────────────────
with tab3:
    customers_df = get_all_customers()

    if customers_df.empty:
        st.info("尚無客戶資料")
    else:
        names = customers_df["name"].tolist()
        selected_name = st.selectbox("選擇客戶", names)

        selected_row = customers_df[customers_df["name"] == selected_name].iloc[0]
        customer_id = selected_row["id"]

        # 客戶基本資訊
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"### {selected_name}")
            st.markdown(f"**統一開戶:** {'✅' if selected_row.get('unified_account') else '❌'}")
            st.markdown(f"**PI 見簽:** {'✅' if selected_row.get('pi_signed') else '❌'}")
            st.markdown(f"**已下單:** {'✅' if selected_row.get('ordered') else '❌'}")
        with col2:
            usd = selected_row.get('usd_amount')
            ctbc = selected_row.get('ctbc_position')
            fund = selected_row.get('fund_amount')
            if usd:
                st.metric("USD 額度", f"${usd:,.0f}")
            if ctbc:
                st.metric("中信部位", f"${ctbc:,.0f}")
            if fund:
                st.metric("FUND", f"${fund:,.0f}")

        # 編輯客戶
        with st.expander("✏️ 編輯客戶資料"):
            with st.form(f"edit_{customer_id}"):
                new_name = st.text_input("姓名", value=selected_name)
                new_usd = st.number_input("USD額度", value=float(selected_row.get("usd_amount") or 0), step=10000.0)
                new_ctbc = st.number_input("中信部位", value=float(selected_row.get("ctbc_position") or 0), step=10000.0)
                new_fund = st.number_input("FUND", value=float(selected_row.get("fund_amount") or 0), step=100000.0)
                new_unified = st.checkbox("統一開戶", value=bool(selected_row.get("unified_account")))
                new_pi = st.checkbox("PI見簽", value=bool(selected_row.get("pi_signed")))
                new_ordered = st.checkbox("已下單", value=bool(selected_row.get("ordered")))
                new_notes = st.text_area("備註", value=selected_row.get("notes") or "")

                if st.form_submit_button("💾 儲存變更"):
                    update_customer(customer_id, {
                        "name": new_name,
                        "usd_amount": new_usd or None,
                        "ctbc_position": new_ctbc or None,
                        "fund_amount": new_fund or None,
                        "unified_account": new_unified,
                        "pi_signed": new_pi,
                        "ordered": new_ordered,
                        "notes": new_notes or None,
                    })
                    st.success("✅ 更新成功")
                    st.rerun()

        st.markdown("---")

        # 該客戶的投資記錄
        st.subheader("📊 投資持倉")
        investments = get_investments_by_customer(customer_id)

        if not investments:
            st.info("此客戶目前無持倉記錄")
        else:
            total_inv = sum(i.get("amount_usd", 0) or 0 for i in investments)
            st.metric("投資總計", f"USD {total_inv:,.0f}")

            # 取得所有標的股票現價
            all_tickers = []
            for inv in investments:
                sn = inv.get("structured_notes") or {}
                all_tickers += [sn.get(f"underlying_{i}") for i in range(1, 6)
                                 if isinstance(sn.get(f"underlying_{i}"), str)]
            all_tickers = list(set([t for t in all_tickers if t]))

            prices = {}
            if all_tickers:
                with st.spinner("取得股票現價..."):
                    prices = get_prices(all_tickers)

            for inv in investments:
                sn = inv.get("structured_notes") or {}
                if not sn:
                    continue

                code = sn.get("product_code", "—")
                underlyings = get_sn_underlyings(sn)
                ticker_str = " / ".join([u["ticker"] for u in underlyings])
                amount = inv.get("amount_usd", 0) or 0
                obs_date = str(sn.get("observation_date", ""))[:10]

                analysis = analyze_sn_status(sn, prices)
                emoji = analysis.get("status_emoji", "❓")
                label = analysis.get("status_label", "—")

                with st.expander(f"{emoji} {code} ({ticker_str}) — USD {amount:,.0f}"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown(f"**標的股票:** {ticker_str}")
                        st.markdown(f"**比價日期:** {obs_date}")
                        strike = sn.get("strike_pct")
                        coupon = sn.get("coupon_pct")
                        if strike:
                            st.markdown(f"**執行價格:** {strike*100:.2f}%")
                        if coupon:
                            st.markdown(f"**配息率:** {coupon*100:.2f}%")
                    with col_b:
                        st.markdown(f"**投資金額:** USD {amount:,.0f}")
                        st.markdown(f"**狀態:** {label}")

                    # 各標的現價
                    for d in analysis.get("details", []):
                        ticker = d["ticker"]
                        curr = d.get("current_price")
                        init = d.get("initial_price")
                        chg = d.get("change_pct")
                        ki_s = d.get("ki_status", "—")
                        ko_s = d.get("ko_status", "—")

                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.markdown(f"**{ticker}**")
                        with col2:
                            if curr:
                                st.markdown(f"現價: **${curr:,.2f}**")
                            else:
                                st.markdown("現價: 取得中")
                        with col3:
                            if chg is not None:
                                color = "🟢" if chg >= 0 else "🔴"
                                st.markdown(f"{color} {chg:+.2f}%")
                        with col4:
                            st.markdown(f"{ko_s} {ki_s}")

        # 刪除客戶
        st.markdown("---")
        with st.expander("🗑️ 刪除客戶 (危險操作)"):
            st.warning(f"⚠️ 刪除客戶 **{selected_name}** 將同時刪除所有相關投資記錄，此動作無法復原！")
            confirm = st.text_input("請輸入客戶姓名確認刪除:", placeholder=selected_name)
            if st.button("確認刪除", type="primary"):
                if confirm == selected_name:
                    delete_customer(customer_id)
                    st.success(f"✅ 已刪除客戶 {selected_name}")
                    st.rerun()
                else:
                    st.error("姓名不符，刪除取消")

# ──────────────────────────────────────────────────────────────
# Tab 4: 匯出資料
# ──────────────────────────────────────────────────────────────
with tab4:
    st.subheader("📤 匯出客戶資料")
    st.caption("可匯出為 Excel (.xlsx) 或 CSV 格式")

    customers_df = get_all_customers()
    if customers_df.empty:
        st.info("尚無客戶資料可匯出")
        st.stop()

    today_str = date.today().strftime("%Y%m%d")

    # ── 匯出模式選擇 ────────────────────────────────────────
    mode = st.radio("匯出方式", ["📅 依月份分頁", "👥 依客戶彙總"], horizontal=True)
    st.markdown("---")

    # ══════════════════════════════════════════════════════
    # 模式 1: 依月份 — 每個月一個 Sheet
    # ══════════════════════════════════════════════════════
    if mode == "📅 依月份分頁":
        st.caption("每個月份各為一個工作表，內含該月所有商品及投資明細")

        # 取得所有 SN (含 month_label)
        from utils.database import get_all_sns as _get_all_sns
        sns_df_all = _get_all_sns()

        if sns_df_all.empty or "month_label" not in sns_df_all.columns:
            st.warning("尚無月份資料")
        else:
            months = sorted(
                [m for m in sns_df_all["month_label"].dropna().unique() if m],
                key=lambda x: (
                    int(x.replace("月","")) if x.replace("月","").isdigit() else 99
                )
            )

            if not months:
                st.warning("找不到月份資料")
            else:
                st.info(f"找到 **{len(months)}** 個月份：{' · '.join(months)}")

                if st.button("📊 產生 Excel（依月份）", type="primary", use_container_width=True):
                    with st.spinner("整理資料中，請稍候..."):
                        buf = io.BytesIO()
                        with pd.ExcelWriter(buf, engine="openpyxl") as writer:

                            # Sheet 1: 總覽
                            summary_rows = []
                            for m in months:
                                m_sns = sns_df_all[sns_df_all["month_label"] == m]
                                m_invs_total = 0
                                m_customers = set()
                                for _, sn_row in m_sns.iterrows():
                                    invs = get_investments_by_sn(sn_row["id"])
                                    for inv in invs:
                                        m_invs_total += inv.get("amount_usd") or 0
                                        if inv.get("customers"):
                                            m_customers.add(inv["customers"].get("name",""))
                                summary_rows.append({
                                    "月份": m,
                                    "商品數": len(m_sns),
                                    "投資客戶數": len(m_customers),
                                    "總投資金額(USD)": m_invs_total,
                                })
                            pd.DataFrame(summary_rows).to_excel(
                                writer, sheet_name="總覽", index=False)

                            # 每個月一個 Sheet
                            for m in months:
                                m_sns = sns_df_all[sns_df_all["month_label"] == m]
                                rows = []
                                for _, sn_row in m_sns.iterrows():
                                    tickers = " / ".join([
                                        str(sn_row.get(f"underlying_{i}", ""))
                                        for i in range(1, 6)
                                        if isinstance(sn_row.get(f"underlying_{i}"), str)
                                    ])
                                    invs = get_investments_by_sn(sn_row["id"])
                                    if invs:
                                        for inv in invs:
                                            cname = (inv.get("customers") or {}).get("name", "—")
                                            rows.append({
                                                "商品代號": sn_row.get("product_code", "—"),
                                                "標的股票": tickers,
                                                "比價日期": str(sn_row.get("observation_date",""))[:10],
                                                "下單日期": str(sn_row.get("trade_date",""))[:10],
                                                "執行價(%)": f"{sn_row.get('strike_pct',0)*100:.2f}%" if sn_row.get("strike_pct") else "—",
                                                "配息率(%)": f"{sn_row.get('coupon_pct',0)*100:.2f}%" if sn_row.get("coupon_pct") else "—",
                                                "KO水位": f"{sn_row.get('ko_barrier',0)*100:.0f}%" if sn_row.get("ko_barrier") else "—",
                                                "KI水位": f"{sn_row.get('ki_barrier',0)*100:.0f}%" if sn_row.get("ki_barrier") else "—",
                                                "狀態": sn_row.get("status", "—"),
                                                "客戶姓名": cname,
                                                "投資金額(USD)": inv.get("amount_usd"),
                                            })
                                    else:
                                        rows.append({
                                            "商品代號": sn_row.get("product_code", "—"),
                                            "標的股票": tickers,
                                            "比價日期": str(sn_row.get("observation_date",""))[:10],
                                            "下單日期": str(sn_row.get("trade_date",""))[:10],
                                            "執行價(%)": f"{sn_row.get('strike_pct',0)*100:.2f}%" if sn_row.get("strike_pct") else "—",
                                            "配息率(%)": f"{sn_row.get('coupon_pct',0)*100:.2f}%" if sn_row.get("coupon_pct") else "—",
                                            "KO水位": f"{sn_row.get('ko_barrier',0)*100:.0f}%" if sn_row.get("ko_barrier") else "—",
                                            "KI水位": f"{sn_row.get('ki_barrier',0)*100:.0f}%" if sn_row.get("ki_barrier") else "—",
                                            "狀態": sn_row.get("status", "—"),
                                            "客戶姓名": "（無投資記錄）",
                                            "投資金額(USD)": None,
                                        })

                                sheet_name = m[:31]  # Excel sheet name max 31 chars
                                pd.DataFrame(rows).to_excel(
                                    writer, sheet_name=sheet_name, index=False)

                        buf.seek(0)

                    st.download_button(
                        label="⬇️ 點此下載 Excel（依月份）",
                        data=buf.getvalue(),
                        file_name=f"投資明細_依月份_{today_str}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )

    # ══════════════════════════════════════════════════════
    # 模式 2: 依客戶彙總
    # ══════════════════════════════════════════════════════
    else:
        col_a, col_b = st.columns(2)

        with col_a:
            st.caption("Sheet 1: 客戶基本資料　Sheet 2: 投資明細")
            if st.button("📊 下載 Excel（依客戶）", type="primary", use_container_width=True):
                with st.spinner("產生中..."):
                    cust_export = customers_df[[c for c in
                        ["name","unified_account","pi_signed","ordered","usd_amount","ctbc_position","fund_amount","notes"]
                        if c in customers_df.columns]].rename(columns={
                        "name":"客戶姓名","unified_account":"統一開戶","pi_signed":"PI見簽",
                        "ordered":"已下單","usd_amount":"USD額度","ctbc_position":"中信部位",
                        "fund_amount":"FUND金額","notes":"備註"})

                    inv_rows = []
                    for _, row in customers_df.iterrows():
                        for inv in get_investments_by_customer(row["id"]):
                            sn = inv.get("structured_notes") or {}
                            tickers = " / ".join([sn.get(f"underlying_{i}","") for i in range(1,6)
                                                  if isinstance(sn.get(f"underlying_{i}"),str)])
                            inv_rows.append({
                                "客戶姓名": row["name"],
                                "商品代號": sn.get("product_code","—"),
                                "標的股票": tickers,
                                "投資金額(USD)": inv.get("amount_usd"),
                                "比價日期": str(sn.get("observation_date",""))[:10],
                                "月份": sn.get("month_label","—"),
                                "狀態": sn.get("status","—"),
                            })

                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                        cust_export.to_excel(writer, sheet_name="客戶基本資料", index=False)
                        if inv_rows:
                            pd.DataFrame(inv_rows).to_excel(writer, sheet_name="投資明細", index=False)
                    buf.seek(0)

                st.download_button("⬇️ 下載 Excel", buf.getvalue(),
                    f"客戶資料_{today_str}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True)

        with col_b:
            st.caption("僅客戶基本資料，適合匯入其他系統")
            cust_csv = customers_df[["name","usd_amount","ordered","pi_signed","notes"]
                ].rename(columns={"name":"客戶姓名","usd_amount":"USD額度",
                                  "ordered":"已下單","pi_signed":"PI見簽","notes":"備註"})
            st.download_button(
                label="⬇️ 下載 CSV",
                data=cust_csv.to_csv(index=False, encoding="utf-8-sig"),
                file_name=f"客戶資料_{today_str}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # ── 預覽 ────────────────────────────────────────────────
    st.markdown("---")
    st.caption(f"預覽：共 {len(customers_df)} 位客戶")
    preview = customers_df[["name", "usd_amount", "ordered", "pi_signed"]].copy()
    preview.columns = ["姓名", "USD額度", "已下單", "PI見簽"]
    st.dataframe(preview, use_container_width=True, hide_index=True)
