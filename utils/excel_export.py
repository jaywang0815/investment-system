"""
Excel 匯出 & Google Sheets 同步模組
"""
import io
from datetime import date
from typing import Optional
import pandas as pd
import streamlit as st

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False


# ============================================================
# Excel 匯出
# ============================================================

def export_to_excel(customers_df: pd.DataFrame, sns_df: pd.DataFrame,
                    investments_df: pd.DataFrame) -> bytes:
    """匯出所有資料為 Excel 檔案"""
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        # 客戶資料
        customers_out = customers_df.copy()
        for col in ["unified_account", "pi_signed", "ordered"]:
            if col in customers_out.columns:
                customers_out[col] = customers_out[col].map({True: "Ｖ", False: ""})
        col_rename = {
            "name": "戶名", "unified_account": "統一開戶",
            "pi_signed": "PI見簽", "ordered": "已下單",
            "usd_amount": "USD金額", "ctbc_position": "中信部位",
            "fund_amount": "FUND", "notes": "備註"
        }
        customers_out = customers_out.rename(columns=col_rename)
        display_cols = [c for c in col_rename.values() if c in customers_out.columns]
        customers_out[display_cols].to_excel(writer, sheet_name="客戶資料", index=False)

        # SN 商品資料
        sns_out = sns_df.copy()
        sn_col_rename = {
            "product_code": "商品代號", "trade_date": "交易日期",
            "underlying_1": "標的1", "underlying_2": "標的2",
            "underlying_3": "標的3", "underlying_4": "標的4",
            "underlying_5": "標的5", "initial_price_1": "期初價1",
            "initial_price_2": "期初價2", "initial_price_3": "期初價3",
            "initial_price_4": "期初價4", "initial_price_5": "期初價5",
            "strike_pct": "執行價%", "coupon_pct": "配息%",
            "observation_date": "比價日", "ko_barrier": "KO水位",
            "ki_barrier": "KI水位", "status": "狀態",
            "total_order_amount": "總下單金額", "month_label": "月份"
        }
        sns_out = sns_out.rename(columns=sn_col_rename)
        for col in ["執行價%", "配息%", "KO水位", "KI水位"]:
            if col in sns_out.columns:
                sns_out[col] = sns_out[col].apply(
                    lambda x: f"{x*100:.2f}%" if pd.notna(x) else ""
                )
        status_map = {
            "active": "有效", "ko_triggered": "KO觸發",
            "ki_triggered": "KI觸發", "expired": "已到期", "matured": "已結算"
        }
        if "狀態" in sns_out.columns:
            sns_out["狀態"] = sns_out["狀態"].map(status_map).fillna(sns_out["狀態"])
        display_sn_cols = [c for c in sn_col_rename.values() if c in sns_out.columns]
        sns_out[display_sn_cols].to_excel(writer, sheet_name="SN商品", index=False)

        # 投資記錄
        if not investments_df.empty:
            inv_out = investments_df.copy()
            inv_col_rename = {
                "customer_name": "客戶姓名", "product_code": "商品代號",
                "amount_usd": "投資金額(USD)", "underlying_1": "標的1",
                "underlying_2": "標的2", "underlying_3": "標的3",
                "observation_date": "比價日", "status": "狀態"
            }
            inv_out = inv_out.rename(columns=inv_col_rename)
            display_inv_cols = [c for c in inv_col_rename.values() if c in inv_out.columns]
            inv_out[display_inv_cols].to_excel(writer, sheet_name="投資記錄", index=False)

        # 格式化
        wb = writer.book
        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 30)

    return buffer.getvalue()


# ============================================================
# Google Sheets 同步
# ============================================================

def sync_to_google_sheets(customers_df: pd.DataFrame, sns_df: pd.DataFrame,
                           sheet_id: Optional[str] = None) -> bool:
    """同步資料到 Google Sheets"""
    if not GSPREAD_AVAILABLE:
        st.error("gspread 未安裝，請執行 pip install gspread")
        return False

    try:
        sheet_id = sheet_id or st.secrets.get("GOOGLE_SHEET_ID")
        if not sheet_id:
            st.error("請在 secrets.toml 設定 GOOGLE_SHEET_ID")
            return False

        # 使用 service account
        creds_info = st.secrets.get("GOOGLE_SERVICE_ACCOUNT")
        if not creds_info:
            st.error("請在 secrets.toml 設定 GOOGLE_SERVICE_ACCOUNT")
            return False

        creds = Credentials.from_service_account_info(
            dict(creds_info),
            scopes=["https://spreadsheets.google.com/feeds",
                    "https://www.googleapis.com/auth/drive"]
        )
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(sheet_id)

        # 同步客戶資料
        try:
            ws = spreadsheet.worksheet("客戶資料")
        except gspread.WorksheetNotFound:
            ws = spreadsheet.add_worksheet("客戶資料", rows=200, cols=20)

        ws.clear()
        customers_out = customers_df[["name", "usd_amount", "ctbc_position",
                                       "unified_account", "pi_signed", "ordered"]].copy()
        customers_out.columns = ["戶名", "USD金額", "中信部位", "統一開戶", "PI見簽", "已下單"]
        ws.update([customers_out.columns.tolist()] + customers_out.fillna("").values.tolist())

        # 同步 SN 商品
        try:
            ws2 = spreadsheet.worksheet("SN商品")
        except gspread.WorksheetNotFound:
            ws2 = spreadsheet.add_worksheet("SN商品", rows=200, cols=20)

        ws2.clear()
        sns_out = sns_df[["product_code", "trade_date", "underlying_1", "underlying_2",
                            "underlying_3", "strike_pct", "coupon_pct",
                            "observation_date", "ko_barrier", "ki_barrier", "status"]].copy()
        sns_out.columns = ["代號", "日期", "標的1", "標的2", "標的3",
                            "執行價%", "配息%", "比價日", "KO水位", "KI水位", "狀態"]
        ws2.update([sns_out.columns.tolist()] + sns_out.fillna("").astype(str).values.tolist())

        return True

    except Exception as e:
        st.error(f"Google Sheets 同步失敗: {e}")
        return False
