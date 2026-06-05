"""
報表匯出頁面 - PDF + Excel + Google Sheets
"""
import streamlit as st
import pandas as pd
from datetime import date
import io
from utils.database import (
    get_all_customers, get_all_sns, get_all_investments,
    get_investments_by_customer, get_investments_by_sn, get_customer
)
from utils.stock_prices import get_prices, analyze_sn_status, get_sn_underlyings
from utils.pdf_report import generate_customer_report
from utils.excel_export import export_to_excel, sync_to_google_sheets

st.set_page_config(page_title="報表匯出", page_icon="📄", layout="wide")

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

st.title("📄 報表匯出")

tab1, tab2, tab3, tab4 = st.tabs(["📑 客戶PDF報表", "📊 Excel匯出", "🔗 Google試算表", "📜 歷史報表"])

# ──────────────────────────────────────────────────────────────
# Tab 1: 客戶 PDF 報表
# ──────────────────────────────────────────────────────────────
with tab1:
    st.subheader("產生客戶個人 PDF 報表")

    customers_df = get_all_customers()
    if customers_df.empty:
        st.info("尚無客戶資料")
        st.stop()

    col1, col2 = st.columns([2, 1])
    with col1:
        # 選擇客戶 (單一或全部)
        report_mode = st.radio("報表模式", ["單一客戶", "所有客戶 (批次)"], horizontal=True)

        if report_mode == "單一客戶":
            selected_name = st.selectbox("選擇客戶", customers_df["name"].tolist())
            target_customers = customers_df[customers_df["name"] == selected_name]
        else:
            target_customers = customers_df
            st.info(f"將產生 {len(customers_df)} 份報表")

    with col2:
        st.markdown("**報表設定**")
        include_charts = st.checkbox("包含圖表說明", value=True)
        today_str = date.today().strftime("%Y%m%d")

    st.markdown("---")

    if st.button("🔄 產生 PDF 報表", type="primary"):
        with st.spinner("取得股票現價中..."):
            sns_df = get_all_sns(status="active")
            all_tickers = []
            for _, row in sns_df.iterrows():
                for i in range(1, 6):
                    t = row.get(f"underlying_{i}")
                    if isinstance(t, str):
                        all_tickers.append(t)
            prices = get_prices(list(set(all_tickers))) if all_tickers else {}

        for _, customer_row in target_customers.iterrows():
            customer_id = customer_row["id"]
            customer_name = customer_row["name"]

            with st.spinner(f"產生 {customer_name} 的報表..."):
                investments = get_investments_by_customer(customer_id)

                if not investments:
                    st.warning(f"⚠️ {customer_name} 目前無投資記錄，跳過")
                    continue

                try:
                    pdf_bytes = generate_customer_report(
                        customer=customer_row.to_dict(),
                        investments=investments,
                        prices=prices
                    )

                    filename = f"投資報表_{customer_name}_{today_str}.pdf"
                    st.download_button(
                        label=f"⬇️ 下載 {customer_name} 的報表",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf",
                        key=f"pdf_{customer_id}"
                    )
                    st.success(f"✅ {customer_name} 報表產生完成")

                except Exception as e:
                    st.error(f"❌ {customer_name} 報表產生失敗: {e}")

    # PDF 預覽說明
    with st.expander("📋 報表包含哪些內容？"):
        st.markdown("""
        **客戶個人 PDF 報表包含:**
        - 客戶基本資料 (姓名、USD額度、中信部位)
        - 投資概覽 (持倉數量、總投資金額)
        - 各 SN 商品詳細明細:
          - 商品代號、標的股票、期初價格
          - 執行價格、配息率、KO/KI 水位
          - **即時現價** 及各標的漲跌幅
          - KO/KI 狀態指示燈
        - 報表日期及免責聲明

        *語言: 繁體中文*
        """)

