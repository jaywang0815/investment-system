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

# ── Session state ──────────────────────────────────────────────
if "show_add_form" not in st.session_state:
    st.session_state["show_add_form"] = False
if "selected_customer_id" not in st.session_state:
    st.session_state["selected_customer_id"] = None

# ── Header ─────────────────────────────────────────────────────
from utils.ui_helpers import dog_header
dog_header("客戶管理")

customers_df = get_all_customers()

# Stats bar
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("客戶總數", len(customers_df))
with col2:
    ordered = int(customers_df["ordered"].sum()) if "ordered" in customers_df.columns else 0
    st.metric("已下單", ordered)
with col3:
    total_usd = customers_df["usd_amount"].sum() if "usd_amount" in customers_df.columns else 0
    st.metric("USD 總額度", f"${total_usd:,.0f}")
with col4:
    linked = 0
    if "line_user_id" in customers_df.columns:
        linked = customers_df["line_user_id"].notna().sum()
        linked = int((customers_df["line_user_id"].fillna("") != "").sum())
    st.metric("LINE 已連結", f"{linked} 人")

st.markdown("---")

# ── Search + Add button ────────────────────────────────────────
col_search, col_btn = st.columns([5, 1])
with col_search:
    search = st.text_input(
        "搜尋",
        placeholder="🔍 輸入客戶姓名、備註關鍵字...",
        label_visibility="collapsed"
    )
with col_btn:
    if st.button("➕ 新增客戶", type="primary", use_container_width=True):
        st.session_state["show_add_form"] = not st.session_state["show_add_form"]
        st.session_state["selected_customer_id"] = None

