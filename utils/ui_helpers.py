import base64
import streamlit as st
from pathlib import Path

def _img_b64(filename: str) -> str:
    p = Path(__file__).parent.parent / "assets" / filename
    if p.exists():
        return base64.b64encode(p.read_bytes()).decode()
    return ""

# Map page → dog image (rotate through the 4 dogs)
_PAGE_DOGS = {
    "客戶管理":   "dog_bw.png",
    "SN商品管理": "dog_cream_lie.png",
    "KO KI警示":  "dog_bw_play.png",
    "系統設定":   "logo.png",
    "報表匯出":   "dog_cream_play.png",
    "資料匯入":   "dog_bw_play.png",
    "月份管理":   "dog_cream_lie.png",
    "即時圖表":   "dog_bw.png",
    "首頁總覽":   "logo.png",
}

def dog_header(title: str, dog_img: str = ""):
    """Page title with a small dog icon replacing the emoji."""
    img_file = dog_img or _PAGE_DOGS.get(title, "logo.png")
    b64 = _img_b64(img_file)
    if b64:
        icon = f'<img src="data:image/png;base64,{b64}" style="width:44px;height:44px;vertical-align:middle;margin-right:10px;flex-shrink:0;">'
    else:
        icon = "🐾 "
    st.markdown(f"""
<h1 style="display:flex;align-items:center;font-size:1.55rem;font-weight:700;
           color:#1E3A8A;padding-bottom:0.3rem;border-bottom:2px solid #e2e8f0;
           margin-bottom:1rem;">
    {icon}{title}
</h1>
""", unsafe_allow_html=True)
