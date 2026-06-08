"""
KO/KI 警示頁面 + LINE 通知
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from utils.database import get_all_sns, get_investments_by_sn, get_dashboard_stats, save_alert
from utils.stock_prices import get_prices, get_all_tickers_for_active_sns, analyze_sn_status
from utils.line_service import send_line_notify, build_daily_report, build_alert_message

st.set_page_config(page_title="KO/KI警示", page_icon="⚠️", layout="wide")


def _render_sn_alert(sn, analysis, prices):
    """渲染單一 SN 的警示詳情"""
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**比價日:** {str(sn.get('observation_date',''))[:10]}")
        strike = sn.get("strike_pct")
        ko = sn.get("ko_barrier")
        ki = sn.get("ki_barrier")
        if strike:
            st.markdown(f"**執行價:** {strike*100:.2f}%")
        if ko:
            st.markdown(f"**KO水位:** {ko*100:.0f}%")
        if ki:
            st.markdown(f"**KI水位:** {ki*100:.0f}%")

    with col2:
        worst = analysis.get("worst_performance")
        if worst:
            st.markdown(f"**最差表現:** {worst*100:.1f}%")
        st.markdown(f"**狀態:** {analysis['status_label']}")

        try:
            investments = get_investments_by_sn(sn["id"])
            affected_customers = [i.get("customers", {}).get("name", "—") for i in investments]
            total_impact = sum(i.get("amount_usd", 0) or 0 for i in investments)
            st.markdown(f"**影響客戶:** {', '.join(affected_customers)}")
            st.markdown(f"**涉及金額:** USD {total_impact:,.0f}")
        except Exception:
            pass

    detail_data = []
    for d in analysis.get("details", []):
        detail_data.append({
            "標的": d["ticker"],
            "期初": f"${d['initial_price']:,.2f}" if d.get("initial_price") else "—",
            "現價": f"${d['current_price']:,.2f}" if d.get("current_price") else "取得中",
            "漲跌%": f"{d['change_pct']:+.2f}%" if d.get("change_pct") is not None else "—",
            "執行價": f"${d['strike_price']:,.2f}" if d.get("strike_price") else "—",
            "KO價格": f"${d['ko_price']:,.2f}" if d.get("ko_price") else "無",
            "KI價格": f"${d['ki_price']:,.2f}" if d.get("ki_price") else "無",
            "KO狀態": d.get("ko_status", "—"),
            "KI狀態": d.get("ki_status", "—"),
        })

    if detail_data:
        st.dataframe(pd.DataFrame(detail_data), use_container_width=True, hide_index=True)


from utils.ui_helpers import dog_header, require_auth
dog_header("KO KI警示")
require_auth()

# ── 資料載入 ──────────────────────────────────────────────────
with st.spinner("載入商品資料..."):
    sns_df = get_all_sns(status="active")

if sns_df.empty:
    st.info("目前無有效商品資料")
    st.stop()

all_tickers = get_all_tickers_for_active_sns(sns_df)
with st.spinner(f"取得 {len(all_tickers)} 個股票即時價格..."):
    prices = get_prices(all_tickers)

# ── 分析所有 SN ────────────────────────────────────────────────
analyzed = []
for _, sn_row in sns_df.iterrows():
    sn = sn_row.to_dict()
    analysis = analyze_sn_status(sn, prices)
    analyzed.append({"sn": sn, "analysis": analysis})

# 分類
ki_triggered   = [a for a in analyzed if a["analysis"]["overall_status"] == "ki_triggered"]
ki_risk        = [a for a in analyzed if a["analysis"]["overall_status"] == "ki_risk"]
ko_triggered   = [a for a in analyzed if a["analysis"]["overall_status"] == "ko_triggered"]
ko_risk        = [a for a in analyzed if a["analysis"]["overall_status"] == "ko_risk"]
normal         = [a for a in analyzed if a["analysis"]["overall_status"] == "normal"]

# ── 狀態摘要卡片 ──────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.metric("🔴 KI 觸發", len(ki_triggered), delta="需要立即關注" if ki_triggered else None,
              delta_color="inverse")
with c2:
    st.metric("🟠 KI 風險", len(ki_risk), delta="接近KI水位" if ki_risk else None,
              delta_color="inverse")
with c3:
    st.metric("🟢 KO 觸發", len(ko_triggered), delta="即將贖回" if ko_triggered else None)
with c4:
    st.metric("🟡 KO 接近", len(ko_risk))
with c5:
    st.metric("✅ 正常", len(normal))

st.markdown("---")

# ── 比價日提醒 ────────────────────────────────────────────────
today = date.today()
st.subheader("📅 近 14 天比價日提醒")
upcoming_df = sns_df[
    pd.to_datetime(sns_df["observation_date"]).dt.date.between(today, today + timedelta(days=14))
].sort_values("observation_date")

if upcoming_df.empty:
    st.success("✅ 未來 14 天內無比價日")
else:
    for _, row in upcoming_df.iterrows():
        obs = pd.to_datetime(row["observation_date"]).date()
        days_left = (obs - today).days
        code = row.get("product_code", "—")
        tickers = " / ".join([str(row.get(f"underlying_{i}")) for i in range(1,6)
                               if row.get(f"underlying_{i}") and isinstance(row.get(f"underlying_{i}"), str)])
        badge = "🔴" if days_left <= 3 else "🟡" if days_left <= 7 else "🟢"
        st.markdown(f"{badge} **{str(obs)[:10]}** (剩 {days_left} 天) &nbsp;|&nbsp; `{code}` &nbsp; {tickers}")

st.markdown("---")

# ── KI 觸發警示 ───────────────────────────────────────────────
if ki_triggered:
    st.subheader("🔴 KI 觸發 - 立即處理")
    for item in ki_triggered:
        sn = item["sn"]
        analysis = item["analysis"]
        code = sn.get("product_code", "—")

        with st.expander(f"🔴 {code} — {analysis['status_label']}", expanded=True):
            _render_sn_alert(sn, analysis, prices)

if ki_risk:
    st.subheader("🟠 接近 KI 水位 - 密切關注")
    for item in ki_risk:
        sn = item["sn"]
        analysis = item["analysis"]
        code = sn.get("product_code", "—")
        with st.expander(f"🟠 {code} — {analysis['status_label']}"):
            _render_sn_alert(sn, analysis, prices)

if ko_triggered:
    st.subheader("🟢 KO 觸發 - 即將提前贖回")
    for item in ko_triggered:
        sn = item["sn"]
        analysis = item["analysis"]
        code = sn.get("product_code", "—")
        with st.expander(f"🟢 {code} — {analysis['status_label']}"):
            _render_sn_alert(sn, analysis, prices)

if ko_risk:
    st.subheader("🟡 接近 KO 水位")
    for item in ko_risk:
        sn = item["sn"]
        analysis = item["analysis"]
        code = sn.get("product_code", "—")
        with st.expander(f"🟡 {code} — {analysis['status_label']}"):
            _render_sn_alert(sn, analysis, prices)

# ── LINE 通知 ─────────────────────────────────────────────────
st.markdown("---")
st.subheader("📲 LINE 通知")

col_line1, col_line2 = st.columns(2)

with col_line1:
    st.markdown("**每日報告**")
    if st.button("📤 立即發送每日報告到 LINE", type="primary"):
        # 先檢查 Secrets 是否齊全
        access_token = st.secrets.get("LINE_CHANNEL_ACCESS_TOKEN")
        user_id = st.secrets.get("LINE_ADMIN_USER_ID")
        if not access_token:
            st.error("❌ 缺少 LINE_CHANNEL_ACCESS_TOKEN，請至 Streamlit Cloud Secrets 新增")
        elif not user_id:
            st.error("❌ 缺少 LINE_ADMIN_USER_ID，請至 Streamlit Cloud Secrets 新增")
        else:
            stats = get_dashboard_stats()
            upcoming = upcoming_df.to_dict("records") if not upcoming_df.empty else []
            sns_with_customers = []
            for a in analyzed:
                invs = get_investments_by_sn(a["sn"]["id"])
                names = "、".join([i.get("customers", {}).get("name", "") for i in invs if i.get("customers")])
                sns_with_customers.append({**a["sn"], **a["analysis"], "customer_names": names})
            report = build_daily_report(
                stats=stats,
                sns_with_status=sns_with_customers,
                upcoming_obs=upcoming
            )
            if send_line_notify(report):
                st.success("✅ 每日報告已發送到 LINE!")
            else:
                st.error("❌ 發送失敗 — Token 或 User ID 可能有誤，請至 LINE Developers 重新產生 Channel Access Token")

with col_line2:
    st.markdown("**發送特定商品警示**")
    alert_items = ki_triggered + ki_risk + ko_triggered + ko_risk
    if not alert_items:
        st.info("目前無警示商品需要通知")
    else:
        codes_with_alerts = [a["sn"].get("product_code", "—") for a in alert_items]
        selected_alert = st.selectbox("選擇商品", codes_with_alerts, key="alert_select")

        if st.button("📢 發送此商品警示", key="send_alert"):
            for item in alert_items:
                if item["sn"].get("product_code") == selected_alert:
                    msg = build_alert_message(item["sn"], item["analysis"])
                    if send_line_notify(msg):
                        save_alert(
                            item["sn"]["id"],
                            item["analysis"]["overall_status"],
                            f"{selected_alert}: {item['analysis']['status_label']}"
                        )
                        st.success("✅ 警示已發送到 LINE!")
                    else:
                        st.error("❌ 發送失敗")
                    break