# ── 新增客戶 Form ──────────────────────────────────────────────
if st.session_state["show_add_form"]:
    with st.container(border=True):
        st.subheader("➕ 新增客戶")
        with st.form("add_customer_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("客戶姓名 *", placeholder="例: 游家順")
                usd_amount = st.number_input("USD 額度", min_value=0, step=10000, value=0)
                ctbc_position = st.number_input("中信部位 (USD)", min_value=0, step=10000, value=0)
                fund_amount = st.number_input("FUND 金額", min_value=0, step=100000, value=0)
            with col2:
                unified_account = st.checkbox("統一開戶")
                pi_signed = st.checkbox("PI 見簽")
                ordered = st.checkbox("已下單")
            notes = st.text_area("備註", placeholder="輸入備註...")

            col_sub, col_cancel = st.columns(2)
            with col_sub:
                submitted = st.form_submit_button("✅ 新增", type="primary", use_container_width=True)
            with col_cancel:
                cancelled = st.form_submit_button("✖ 取消", use_container_width=True)

            if submitted:
                if not name.strip():
                    st.error("請填寫客戶姓名")
                else:
                    result = create_customer({
                        "name": name.strip(),
                        "unified_account": unified_account,
                        "pi_signed": pi_signed,
                        "ordered": ordered,
                        "usd_amount": usd_amount or None,
                        "ctbc_position": ctbc_position or None,
                        "fund_amount": fund_amount or None,
                        "notes": notes.strip() or None,
                    })
                    if result:
                        st.success(f"✅ 客戶 **{name}** 新增成功！")
                        st.session_state["show_add_form"] = False
                        st.rerun()
                    else:
                        st.error("新增失敗，請確認資料庫連線")

            if cancelled:
                st.session_state["show_add_form"] = False
                st.rerun()

st.markdown("")

# ── Filter customers ───────────────────────────────────────────
if search:
    mask = customers_df["name"].str.contains(search, case=False, na=False, regex=False)
    if "notes" in customers_df.columns:
        mask |= customers_df["notes"].str.contains(search, case=False, na=False, regex=False)
    filtered_df = customers_df[mask]
    st.caption(f"搜尋「{search}」— 找到 {len(filtered_df)} 位客戶")
else:
    filtered_df = customers_df

# ── Tabs ───────────────────────────────────────────────────────
tab_list, tab_export = st.tabs(["📋 客戶列表", "📤 匯出資料"])

# ══════════════════════════════════════════════════════════════
# Tab 1: 客戶列表
# ══════════════════════════════════════════════════════════════
with tab_list:
    if filtered_df.empty:
        if search:
            st.info(f"找不到「{search}」相關的客戶")
        else:
            st.info("尚無客戶資料，請點擊上方「➕ 新增客戶」")
    else:
        for _, row in filtered_df.iterrows():
            cid = row["id"]
            cname = row["name"]
            usd = row.get("usd_amount")
            ordered_val = row.get("ordered")
            pi = row.get("pi_signed")
            line_id = row.get("line_user_id") or ""
            notes_val = row.get("notes") or ""

            # Card header label
            usd_str = f"USD {usd:,.0f}" if usd else ""
            line_badge = "🟢 LINE" if line_id else ""
            ordered_badge = "✅ 已下單" if ordered_val else ""
            badges = "  ".join(b for b in [usd_str, ordered_badge, line_badge] if b)

            with st.expander(f"**{cname}**　　{badges}"):
                col_info, col_edit = st.columns([1, 1])

                with col_info:
                    st.markdown("**基本資料**")
                    st.markdown(f"統一開戶: {'✅' if row.get('unified_account') else '❌'}")
                    st.markdown(f"PI 見簽: {'✅' if pi else '❌'}")
                    st.markdown(f"已下單: {'✅' if ordered_val else '❌'}")
                    if usd:
                        st.markdown(f"USD 額度: **${usd:,.0f}**")
                    ctbc = row.get("ctbc_position")
                    if ctbc:
                        st.markdown(f"中信部位: ${ctbc:,.0f}")
                    fund = row.get("fund_amount")
                    if fund:
                        st.markdown(f"FUND: ${fund:,.0f}")
                    if notes_val:
                        st.caption(f"備註: {notes_val}")
                    if line_id:
                        st.success(f"LINE: {line_id[:8]}...")
                    else:
                        st.warning("尚未連結 LINE")

                with col_edit:
                    st.markdown("**編輯資料**")
                    with st.form(f"edit_{cid}"):
                        new_name = st.text_input("姓名", value=cname)
                        new_usd = st.number_input("USD額度", value=float(usd or 0), step=10000.0)
                        new_ctbc = st.number_input("中信部位", value=float(row.get("ctbc_position") or 0), step=10000.0)
                        new_unified = st.checkbox("統一開戶", value=bool(row.get("unified_account")))
                        new_pi = st.checkbox("PI見簽", value=bool(pi))
                        new_ordered = st.checkbox("已下單", value=bool(ordered_val))
                        new_notes = st.text_area("備註", value=notes_val, height=68)

                        col_save, col_del = st.columns(2)
                        with col_save:
                            if st.form_submit_button("💾 儲存", type="primary", use_container_width=True):
                                update_customer(cid, {
                                    "name": new_name,
                                    "usd_amount": new_usd or None,
                                    "ctbc_position": new_ctbc or None,
                                    "unified_account": new_unified,
                                    "pi_signed": new_pi,
                                    "ordered": new_ordered,
                                    "notes": new_notes or None,
                                })
                                st.success("✅ 更新成功")
                                st.rerun()
                        with col_del:
                            if st.form_submit_button("🗑️ 刪除", use_container_width=True):
                                st.session_state[f"confirm_del_{cid}"] = True

                # Confirm delete
                if st.session_state.get(f"confirm_del_{cid}"):
                    st.warning(f"確定刪除 **{cname}**？此動作無法復原！")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("確認刪除", key=f"do_del_{cid}", type="primary", use_container_width=True):
                            delete_customer(cid)
                            st.session_state.pop(f"confirm_del_{cid}", None)
                            st.rerun()
                    with c2:
                        if st.button("取消", key=f"cancel_del_{cid}", use_container_width=True):
                            st.session_state.pop(f"confirm_del_{cid}", None)
                            st.rerun()

                # 投資持倉
                st.markdown("---")
                investments = get_investments_by_customer(cid)
                if not investments:
                    st.caption("此客戶目前無持倉記錄")
                else:
                    total_inv = sum(i.get("amount_usd", 0) or 0 for i in investments)
                    st.markdown(f"**持倉 {len(investments)} 筆 | 合計 USD {total_inv:,.0f}**")
                    for inv in investments:
                        sn = inv.get("structured_notes") or {}
                        if not sn:
                            continue
                        code = sn.get("product_code", "—")
                        t1 = sn.get("underlying_1", "")
                        t2 = sn.get("underlying_2", "")
                        tstr = f"{t1}/{t2}" if t2 else t1
                        amt = inv.get("amount_usd", 0) or 0
                        obs = str(sn.get("observation_date", ""))[:10]
                        st.caption(f"• {code} ({tstr}) — USD {amt:,.0f} | 比價: {obs}")


# ══════════════════════════════════════════════════════════════
# Tab 2: 匯出資料
# ══════════════════════════════════════════════════════════════
with tab_export:
    st.subheader("📤 匯出客戶資料")

    if customers_df.empty:
        st.info("尚無客戶資料可匯出")
        st.stop()

    today_str = date.today().strftime("%Y%m%d")
    mode = st.radio("匯出方式", ["📅 依月份分頁", "👥 依客戶彙總"], horizontal=True)
    st.markdown("---")

    if mode == "📅 依月份分頁":
        sns_df_all = get_all_sns()
        if sns_df_all.empty or "month_label" not in sns_df_all.columns:
            st.warning("尚無月份資料")
        else:
            months = sorted(
                [m for m in sns_df_all["month_label"].dropna().unique() if m],
                key=lambda x: int(x.replace("月","")) if x.replace("月","").isdigit() else 99
            )
            selected_months = st.multiselect("選擇月份", options=months, default=months)

            if st.button("📊 產生 Excel（依月份）", type="primary", use_container_width=True):
                if not selected_months:
                    st.warning("請至少選擇一個月份")
                else:
                    with st.spinner("整理資料中..."):
                        buf = io.BytesIO()
                        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                            for m in selected_months:
                                m_sns = sns_df_all[sns_df_all["month_label"] == m]
                                rows = []
                                for _, sn_row in m_sns.iterrows():
                                    tickers = " / ".join([
                                        str(sn_row.get(f"underlying_{i}", ""))
                                        for i in range(1, 6)
                                        if isinstance(sn_row.get(f"underlying_{i}"), str)
                                    ])
                                    invs = get_investments_by_sn(sn_row["id"])
                                    base = {
                                        "商品代號": sn_row.get("product_code", "—"),
                                        "標的股票": tickers,
                                        "比價日期": str(sn_row.get("observation_date",""))[:10],
                                        "執行價(%)": f"{sn_row.get('strike_pct',0)*100:.2f}%" if sn_row.get("strike_pct") else "—",
                                        "配息率(%)": f"{sn_row.get('coupon_pct',0)*100:.2f}%" if sn_row.get("coupon_pct") else "—",
                                        "KO水位": f"{sn_row.get('ko_barrier',0)*100:.0f}%" if sn_row.get("ko_barrier") else "—",
                                        "KI水位": f"{sn_row.get('ki_barrier',0)*100:.0f}%" if sn_row.get("ki_barrier") else "—",
                                        "狀態": sn_row.get("status", "—"),
                                    }
                                    if invs:
                                        for inv in invs:
                                            row = base.copy()
                                            row["客戶姓名"] = (inv.get("customers") or {}).get("name", "—")
                                            row["投資金額(USD)"] = inv.get("amount_usd")
                                            rows.append(row)
                                    else:
                                        row = base.copy()
                                        row["客戶姓名"] = "（無投資記錄）"
                                        row["投資金額(USD)"] = None
                                        rows.append(row)
                                pd.DataFrame(rows).to_excel(writer, sheet_name=m[:31], index=False)
                        buf.seek(0)
                    st.download_button(
                        "⬇️ 下載 Excel（依月份）", buf.getvalue(),
                        f"投資明細_依月份_{today_str}.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

    else:
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("📊 下載 Excel（依客戶）", type="primary", use_container_width=True):
                with st.spinner("產生中..."):
                    export_cols = [c for c in ["name","unified_account","pi_signed","ordered","usd_amount","ctbc_position","fund_amount","notes","line_user_id"] if c in customers_df.columns]
                    cust_export = customers_df[export_cols].rename(columns={
                        "name":"客戶姓名","unified_account":"統一開戶","pi_signed":"PI見簽",
                        "ordered":"已下單","usd_amount":"USD額度","ctbc_position":"中信部位",
                        "fund_amount":"FUND金額","notes":"備註","line_user_id":"LINE User ID"})
                    inv_rows = []
                    for _, row in customers_df.iterrows():
                        for inv in get_investments_by_customer(row["id"]):
                            sn = inv.get("structured_notes") or {}
                            tickers = " / ".join([sn.get(f"underlying_{i}","") for i in range(1,6) if isinstance(sn.get(f"underlying_{i}"),str)])
                            inv_rows.append({
                                "客戶姓名": row["name"],
                                "商品代號": sn.get("product_code","—"),
                                "標的股票": tickers,
                                "投資金額(USD)": inv.get("amount_usd"),
                                "比價日期": str(sn.get("observation_date",""))[:10],
                                "狀態": sn.get("status","—"),
                            })
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                        cust_export.to_excel(writer, sheet_name="客戶基本資料", index=False)
                        if inv_rows:
                            pd.DataFrame(inv_rows).to_excel(writer, sheet_name="投資明細", index=False)
                    buf.seek(0)
                st.download_button("⬇️ 下載", buf.getvalue(), f"客戶資料_{today_str}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

        with col_b:
            cust_csv = customers_df[["name","usd_amount","ordered","pi_signed","notes"]].rename(
                columns={"name":"客戶姓名","usd_amount":"USD額度","ordered":"已下單","pi_signed":"PI見簽","notes":"備註"})
            st.download_button(
                "⬇️ 下載 CSV", cust_csv.to_csv(index=False, encoding="utf-8-sig"),
                f"客戶資料_{today_str}.csv", "text/csv", use_container_width=True)
