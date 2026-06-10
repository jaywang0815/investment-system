"""
結算 — 配息與結算合計 (原幣)，可手動調整
出場日邏輯 (客戶確認): 從比價日起，收盤價 >= 期初×KO% 即該標的 KO (sticky)；
所有標的都 KO 後，最後一隻 KO 當天 = 出場日；尚有未 KO → 未出場。
配息: 基準日=期初+7天, 第一個月保證, 之後按實際天數, 年化÷365, 依原幣。
數值皆可手動修改以對齊公司計算。
"""
import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="結算", page_icon=None, layout="wide")

from utils.ui_helpers import dog_header, require_auth
dog_header("結算")
require_auth()

from utils.database import get_supabase
from utils.settlement import settle, detect_exit_date
from utils.money import format_money

st.caption("出場日 = 所有標的收盤價都達 KO 後、最後一隻 KO 當天 · 配息基準日=期初+7天 · 第一個月保證 · 年化÷365 · 原幣")
st.info("輔助計算。數值如與公司系統不同，可直接修改「配息金額」「出場日」再儲存 — 系統會記住調整值，並保留系統計算供對照。", icon="ℹ️")

c1, c2 = st.columns([1, 1])
with c1:
    settle_date = st.date_input("結算日 (未出場/未設出場日的商品，用此日估算)", value=date.today())
with c2:
    detect_on = st.checkbox("自動偵測出場日 (依收盤價，較慢)", value=False,
                            help="掃描比價日起的歷史收盤價，推算各商品的出場日")

sb = get_supabase()

SN_FIELDS = ("product_code,trade_date,exit_date,coupon_pct,observation_date,ko_barrier,"
             "underlying_1,underlying_2,underlying_3,underlying_4,underlying_5,"
             "initial_price_1,initial_price_2,initial_price_3,initial_price_4,initial_price_5")
SEL = f"id, amount_usd, currency, settle_coupon, settle_note, customers(name), structured_notes({SN_FIELDS})"

try:
    rows = sb.table("investments").select(SEL).execute().data or []
except Exception as e:
    st.error(f"讀取失敗，請先執行 scripts/currency_settle_schema.sql。{e}")
    st.stop()

if not rows:
    st.info("尚無投資記錄")
    st.stop()


@st.cache_data(ttl=1800, show_spinner=False)
def _detect(obs, unds):
    return detect_exit_date(obs, [{"ticker": t, "initial": i, "ko_barrier": k} for t, i, k in unds])


def _underlyings(sn):
    out = []
    ko = sn.get("ko_barrier")
    for i in range(1, 6):
        t = sn.get(f"underlying_{i}")
        ip = sn.get(f"initial_price_{i}")
        if t and ip:
            out.append((str(t), float(ip), float(ko) if ko else None))
    return tuple(out)


if detect_on:
    with st.spinner("偵測出場日中 (讀取歷史收盤價)…"):
        # 觸發各商品偵測 (cache)
        _seen = set()
        for r in rows:
            sn = r.get("structured_notes") or {}
            code = sn.get("product_code")
            if code and code not in _seen:
                _seen.add(code)
                _detect(str(sn.get("observation_date") or sn.get("trade_date")), _underlyings(sn))

