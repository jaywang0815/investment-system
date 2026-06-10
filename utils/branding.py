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

# ── 配色 (品牌紅，精緻不刺眼) — hex 字串不含 # ────────────────
# 紅作為「重點色」，大面積用淺底/中性，避免整份過紅。
C_PRIMARY = "A62A36"   # 精緻深紅 (酒紅調) — 標題 / 代號 / 文字重點
C_HEADER  = "8E232E"   # 更深 — 群組標頭
C_ACCENT  = "C0392B"   # 重點紅 — 細線 / 強調 (節制使用)
C_TINT    = "FBEEEF"   # 極淺玫瑰底 — 標籤格 / 總計帶
C_ZEBRA   = "FAF7F7"   # 斑馬列中性暖灰
C_BORDER  = "EAD9DB"   # 邊框
C_TEXT    = "1F1B1B"   # 主文字 (近黑)
C_MUTED   = "7A6F70"   # 次文字
C_GREEN   = "1B9E5A"   # KO / 正向
C_RED     = "C0392B"   # KI / 負向
C_EXIT_BG = "EAF3E0"   # 出場列底 (淺綠，仿客戶表)
C_NEW_BG  = "EAF7EE"   # 本月新增列底 (綠)
C_WHITE   = "FFFFFF"


def hx(c: str) -> str:
    """'B23A2B' -> '#B23A2B' (for reportlab / matplotlib)."""
    return c if c.startswith("#") else "#" + c


def has_logo() -> bool:
    return os.path.exists(LOGO_PATH)
