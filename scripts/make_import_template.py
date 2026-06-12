"""產生空白標準匯入範本 (深綠吉利)。使用統一 builder (utils/excel_template)。
用法: python3 scripts/make_import_template.py -> templates/import_template.xlsx"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.excel_template import build_workbook  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
os.makedirs(OUT_DIR, exist_ok=True)
OUT = os.path.join(OUT_DIR, "import_template.xlsx")

wb = build_workbook(with_sample=True)
wb.save(OUT)
print("wrote", OUT)