recs = []
for r in rows:
    sn = r.get("structured_notes") or {}
    cust = r.get("customers") or {}
    principal = r.get("amount_usd") or 0
    ccy = r.get("currency") or "USD"

    manual_exit = sn.get("exit_date")
    source = "手動"
    exited = True
    if manual_exit:
        eff_exit = str(manual_exit)[:10]
    elif detect_on:
        det = _detect(str(sn.get("observation_date") or sn.get("trade_date")), _underlyings(sn))
        if det["exit_date"]:
            eff_exit = str(det["exit_date"]); source = "推算"
        else:
            eff_exit = str(settle_date); source = "未出場(估)"; exited = False
    else:
        eff_exit = str(settle_date); source = "結算日"

    s = settle(principal, sn.get("coupon_pct"), sn.get("trade_date"), eff_exit, ccy)
    sys_coupon = 0.0 if s["error"] else s["coupon"]
    override = r.get("settle_coupon")
    eff_coupon = float(override) if override is not None else sys_coupon

    recs.append({
        "id": r["id"], "ccy": ccy, "principal": principal,
        "sys_coupon": sys_coupon, "override": override,
        "row": {
            "客戶": cust.get("name", "—"),
            "代號": sn.get("product_code", "—"),
            "幣別": ccy,
            "本金": round(principal, 2),
            "期初日": str(sn.get("trade_date"))[:10] if sn.get("trade_date") else "—",
            "出場日": eff_exit if not s["error"] else "—",
            "出場來源": ("⚠缺資料" if s["error"] else "● 未出場" if not exited else source),
            "天數": s["days"] if not s["error"] else 0,
            "系統配息": round(sys_coupon, 2),
            "配息金額": round(eff_coupon, 2),
            "結算合計": round(principal + eff_coupon, 2),
            "狀態": ("⚠缺資料" if s["error"] else "✎已調整" if override is not None else "系統計算"),
            "備註": r.get("settle_note") or "",
        },
    })

editor_df = pd.DataFrame([x["row"] for x in recs])

# ── 各幣別小計 ───────────────────────────────────────────────
st.markdown("##### 各幣別結算小計")
tmp = editor_df.copy()
tmp["_ccy"] = [x["ccy"] for x in recs]
summary = tmp.groupby("_ccy").agg(配息=("配息金額", "sum"), 合計=("結算合計", "sum")).reset_index()
cols = st.columns(max(len(summary), 1))
for i, (_, srow) in enumerate(summary.iterrows()):
    with cols[i % len(cols)]:
        st.metric(f"{srow['_ccy']} · 合計", format_money(srow["合計"], srow["_ccy"]),
                  delta=f"配息 {format_money(srow['配息'], srow['_ccy'])}")

# ── 可編輯明細 ───────────────────────────────────────────────
st.markdown("##### 結算明細 (可修改「配息金額」與「備註」)")
edited = st.data_editor(
    editor_df, use_container_width=True, hide_index=True, num_rows="fixed",
    column_config={
        "客戶": st.column_config.TextColumn(disabled=True),
        "代號": st.column_config.TextColumn(disabled=True),
        "幣別": st.column_config.TextColumn(disabled=True),
        "本金": st.column_config.NumberColumn(disabled=True, format="%.2f"),
        "期初日": st.column_config.TextColumn(disabled=True),
        "出場日": st.column_config.TextColumn(disabled=True),
        "出場來源": st.column_config.TextColumn(disabled=True),
        "天數": st.column_config.NumberColumn(disabled=True),
        "系統配息": st.column_config.NumberColumn("系統配息(對照)", disabled=True, format="%.2f"),
        "配息金額": st.column_config.NumberColumn("配息金額 ✎", format="%.2f"),
        "結算合計": st.column_config.NumberColumn(disabled=True, format="%.2f"),
        "狀態": st.column_config.TextColumn(disabled=True),
        "備註": st.column_config.TextColumn("備註 ✎"),
    },
    key="settle_editor",
)

if st.button("💾 儲存調整", type="primary"):
    saved = 0
    for i, rec in enumerate(recs):
        new_coupon = edited.iloc[i]["配息金額"]
        new_note = (edited.iloc[i]["備註"] or "").strip() or None
        try:
            new_coupon = round(float(new_coupon), 2)
        except (TypeError, ValueError):
            new_coupon = rec["sys_coupon"]
        override = None if abs(new_coupon - round(rec["sys_coupon"], 2)) < 0.005 else new_coupon
        if override != rec["override"] or new_note != (rows[i].get("settle_note")):
            sb.table("investments").update(
                {"settle_coupon": override, "settle_note": new_note}
            ).eq("id", rec["id"]).execute()
            saved += 1
    st.success(f"已儲存 {saved} 筆調整")
    st.rerun()

csv = editor_df.drop(columns=["系統配息"]).to_csv(index=False).encode("utf-8-sig")
st.download_button("⬇ 下載結算表 (CSV)", data=csv,
                   file_name=f"結算表_{settle_date}.csv", mime="text/csv")
