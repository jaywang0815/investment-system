"""
報表匯出頁面 - PDF + Excel + Google Sheets
"""
import streamlit as st
import pandas as pd
from datetime import date
from utils.database import (
    get_all_customers, get_all_sns, get_all_investments,
    get_investments_by_customer, get_customer
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
    st.subheader("匯出所有資料為 Excel")
    st.markdown("""
    Excel 檔案包含三個工作表:
    - **客戶資料**: 所有客戶基本資訊
    - **SN商品**: 所有結構型商品資料
    - **投資記錄**: 客戶與商品的投資對應關係
    """)

    if st.button("📥 產生 Excel 檔案", type="primary"):
        with st.spinner("產生中..."):
            customers_df = get_all_customers()
            sns_df = get_all_sns()
            investments_df = get_all_investments()

            excel_bytes = export_to_excel(customers_df, sns_df, investments_df)
            today_str = date.today().strftime("%Y%m%d")

        st.download_button(
            label="⬇️ 下載 Excel 檔案",
            data=excel_bytes,
            file_name=f"投資管理資料_{today_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.success("✅ Excel 檔案產生完成")

    st.markdown("---")
    st.markdown("**資料預覽**")
    preview_choice = st.radio("選擇預覽", ["客戶資料", "SN商品", "投資記錄"], horizontal=True)

    if preview_choice == "客戶資料":
        df = get_all_customers()
        if not df.empty:
            st.dataframe(df[["name", "usd_amount", "ctbc_position", "ordered", "pi_signed"]].head(20),
                         use_container_width=True, hide_index=True)
    elif preview_choice == "SN商品":
        df = get_all_sns()
        if not df.empty:
            show_cols = ["product_code", "underlying_1", "underlying_2", "underlying_3",
                         "strike_pct", "coupon_pct", "observation_date", "status"]
            show_cols = [c for c in show_cols if c in df.columns]
            st.dataframe(df[show_cols].head(20), use_container_width=True, hide_index=True)
    else:
        df = get_all_investments()
        if not df.empty:
            show_cols = ["customer_name", "product_code", "amount_usd", "observation_date", "status"]
            show_cols = [c for c in show_cols if c in df.columns]
            st.dataframe(df[show_cols].head(20), use_container_width=True, hide_index=True)

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
