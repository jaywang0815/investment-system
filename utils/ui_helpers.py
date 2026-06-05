import base64
import streamlit as st
from pathlib import Path

def _img_b64(filename: str) -> str:
    p = Path(__file__).parent.parent / "assets" / filename
    if p.exists():
        return base64.b64encode(p.read_bytes()).decode()
    return ""

# homepage keeps the French bulldog logo; other pages get animals from the collection
_PAGE_DOGS = {
    "首頁總覽":   "logo.png",
    "客戶管理":   "animals/beagle.png",
    "SN商品管理": "animals/golden.png",
    "KO KI警示":  "animals/schnauzer.png",
    "系統設定":   "animals/samoyed.png",
    "報表匯出":   "animals/corgi.png",
    "資料匯入":   "animals/dalmatian.png",
    "月份管理":   "animals/shiba.png",
    "即時圖表":   "animals/frenchie.png",
}

def dog_header(title: str, dog_img: str = ""):
    """Page title with an animal icon instead of an emoji."""
    img_file = dog_img or _PAGE_DOGS.get(title, "logo.png")
    b64 = _img_b64(img_file)
    if b64:
        icon = f'<img src="data:image/png;base64,{b64}" style="width:72px;height:72px;object-fit:contain;vertical-align:middle;margin-right:12px;flex-shrink:0;">'
    else:
        icon = "🐾 "
    st.markdown(f"""
<h1 style="display:flex;align-items:center;font-size:1.55rem;font-weight:700;
           color:#1E3A8A;padding-bottom:0.3rem;border-bottom:2px solid #e2e8f0;
           margin-bottom:1rem;">
    {icon}{title}
</h1>
""", unsafe_allow_html=True)
