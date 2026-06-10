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
from utils.pdf_report import generate_customer_report, generate_portfolio_detail
from utils.excel_export import export_to_excel, sync_to_google_sheets, build_excel_bytes

st.set_page_config(page_title="報表匯出", page_icon=None, layout="wide")

from utils.ui_helpers import dog_header, require_auth
dog_header("報表匯出")
require_auth()

tab1, tab2, tab3 = st.tabs(
    ["投資報表", "Excel匯出", "Google試算表"])

# ──────────────────────────────────────────────────────────────
# Tab 1: 投資報表 — 個人完整報表 + 全部客戶明細表 (合併)
# ──────────────────────────────────────────────────────────────
def _personal_report():
    st.markdown("##### 個人完整報表（含投資明細摘要 + 走勢圖）")

    customers_df = get_all_customers()
    if customers_df.empty:
        st.info("尚無客戶資料")
        return

    today_str = date.today().strftime("%Y%m%d")
    _period_map = {
        "3個月": "3mo", "6個月": "6mo",
        "1年": "1y", "1年半": "18mo",
        "2年": "2y", "2年半": "2y6mo",
        "3年": "3y", "3年半": "3y6mo",
        "4年": "4y", "4年半": "4y6mo",
        "5年": "5y",
    }

    col1, col2 = st.columns([2, 1])
    with col1:
        report_mode = st.radio("報表模式", ["單一客戶", "所有客戶 (批次)"], horizontal=True)

        if report_mode == "單一客戶":
            selected_name = st.selectbox("選擇客戶", customers_df["name"].tolist())
            target_customers = customers_df[customers_df["name"] == selected_name]
        else:
            target_customers = customers_df
            st.info(f"將產生 {len(customers_df)} 份報表")

    with col2:
        st.markdown("**報表設定**")
        include_charts = st.checkbox("包含走勢圖", value=True)
        st.selectbox("走勢圖區間", list(_period_map.keys()), index=1, key="pdf_period_label")
        show_info = st.checkbox("商品基本資訊", value=True)
        show_amount = st.checkbox("顯示投資金額", value=True)
        ALL_DETAIL_COLS = ["期初價格", "現價", "漲跌幅", "執行價", "KO 水位", "KI 水位", "狀態"]
        sel_cols = st.multiselect("明細表欄位 (標的名稱固定顯示)",
                                  ALL_DETAIL_COLS, default=ALL_DETAIL_COLS)

    chart_period = _period_map.get(st.session_state.get("pdf_period_label", "6個月"), "6mo")

    st.markdown("---")

    if st.button("產生 PDF 報表", type="primary"):
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
                    st.warning(f"{customer_name} 目前無投資記錄，跳過")
                    continue

                try:
                    pdf_bytes = generate_customer_report(
                        customer=customer_row.to_dict(),
                        investments=investments,
                        prices=prices,
                        chart_period=chart_period,
                        columns=sel_cols,
                        show_info=show_info,
                        show_amount=show_amount,
                        show_charts=include_charts,
                    )

                    filename = f"投資報表_{customer_name}_{today_str}.pdf"
                    st.download_button(
                        label=f"下載 {customer_name} 的報表",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf",
                        key=f"pdf_{customer_id}"
                    )
                    st.success(f"{customer_name} 報表產生完成")

                except Exception as e:
                    st.error(f"{customer_name} 報表產生失敗: {e}")

    # PDF 預覽說明
    with st.expander("報表包含哪些內容？"):
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

    if st.button("產生 Excel 檔案", type="primary", use_container_width=True):
        with st.spinner("整理資料中，請稍候..."):
            customers_df = get_all_customers()
            sns_df = get_all_sns()

            # filter by selected months
            if selected_months and not sns_df.empty and "month_label" in sns_df.columns:
                sns_df = sns_df[sns_df["month_label"].isin(selected_months)]

            customers = customers_df.to_dict("records") if not customers_df.empty else []
            sns_all = sns_df.to_dict("records") if not sns_df.empty else []

            # build sn_inv_map
            sn_inv_map: dict = {}
            for sn in sns_all:
                sn_id = sn.get("id")
                if not sn_id:
                    continue
                invs = get_investments_by_sn(sn_id)
                for inv in (invs or []):
                    cname = (inv.get("customers") or {}).get("name", "—")
                    amt = inv.get("amount_usd") or 0
                    sn_inv_map.setdefault(sn_id, []).append((cname, amt))

            excel_bytes = build_excel_bytes(customers, sns_all, sn_inv_map)

        months_label = "、".join(selected_months) if selected_months else "全部"
        st.download_button(
            label="下載 Excel 檔案",
            data=excel_bytes,
            file_name=f"投資資料_{months_label}_{today_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        st.success("Excel 產生完成")

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

    if st.button("立即同步到 Google Sheets", type="primary"):
        with st.spinner("同步中..."):
            customers_df = get_all_customers()
            sns_df = get_all_sns()
            success = sync_to_google_sheets(customers_df, sns_df, sheet_id or None)

        if success:
            st.success("資料已同步到 Google Sheets!")
            if sheet_id:
                st.markdown(f"[開啟 Google Sheets](https://docs.google.com/spreadsheets/d/{sheet_id})")
        else:
            st.error("同步失敗，請檢查設定")

# ──────────────────────────────────────────────────────────────
# 全部客戶投資明細表 (可編輯)
# ──────────────────────────────────────────────────────────────
def _detail_table():
    st.markdown("##### 全部客戶投資明細表（可編輯，仿客戶 CTBC 表）")
    st.caption("可直接編輯下表（備註自由填寫、可新增/刪除列），確認後再產生 PDF｜日期=民國紀年・金額=原幣｜統一證券 報告人 秦聖鈞")

    from datetime import date as _d

    def _load_detail_df(selected=None):
        from utils.database import get_supabase
        from utils.pdf_report import _roc, _detail_to_date
        sb = get_supabase()
        sn_fields = "product_code,trade_date,observation_date,coupon_pct,exit_date"
        try:
            rows = sb.table("investments").select(
                f"amount_usd, currency, customers(name), structured_notes({sn_fields})"
            ).execute().data or []
        except Exception:
            rows = sb.table("investments").select(
                f"amount_usd, customers(name), structured_notes({sn_fields})"
            ).execute().data or []

        def _tenor_ym(trade, obs):
            td, od = _detail_to_date(trade), _detail_to_date(obs)
            if td and od and od > td:
                m = max(round((od - td).days / 30), 1)
                return f"{round(m/12)}Y" if m >= 12 else f"{m}M"
            return ""

        recs = []
        for r in rows:
            sn = r.get("structured_notes") or {}
            cust = (r.get("customers") or {}).get("name", "—")
            td = _detail_to_date(sn.get("trade_date"))
            cp = sn.get("coupon_pct")
            exited = bool(sn.get("exit_date"))
            recs.append({
                "日期": _roc(td),
                "公司名稱": cust,
                "代號": sn.get("product_code") or "",
                "期間": _tenor_ym(sn.get("trade_date"), sn.get("observation_date")),
                "配息": f"{cp*100:g}%" if cp else "",
                "金額": float(r.get("amount_usd") or 0),
                "幣別": (r.get("currency") or "USD"),
                "備註": "出場" if exited else "",
                "出場": exited,
            })
        if selected:
            sset = set(selected)
            recs = [r for r in recs if r["公司名稱"] in sset]
        recs.sort(key=lambda x: x["公司名稱"] or "zz")
        return pd.DataFrame(recs, columns=["日期", "公司名稱", "代號", "期間", "配息",
                                           "金額", "幣別", "備註", "出場"])

    _cust_df = get_all_customers()
    _all_names = _cust_df["name"].dropna().tolist() if not _cust_df.empty else []
    sel_custs = st.multiselect("選擇客戶（空白 = 全部客戶）", _all_names, default=[],
                               placeholder="可挑單一或多位客戶...")

    c1, c2, c3 = st.columns([1.2, 1, 1.4])
    if c1.button("載入所選客戶 / 重設", type="secondary") or "detail_df" not in st.session_state:
        st.session_state["detail_df"] = _load_detail_df(sel_custs)
    sec_title = c2.text_input("通路標題", value="CTBC", help="表格上方黃色標題（銀行/通路）")
    rep_date = c3.text_input("報表日期", value=_d.today().strftime("%Y-%m-%d"))

    st.markdown("**編輯明細**（雙擊儲存格修改；最下方空白列可新增；勾選列首刪除）")
    edited = st.data_editor(
        st.session_state["detail_df"],
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "金額": st.column_config.NumberColumn("金額", format="%d", step=1000),
            "幣別": st.column_config.SelectboxColumn(
                "幣別", options=["USD", "JPY", "EUR", "HKD", "CNY", "AUD", "GBP", "TWD", "SGD"]),
            "出場": st.column_config.CheckboxColumn("出場", help="勾選＝該列標綠色"),
        },
        key="detail_editor",
    )
    st.session_state["detail_df"] = edited

    if st.button("產生明細表 PDF", type="primary"):
        items = []
        for _, row in edited.iterrows():
            if not (str(row.get("公司名稱", "") or "").strip() or str(row.get("代號", "") or "").strip()):
                continue
            items.append({
                "customer": (str(row.get("公司名稱") or "—").strip() or "—"),
                "date_str": str(row.get("日期") or ""),
                "product_code": str(row.get("代號") or ""),
                "tenor": str(row.get("期間") or ""),
                "coupon": str(row.get("配息") or ""),
                "amount": float(row.get("金額") or 0),
                "currency": str(row.get("幣別") or "USD"),
                "note": str(row.get("備註") or ""),
                "exited": bool(row.get("出場")),
            })
        if not items:
            st.warning("尚無資料")
        else:
            with st.spinner("產生中..."):
                pdf = generate_portfolio_detail(items, report_date=rep_date,
                                                section_title=sec_title)
            n_cust = len({i["customer"] for i in items})
            st.download_button("⬇ 下載 投資績效明細表 (PDF)", data=pdf,
                               file_name=f"投資績效明細表_{rep_date}.pdf",
                               mime="application/pdf")
            st.success(f"已產生：{len(items)} 筆 · {n_cust} 位客戶")


# ── Tab 1 渲染：個人完整報表 / 全部客戶明細表 (二合一) ──────────
with tab1:
    st.subheader("投資報表")
    _view = st.radio("報表類型",
                     ["個人完整報表", "全部客戶投資明細表"],
                     horizontal=True, key="report_view")
    st.markdown("---")
    if _view == "個人完整報表":
        _personal_report()
    else:
        _detail_table()