# ──────────────────────────────────────────────────────────────
# Tab 2: Excel 匯出
# ──────────────────────────────────────────────────────────────
with tab2:
    st.subheader("匯出資料為 Excel")

    sns_df_all = get_all_sns()
    today_str = date.today().strftime("%Y%m%d")

    # ── 取得所有月份 ────────────────────────────────────────
    all_months = []
    if not sns_df_all.empty and "month_label" in sns_df_all.columns:
        all_months = sorted(
            [m for m in sns_df_all["month_label"].dropna().unique() if m],
            key=lambda x: int(x.replace("月","")) if x.replace("月","").isdigit() else 99
        )

    # ── 選擇月份 ────────────────────────────────────────────
    if all_months:
        selected_months = st.multiselect(
            "選擇月份（可複選）",
            options=all_months,
            default=all_months,
            placeholder="選擇要匯出的月份..."
        )
    else:
        selected_months = []
        st.info("尚無月份資料，將匯出全部")

    st.caption("每個月份一個工作表，另含「客戶資料」總表")
    st.markdown("---")

    if st.button("📥 產生 Excel 檔案", type="primary", use_container_width=True):
        if all_months and not selected_months:
            st.warning("請至少選擇一個月份")
        else:
            with st.spinner("整理資料中，請稍候..."):
                customers_df = get_all_customers()
                buf = io.BytesIO()

                with pd.ExcelWriter(buf, engine="openpyxl") as writer:

                    # ── Sheet: 客戶基本資料 ──────────────────
                    cust_sheet = customers_df[[c for c in
                        ["name","usd_amount","ctbc_position","fund_amount","unified_account","pi_signed","ordered","notes"]
                        if c in customers_df.columns]].rename(columns={
                        "name":"客戶姓名","usd_amount":"USD額度","ctbc_position":"中信部位",
                        "fund_amount":"FUND","unified_account":"統一開戶",
                        "pi_signed":"PI見簽","ordered":"已下單","notes":"備註"})
                    cust_sheet.to_excel(writer, sheet_name="客戶資料", index=False)

                    # ── 依月份 Sheet ─────────────────────────
                    months_to_export = selected_months if selected_months else all_months
                    if not months_to_export:
                        # ไม่มีเดือน → sheet เดียว รวมทุกอย่าง
                        months_to_export = ["全部"]
                        sns_by_month = {"全部": sns_df_all}
                    else:
                        sns_by_month = {
                            m: sns_df_all[sns_df_all["month_label"] == m]
                            for m in months_to_export
                        }

                    for month, m_sns in sns_by_month.items():
                        rows = []
                        for _, sn_row in m_sns.iterrows():
                            tickers = " / ".join([
                                str(sn_row.get(f"underlying_{i}",""))
                                for i in range(1, 6)
                                if isinstance(sn_row.get(f"underlying_{i}"), str)
                            ])
                            invs = get_investments_by_sn(sn_row["id"])
                            if invs:
                                for inv in invs:
                                    cname = (inv.get("customers") or {}).get("name","—")
                                    rows.append({
                                        "商品代號": sn_row.get("product_code","—"),
                                        "標的股票": tickers,
                                        "比價日期": str(sn_row.get("observation_date",""))[:10],
                                        "下單日期": str(sn_row.get("trade_date",""))[:10],
                                        "執行價(%)": f"{sn_row.get('strike_pct',0)*100:.2f}%" if sn_row.get("strike_pct") else "—",
                                        "配息率(%)": f"{sn_row.get('coupon_pct',0)*100:.2f}%" if sn_row.get("coupon_pct") else "—",
                                        "KO水位": f"{sn_row.get('ko_barrier',0)*100:.0f}%" if sn_row.get("ko_barrier") else "—",
                                        "KI水位": f"{sn_row.get('ki_barrier',0)*100:.0f}%" if sn_row.get("ki_barrier") else "—",
                                        "狀態": sn_row.get("status","—"),
                                        "客戶姓名": cname,
                                        "投資金額(USD)": inv.get("amount_usd"),
                                    })
                            else:
                                rows.append({
                                    "商品代號": sn_row.get("product_code","—"),
                                    "標的股票": tickers,
                                    "比價日期": str(sn_row.get("observation_date",""))[:10],
                                    "下單日期": str(sn_row.get("trade_date",""))[:10],
                                    "執行價(%)": f"{sn_row.get('strike_pct',0)*100:.2f}%" if sn_row.get("strike_pct") else "—",
                                    "配息率(%)": f"{sn_row.get('coupon_pct',0)*100:.2f}%" if sn_row.get("coupon_pct") else "—",
                                    "KO水位": f"{sn_row.get('ko_barrier',0)*100:.0f}%" if sn_row.get("ko_barrier") else "—",
                                    "KI水位": f"{sn_row.get('ki_barrier',0)*100:.0f}%" if sn_row.get("ki_barrier") else "—",
                                    "狀態": sn_row.get("status","—"),
                                    "客戶姓名": "（無投資記錄）",
                                    "投資金額(USD)": None,
                                })
                        pd.DataFrame(rows).to_excel(
                            writer, sheet_name=month[:31], index=False)

                buf.seek(0)

            months_label = "、".join(selected_months) if selected_months else "全部"
            st.download_button(
                label="⬇️ 下載 Excel 檔案",
                data=buf.getvalue(),
                file_name=f"投資資料_{months_label}_{today_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
            st.success("✅ Excel 產生完成")

# ──────────────────────────────────────────────────────────────
# Tab 3: Google 試算表同步
# ──────────────────────────────────────────────────────────────
with tab3:
    st.subheader("同步資料到 Google 試算表")

    st.info("""
    **設定方式:**
    1. 在 Google Cloud Console 建立 Service Account
    2. 下載 JSON 金鑰並複製內容到 secrets.toml 的 `[GOOGLE_SERVICE_ACCOUNT]`
    3. 在 Google Sheets 將 Service Account email 加為編輯者
    4. 將 Sheet ID 填入 secrets.toml 的 `GOOGLE_SHEET_ID`
    """)

    sheet_id = st.text_input(
        "Google Sheet ID",
        value=st.secrets.get("GOOGLE_SHEET_ID", ""),
        placeholder="從 Sheet 網址取得: .../spreadsheets/d/[這裡]/edit"
    )

    if st.button("🔄 立即同步到 Google Sheets", type="primary"):
        with st.spinner("同步中..."):
            customers_df = get_all_customers()
            sns_df = get_all_sns()
            success = sync_to_google_sheets(customers_df, sns_df, sheet_id or None)

        if success:
            st.success("✅ 資料已同步到 Google Sheets!")
            if sheet_id:
                st.markdown(f"[🔗 開啟 Google Sheets](https://docs.google.com/spreadsheets/d/{sheet_id})")
        else:
            st.error("❌ 同步失敗，請檢查設定")

# ──────────────────────────────────────────────────────────────
# Tab 4: 歷史報表 (快速查詢)
# ──────────────────────────────────────────────────────────────
with tab4:
    st.subheader("快速查詢客戶投資狀況")

    customers_df = get_all_customers()
    if not customers_df.empty:
        query_name = st.selectbox("選擇客戶", [""] + customers_df["name"].tolist())

        if query_name:
            customer_row = customers_df[customers_df["name"] == query_name].iloc[0]
            customer_id = customer_row["id"]
            investments = get_investments_by_customer(customer_id)

            if not investments:
                st.info(f"{query_name} 目前無投資記錄")
            else:
                # 取得現價
                all_tickers = []
                for inv in investments:
                    sn = inv.get("structured_notes") or {}
                    all_tickers += [sn.get(f"underlying_{i}") for i in range(1,6) if isinstance(sn.get(f"underlying_{i}"), str)]
                prices = get_prices(list(set([t for t in all_tickers if t]))) if all_tickers else {}

                total = sum(i.get("amount_usd", 0) or 0 for i in investments)
                st.markdown(f"### {query_name} 的投資持倉")
                st.markdown(f"**總投資金額: USD {total:,.0f}**")

                for inv in investments:
                    sn = inv.get("structured_notes") or {}
                    if not sn:
                        continue
                    code = sn.get("product_code", "—")
                    underlyings = get_sn_underlyings(sn)
                    ticker_str = " / ".join([u["ticker"] for u in underlyings])
                    amount = inv.get("amount_usd", 0) or 0
                    analysis = analyze_sn_status(sn, prices)

                    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                    with col1:
                        st.markdown(f"**{code}**")
                        st.caption(ticker_str)
                    with col2:
                        st.markdown(f"比價: {str(sn.get('observation_date',''))[:10]}")
                    with col3:
                        st.markdown(f"USD {amount:,.0f}")
                    with col4:
                        st.markdown(f"{analysis['status_emoji']} {analysis['status_label']}")
                    st.markdown("---")
