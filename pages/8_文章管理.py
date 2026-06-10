"""
文章管理 — 寫中文 → AI 翻成英文 → 發布到公開網站 (justinvestment.co/觀點)
僅後台 (PIN) 可進入編輯
"""
import streamlit as st

st.set_page_config(page_title="文章管理", page_icon=None, layout="wide")

from utils.ui_helpers import dog_header, require_auth
dog_header("文章管理")
require_auth()

from utils.database import get_articles, upsert_article, delete_article

st.caption("在這裡寫投資觀點 (中文)，按「AI 翻譯」自動產生英文，發布後會出現在 justinvestment.co")

# ── 選擇 / 新增 ───────────────────────────────────────────────
try:
    arts = get_articles()
except Exception:
    st.error("找不到 articles 資料表 — 請先在 Supabase SQL Editor 執行 scripts/articles_schema.sql")
    st.stop()
labels = ["➕ 新增文章"] + [
    f"{a.get('title_zh') or '(無標題)'}  ·  {'已發布' if a.get('published') else '草稿'}"
    for a in arts
]
sel = st.selectbox("選擇文章", labels, key="art_select")
chosen = None if sel.startswith("➕") else arts[labels.index(sel) - 1]

FIELDS = ["art_id", "art_slug", "art_cover", "art_pub",
          "art_title_zh", "art_excerpt_zh", "art_body_zh",
          "art_title_en", "art_excerpt_en", "art_body_en"]

# 切換選擇時載入資料 (在 widget 建立前設定 session_state)
if st.session_state.get("art_loaded_for") != sel:
    st.session_state["art_loaded_for"] = sel
    if chosen:
        st.session_state["art_id"]         = chosen.get("id")
        st.session_state["art_slug"]       = chosen.get("slug") or ""
        st.session_state["art_cover"]      = chosen.get("cover_url") or ""
        st.session_state["art_pub"]        = bool(chosen.get("published"))
        st.session_state["art_title_zh"]   = chosen.get("title_zh") or ""
        st.session_state["art_excerpt_zh"] = chosen.get("excerpt_zh") or ""
        st.session_state["art_body_zh"]    = chosen.get("body_zh") or ""
        st.session_state["art_title_en"]   = chosen.get("title_en") or ""
        st.session_state["art_excerpt_en"] = chosen.get("excerpt_en") or ""
        st.session_state["art_body_en"]    = chosen.get("body_en") or ""
    else:
        for f in FIELDS:
            st.session_state[f] = False if f == "art_pub" else (None if f == "art_id" else "")
    st.rerun()


def _run_ai():
    """AI 翻譯/潤稿 → 填入英文欄位 (callback，在 rerun 前設定 state)"""
    from utils.ai_translate import translate_article
    try:
        out = translate_article(
            st.session_state.get("art_title_zh", ""),
            st.session_state.get("art_excerpt_zh", ""),
            st.session_state.get("art_body_zh", ""),
        )
        st.session_state["art_title_en"]   = out.get("title_en", "")
        st.session_state["art_excerpt_en"] = out.get("excerpt_en", "")
        st.session_state["art_body_en"]    = out.get("body_en", "")
        if not st.session_state.get("art_excerpt_zh"):
            st.session_state["art_excerpt_zh"] = out.get("excerpt_zh", "")
        if not st.session_state.get("art_slug"):
            st.session_state["art_slug"] = out.get("slug", "")
        st.session_state["_ai_msg"] = ("ok", "AI 翻譯完成，可再手動微調")
    except Exception as e:
        st.session_state["_ai_msg"] = ("err", f"AI 失敗: {e}")


# ── 基本設定 ─────────────────────────────────────────────────
st.markdown("##### 基本設定")
c1, c2, c3 = st.columns([2, 2, 1])
with c1:
    st.text_input("網址 slug (英文，例: ko-ki-explained)", key="art_slug")
with c2:
    st.text_input("封面圖網址 (選填)", key="art_cover", placeholder="https://...")
with c3:
    st.checkbox("發布", key="art_pub", help="勾選後才會顯示在公開網站")

# ── 中文 (你寫) ──────────────────────────────────────────────
st.markdown("##### 中文內容 (你寫這裡)")
st.text_input("標題", key="art_title_zh")
st.text_input("摘要 (留空可讓 AI 產生)", key="art_excerpt_zh")
st.text_area("內文 (支援 Markdown)", key="art_body_zh", height=260)

st.button("🤖 AI 翻譯 / 潤稿 → 產生英文", on_click=_run_ai, use_container_width=True)
if st.session_state.get("_ai_msg"):
    lvl, txt = st.session_state.pop("_ai_msg")
    (st.success if lvl == "ok" else st.error)(txt)

# ── English (AI 產生，可編輯) ─────────────────────────────────
st.markdown("##### English (AI 產生，可再編輯)")
st.text_input("Title", key="art_title_en")
st.text_input("Excerpt", key="art_excerpt_en")
st.text_area("Body (Markdown)", key="art_body_en", height=260)

# ── 儲存 / 刪除 ──────────────────────────────────────────────
st.markdown("---")
col_s, col_d = st.columns([3, 1])
with col_s:
    if st.button("💾 儲存", type="primary", use_container_width=True):
        if not st.session_state.get("art_title_zh", "").strip():
            st.error("請填寫中文標題")
        elif not st.session_state.get("art_slug", "").strip():
            st.error("請填寫 slug (或先按 AI 產生)")
        else:
            data = {
                "id": st.session_state.get("art_id"),
                "slug": st.session_state["art_slug"].strip(),
                "cover_url": st.session_state.get("art_cover", "").strip() or None,
                "published": bool(st.session_state.get("art_pub")),
                "title_zh": st.session_state.get("art_title_zh", "").strip(),
                "excerpt_zh": st.session_state.get("art_excerpt_zh", "").strip() or None,
                "body_zh": st.session_state.get("art_body_zh", ""),
                "title_en": st.session_state.get("art_title_en", "").strip() or None,
                "excerpt_en": st.session_state.get("art_excerpt_en", "").strip() or None,
                "body_en": st.session_state.get("art_body_en", "") or None,
            }
            if upsert_article(data):
                st.session_state["art_loaded_for"] = None  # 強制重載清單
                st.success("✅ 已儲存")
                st.rerun()
            else:
                st.error("儲存失敗")
with col_d:
    if st.session_state.get("art_id") and st.button("🗑️ 刪除", use_container_width=True):
        delete_article(st.session_state["art_id"])
        st.session_state["art_loaded_for"] = None
        st.rerun()
