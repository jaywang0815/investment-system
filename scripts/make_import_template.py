"""產生標準匯入範本 import_template.xlsx (乾淨、標題明確、含下拉/範例/說明)。
用法: python3 scripts/make_import_template.py  -> 輸出 templates/import_template.xlsx
未來新平台的 importer 依此範本的「標題」讀取 (非位置)。"""
import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
os.makedirs(OUT_DIR, exist_ok=True)
OUT = os.path.join(OUT_DIR, "import_template.xlsx")

RED = "A62A36"; GOLD = "B9822F"; LIGHT = "FBEEEF"; GREY = "F2F2F2"
HEAD_FILL = PatternFill("solid", fgColor=RED)
SAMPLE_FILL = PatternFill("solid", fgColor=GREY)
HEAD_FONT = Font(bold=True, color="FFFFFF", size=11)
THIN = Side(style="thin", color="D9D9D9")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

CATEGORIES = ["SN", "台股", "期貨", "美股", "港股", "國內外基金", "ELN", "PGN", "儲蓄險", "旅平險", "車險", "意外險"]
CURRENCIES = ["USD", "TWD", "HKD", "EUR", "JPY", "CNY"]
FREQ = ["月配", "季配", "半年配", "年配", "到期一次"]
STATUS = ["進行中", "已出場", "暫停"]


def _headers(ws, headers, widths):
    for i, (h, w) in enumerate(zip(headers, widths), 1):
        c = ws.cell(row=1, column=i, value=h)
        c.fill = HEAD_FILL; c.font = HEAD_FONT; c.border = BORDER
        c.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[chr(64 + i) if i <= 26 else "A" + chr(64 + i - 26)].width = w
    ws.row_dimensions[1].height = 22
    ws.freeze_panes = "A2"


def _sample(ws, row_idx, values):
    for i, v in enumerate(values, 1):
        c = ws.cell(row=row_idx, column=i, value=v)
        c.fill = SAMPLE_FILL; c.border = BORDER
        c.font = Font(italic=True, color="888888")


def _dropdown(ws, col_letter, options, rows=200):
    dv = DataValidation(type="list", formula1='"' + ",".join(options) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"{col_letter}2:{col_letter}{rows}")


wb = Workbook()

# ── 0) 說明 ──────────────────────────────────────────────
ws0 = wb.active; ws0.title = "說明"
ws0.column_dimensions["A"].width = 100
lines = [
    ("統一證券 / Justinvestment — 資料匯入範本", True),
    ("", False),
    ("請依下列分頁填寫，灰色斜體列為「範例」，匯入前請刪除範例列。", False),
    ("", False),
    ("【客戶】= 投資人 (你服務的客戶)。必填：姓名。", False),
    ("【商品】= 結構型商品 (SN/ELN/PGN…)。必填：商品代號。SN 類才需填 KO/KI/票息/標的。", False),
    ("【投資】= 把投資人連到商品 (持倉)。必填：客戶姓名、商品代號、投資金額。", False),
    ("", False),
    ("格式規定：", True),
    ("• 日期：YYYY-MM-DD (例 2026-06-18)", False),
    ("• 百分比欄 (KO/KI/履約/票息)：填數字即可，例 KO=100、KI=60、票息=8 (代表 8% 年化)", False),
    ("• 金額：純數字，不要逗號或貨幣符號", False),
    ("• 配息頻率：月配 / 季配 / 半年配 / 年配 / 到期一次", False),
    ("• 客戶姓名（投資分頁）必須與【客戶】分頁的姓名一字不差，才能正確連結", False),
]
for r, (txt, bold) in enumerate(lines, 1):
    c = ws0.cell(row=r, column=1, value=txt)
    c.font = Font(bold=bold, size=14 if (bold and r == 1) else 11, color=RED if r == 1 else "1F1B1B")
    c.alignment = Alignment(wrap_text=True, vertical="center")

# ── 1) 客戶 (投資人) ──────────────────────────────────────
ws1 = wb.create_sheet("客戶")
_headers(ws1, ["姓名*", "美元額度", "幣別", "統一帳號", "備註"], [16, 14, 8, 16, 30])
_sample(ws1, 2, ["蔣太太", 370000, "USD", "", "範例列，請刪除"])
_dropdown(ws1, "C", CURRENCIES)

# ── 2) 商品 (SN) ─────────────────────────────────────────
ws2 = wb.create_sheet("商品")
h2 = ["商品代號*", "類別", "標的1", "期初價1", "標的2", "期初價2", "標的3", "期初價3",
      "KO障壁(%)", "KI障壁(%)", "履約價(%)", "票息(%年化)", "配息頻率", "成交日", "比價日", "到期日", "狀態"]
_headers(ws2, h2, [16, 10, 9, 9, 9, 9, 9, 9, 11, 11, 11, 12, 11, 12, 12, 12, 10])
_sample(ws2, 2, ["EQDS0702653", "SN", "TSLA", 250.5, "TSM", 180.2, "ANET", 95.0,
                 100, 60, 100, 8, "月配", "2026-05-11", "2026-06-18", "", "進行中"])
_dropdown(ws2, "B", CATEGORIES)
_dropdown(ws2, "M", FREQ)
_dropdown(ws2, "Q", STATUS)

# ── 3) 投資 (持倉) ───────────────────────────────────────
ws3 = wb.create_sheet("投資")
_headers(ws3, ["客戶姓名*", "商品代號*", "投資金額*", "幣別"], [16, 16, 14, 8])
_sample(ws3, 2, ["蔣太太", "EQDS0702653", 370000, "USD"])
_dropdown(ws3, "D", CURRENCIES)

wb.save(OUT)
print("wrote", OUT)
