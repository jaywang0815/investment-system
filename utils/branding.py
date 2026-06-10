"""
統一證券 品牌資產 — logo、報告人署名、配色 (PDF / Excel / PPT 共用)
單一改色處：改這裡即可換整套匯出檔的主題色。
"""
import os

_ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
LOGO_PATH = os.path.join(_ASSETS, "company_logo.png")

COMPANY   = "統一證券"
REPORTER  = "秦聖鈞"
# 報表署名 (頁首 / 頁尾共用)
SIGNATURE = "統一證券　報告人　秦聖鈞"

# ── 配色 (品牌紅) — hex 字串不含 # ──────────────────────────
C_PRIMARY = "B23A2B"   # 深品牌紅 — 標題列 / 表頭
C_HEADER  = "9E3326"   # 更深紅 — 群組標頭帶
C_ACCENT  = "E5483A"   # 品牌紅 — 線條 / 重點
C_TINT    = "FBEAE7"   # 淺紅底 — 標籤格 / 表頭淺底
C_ZEBRA   = "FAF6F5"   # 斑馬列中性暖灰
C_BORDER  = "E7D9D6"   # 邊框
C_TEXT    = "1A1A1A"   # 主文字
C_MUTED   = "7A716E"   # 次文字
C_GREEN   = "1B9E5A"   # KO / 正向
C_RED     = "D64541"   # KI / 負向
C_EXIT_BG = "FFF4DC"   # 出場列底 (金)
C_NEW_BG  = "EAF7EE"   # 本月新增列底 (綠)
C_WHITE   = "FFFFFF"


def hx(c: str) -> str:
    """'B23A2B' -> '#B23A2B' (for reportlab / matplotlib)."""
    return c if c.startswith("#") else "#" + c


def has_logo() -> bool:
    return os.path.exists(LOGO_PATH)
