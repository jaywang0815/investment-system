"""
統一證券 品牌資產 — logo、報告人署名、配色 (PDF / Excel / PPT 共用)
單一改色處：改這裡即可換整套匯出檔的主題色。
報表可選主題色：見 THEMES / apply_theme()。
"""
from __future__ import annotations
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
C_GOLD    = "B9822F"   # 金 — 裝飾線 / 重點 (名片金)
C_GOLD_SOFT = "F3E6CC" # 淺金底
C_TABLE_HEAD = "CD9A3F" # 明細表頭金 (apply_theme 會覆寫)
C_INK     = "1F1B1B"   # 近黑
C_WHITE   = "FFFFFF"


# ── 報表主題色 (PDF 匯出可選) ──────────────────────────
# 每個主題覆寫品牌「色彩裝飾」(primary/header/accent/tint/zebra/border/gold/gold_soft/table_head)。
# KO/KI 的綠/紅狀態色保持語意不變 (各主題共用)，避免報表喪失風險辨識度。
THEMES: dict[str, dict] = {
    "mono":           {"label": "經典黑白", "primary": "1A1A1A", "header": "333333", "accent": "555555",
                       "tint": "F2F2F2", "zebra": "F8F8F8", "border": "DCDCDC", "gold": "888888",
                       "gold_soft": "ECECEC", "table_head": "E2E2E2"},
    "red_gold":       {"label": "尊爵紅金", "primary": "A62A36", "header": "8E232E", "accent": "C0392B",
                       "tint": "FBEEEF", "zebra": "FAF7F7", "border": "EAD9DB", "gold": "B9822F",
                       "gold_soft": "F3E6CC", "table_head": "CD9A3F"},
    "navy_gold":      {"label": "海軍藍金", "primary": "1E3A5F", "header": "16293F", "accent": "2C5282",
                       "tint": "EAF0F7", "zebra": "F5F8FB", "border": "D6E0EC", "gold": "C9A227",
                       "gold_soft": "F3E8C8", "table_head": "C9A227"},
    "forest_gold":    {"label": "墨綠金", "primary": "1F4D3A", "header": "153A2B", "accent": "2E6B4F",
                       "tint": "E9F2EC", "zebra": "F4F9F6", "border": "D4E5DA", "gold": "B9822F",
                       "gold_soft": "F1E6CC", "table_head": "C2982F"},
    "purple_gold":    {"label": "尊爵紫金", "primary": "4A2C5E", "header": "382046", "accent": "6B4080",
                       "tint": "F1EBF5", "zebra": "F8F4FA", "border": "E2D4EA", "gold": "C9A227",
                       "gold_soft": "F2E8C8", "table_head": "C9A227"},
    "espresso_gold":  {"label": "深咖金", "primary": "3E2723", "header": "2A1A17", "accent": "5D4037",
                       "tint": "F2ECEA", "zebra": "F8F4F2", "border": "E2D6D0", "gold": "C9A227",
                       "gold_soft": "F2E8C8", "table_head": "C9A227"},
    "burgundy_silver": {"label": "酒紅銀", "primary": "6E1423", "header": "53101B", "accent": "8E1B2E",
                        "tint": "F6EAEC", "zebra": "FAF5F6", "border": "E6D2D5", "gold": "9AA0A6",
                        "gold_soft": "E9EBED", "table_head": "B0B5BA"},
    "teal_gold":      {"label": "湖青金", "primary": "0F4C5C", "header": "0A3742", "accent": "156B7F",
                       "tint": "E6F1F3", "zebra": "F3F9FA", "border": "CFE3E7", "gold": "C9A227",
                       "gold_soft": "F2E8C8", "table_head": "C9A227"},
}
DEFAULT_THEME = "red_gold"


def themes_list() -> list[dict]:
    """ให้ frontend แสดงตัวเลือก: [{key,label,primary,gold}]。"""
    return [{"key": k, "label": v["label"], "primary": hx(v["primary"]), "gold": hx(v["gold"])}
            for k, v in THEMES.items()]


def apply_theme(key: str | None) -> None:
    """覆寫品牌裝飾色為指定主題 (PDF 匯出用)。未知 key → 預設。"""
    global C_PRIMARY, C_HEADER, C_ACCENT, C_TINT, C_ZEBRA, C_BORDER, C_GOLD, C_GOLD_SOFT, C_TABLE_HEAD
    t = THEMES.get(key or DEFAULT_THEME, THEMES[DEFAULT_THEME])
    C_PRIMARY = t["primary"]; C_HEADER = t["header"]; C_ACCENT = t["accent"]
    C_TINT = t["tint"]; C_ZEBRA = t["zebra"]; C_BORDER = t["border"]
    C_GOLD = t["gold"]; C_GOLD_SOFT = t["gold_soft"]; C_TABLE_HEAD = t["table_head"]


def hx(c: str) -> str:
    """'B23A2B' -> '#B23A2B' (for reportlab / matplotlib)."""
    return c if c.startswith("#") else "#" + c


def has_logo() -> bool:
    return os.path.exists(LOGO_PATH)
