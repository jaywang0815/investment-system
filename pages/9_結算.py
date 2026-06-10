"""
結算 — 配息與結算合計 (原幣)，可手動調整以對齊公司計算結果
規則: 基準日 = 期初 + 7 天 · 第一個月保證 · 之後按實際天數 (年化 ÷ 365)
手動調整: 改「配息金額」並儲存 → 存為 override；系統計算結果保留供對照
"""
import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="結算", page_icon=None, layout="wide")

from utils.ui_helpers import dog_header, require_auth
dog_header("結算")
require_auth()

from utils.database import get_supabase
from utils.settlement import settle
from utils.money import format_money

st.caption("配息基準日 = 期初日 + 7 天 · 第一個月保證配息 · 之後按實際天數 (當天計息) · 年化 ÷ 365 · 依原幣")
st.info("計算為輔助參考。若與公司系統不同，可直接修改「配息金額」欄位再按儲存 — 系統會記住你調整的值。", icon="ℹ️")

settle_date = st.date_input("結算日 (未填出場日的商品用此日計算)", value=date.today())
sb = get_supabase()

SEL_FULL = ("id, amount_usd, currency, settle_coupon, settle_note, "
            "customers(name), structured_notes(product_code,trade_date,exit_date,coupon_pct)")
SEL_MIN = ("id, amount_usd, customers(name), "
           "structured_notes(product_code,trade_date,exit_date,coupon_pct)")

migrated = True
try:
    rows = sb.table("investments").select(SEL_FULL).execute().data or []
except Exception:
    migrated = False
    rows = sb.table("investments").select(SEL_MIN).execute().data or []

if not migrated:
    st.warning("尚未建立 currency / settle 欄位 — 請先在 Supabase SQL Editor 執行 "
               "scripts/currency_settle_schema.sql，手動調整功能才會生效 (目前僅顯示系統計算)。")

if not rows:
    st.info("尚無投資記錄")
    st.stop()

# ── 計算每筆 ─────────────────────────────────────────────────
recs = []
for r in rows:
    sn = r.get("structured_notes") or {}
    cust = r.get("customers") or {}
    principal = r.get("amount_usd") or 0
    ccy = r.get("currency") or "USD"
    s = settle(principal, sn.get("coupon_pct"), sn.get("trade_date"),
               sn.get("exit_date") or str(settle_date), ccy)

    sys_coupon = 0.0 if s["error"] else s["coupon"]
    override = r.get("settle_coupon")
    eff_coupon = float(override) if override is not None else sys_coupon
    eff_total = round(principal + eff_coupon, 2)

    recs.append({
        "id": r["id"], "ccy": ccy, "principal": principal,
        "sys_coupon": sys_coupon, "override": override,
        "row": {
            "客戶": cust.get("name", "—"),
            "代號": sn.get("product_code", "—"),
            "幣別": ccy,
            "本金": principal,
            "期初日": str(sn.get("trade_date"))[:10] if sn.get("trade_date") else "—",
            "配息基準日": str(s["base_date"]) if s["base_date"] else "—",
            "出場日": str(s["exit_date"]) if s["exit_date"] else "—",
            "天數": s["days"] if not s["error"] else 0,
            "系統配息": round(sys_coupon, 2),
            "配息金額": round(eff_coupon, 2),   # 可編輯
            "結算合計": eff_total,
            "狀態": ("⚠ 缺資料" if s["error"]
                     else "✎ 已調整" if override is not None else "系統計算"),
            "備註": r.get("settle_note") or "",
        },
    })

editor_df = pd.DataFrame([x["row"] for x in recs])

# ── 各幣別小計 (用有效值) ────────────────────────────────────
st.markdown("##### 各幣別結算小計")
tmp = editor_df.copy()
tmp["_ccy"] = [x["ccy"] for x in recs]
summary = tmp.groupby("_ccy").agg(本金=("本金", "sum"), 配息=("配息金額", "sum"),
                                  合計=("結算合計", "sum")).reset_index()
cols = st.columns(max(len(summary), 1))
for i, (_, srow) in enumerate(summary.iterrows()):
    with cols[i % len(cols)]:
        st.metric(f"{srow['_ccy']} · 合計", format_money(srow["合計"], srow["_ccy"]),
                  delta=f"配息 {format_money(srow['配息'], srow['_ccy'])}")

# ── 可編輯明細 ───────────────────────────────────────────────
st.markdown("##### 結算明細 (可修改「配息金額」與「備註」)")
edited = st.data_editor(
    editor_df,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    column_config={
        "客戶": st.column_config.TextColumn(disabled=True),
        "代號": st.column_config.TextColumn(disabled=True),
        "幣別": st.column_config.TextColumn(disabled=True),
        "本金": st.column_config.NumberColumn(disabled=True, format="%.2f"),
        "期初日": st.column_config.TextColumn(disabled=True),
        "配息基準日": st.column_config.TextColumn(disabled=True),
        "出場日": st.column_config.TextColumn(disabled=True),
        "天數": st.column_config.NumberColumn(disabled=True),
        "系統配息": st.column_config.NumberColumn("系統配息 (對照)", disabled=True, format="%.2f"),
        "配息金額": st.column_config.NumberColumn("配息金額 ✎", format="%.2f"),
        "結算合計": st.column_config.NumberColumn(disabled=True, format="%.2f"),
        "狀態": st.column_config.TextColumn(disabled=True),
        "備註": st.column_config.TextColumn("備註 ✎"),
    },
    key="settle_editor",
)

if st.button("💾 儲存調整", type="primary", disabled=not migrated):
    saved = 0
    for i, rec in enumerate(recs):
        new_coupon = edited.iloc[i]["配息金額"]
        new_note = (edited.iloc[i]["備註"] or "").strip() or None
        try:
            new_coupon = round(float(new_coupon), 2)
        except (TypeError, ValueError):
            new_coupon = rec["sys_coupon"]
        # 與系統值相同 → 清除 override (回到系統計算)；不同 → 存 override
        override = None if abs(new_coupon - round(rec["sys_coupon"], 2)) < 0.005 else new_coupon
        if override != rec["override"] or new_note != (rows[i].get("settle_note")):
            sb.table("investments").update(
                {"settle_coupon": override, "settle_note": new_note}
            ).eq("id", rec["id"]).execute()
            saved += 1
    st.success(f"已儲存 {saved} 筆調整")
    st.rerun()

# ── 下載 ────────────────────────────────────────────────────
csv = editor_df.drop(columns=["系統配息"]).to_csv(index=False).encode("utf-8-sig")
st.download_button("⬇ 下載結算表 (CSV)", data=csv,
                   file_name=f"結算表_{settle_date}.csv", mime="text/csv")
