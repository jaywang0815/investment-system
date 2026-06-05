"""
Supabase 資料庫操作模組
"""
import streamlit as st
from supabase import create_client, Client
import pandas as pd
from typing import Optional

@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# ============================================================
# 客戶操作
# ============================================================

def get_all_customers() -> pd.DataFrame:
    sb = get_supabase()
    resp = sb.table("customers").select("*").order("name").execute()
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()

def get_customer(customer_id: str) -> Optional[dict]:
    sb = get_supabase()
    resp = sb.table("customers").select("*").eq("id", customer_id).execute()
    return resp.data[0] if resp.data else None

def get_customer_by_token(token: str) -> Optional[dict]:
    sb = get_supabase()
    resp = sb.table("customers").select("*").eq("portal_token", token).execute()
    return resp.data[0] if resp.data else None

def create_customer(data: dict) -> Optional[dict]:
    sb = get_supabase()
    resp = sb.table("customers").insert(data).execute()
    return resp.data[0] if resp.data else None

def update_customer(customer_id: str, data: dict) -> Optional[dict]:
    sb = get_supabase()
    resp = sb.table("customers").update(data).eq("id", customer_id).execute()
    return resp.data[0] if resp.data else None

def delete_customer(customer_id: str) -> bool:
    sb = get_supabase()
    sb.table("customers").delete().eq("id", customer_id).execute()
    return True

# ============================================================
# 結構型商品操作
# ============================================================

def get_all_sns(status: Optional[str] = None) -> pd.DataFrame:
    sb = get_supabase()
    query = sb.table("structured_notes").select("*").order("observation_date")
    if status:
        query = query.eq("status", status)
    resp = query.execute()
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()

def get_sn(sn_id: str) -> Optional[dict]:
    sb = get_supabase()
    resp = sb.table("structured_notes").select("*").eq("id", sn_id).execute()
    return resp.data[0] if resp.data else None

def create_sn(data: dict) -> Optional[dict]:
    sb = get_supabase()
    resp = sb.table("structured_notes").insert(data).execute()
    return resp.data[0] if resp.data else None

def update_sn(sn_id: str, data: dict) -> Optional[dict]:
    sb = get_supabase()
    resp = sb.table("structured_notes").update(data).eq("id", sn_id).execute()
    return resp.data[0] if resp.data else None

def delete_sn(sn_id: str) -> bool:
    sb = get_supabase()
    sb.table("structured_notes").delete().eq("id", sn_id).execute()
    return True

# ============================================================
# 投資記錄操作
# ============================================================

def get_investments_by_customer(customer_id: str) -> list:
    sb = get_supabase()
    resp = sb.table("investments").select(
        "*, structured_notes(*)"
    ).eq("customer_id", customer_id).execute()
    return resp.data or []

def get_investments_by_sn(sn_id: str) -> list:
    sb = get_supabase()
    resp = sb.table("investments").select(
        "*, customers(id, name)"
    ).eq("sn_id", sn_id).execute()
    return resp.data or []

def get_all_investments() -> pd.DataFrame:
    sb = get_supabase()
    resp = sb.table("investments").select(
        "id, amount_usd, created_at, customers(id, name), structured_notes(id, product_code, underlying_1, underlying_2, underlying_3, observation_date, ko_barrier, ki_barrier, strike_pct, status)"
    ).execute()
    rows = []
    for item in (resp.data or []):
        row = {
            "id": item["id"],
            "amount_usd": item["amount_usd"],
            "customer_id": item["customers"]["id"] if item.get("customers") else None,
            "customer_name": item["customers"]["name"] if item.get("customers") else None,
            "sn_id": item["structured_notes"]["id"] if item.get("structured_notes") else None,
            "product_code": item["structured_notes"]["product_code"] if item.get("structured_notes") else None,
            "underlying_1": item["structured_notes"]["underlying_1"] if item.get("structured_notes") else None,
            "underlying_2": item["structured_notes"]["underlying_2"] if item.get("structured_notes") else None,
            "underlying_3": item["structured_notes"]["underlying_3"] if item.get("structured_notes") else None,
            "observation_date": item["structured_notes"]["observation_date"] if item.get("structured_notes") else None,
            "status": item["structured_notes"]["status"] if item.get("structured_notes") else None,
        }
        rows.append(row)
    return pd.DataFrame(rows) if rows else pd.DataFrame()

def create_investment(customer_id: str, sn_id: str, amount_usd: float) -> Optional[dict]:
    sb = get_supabase()
    resp = sb.table("investments").insert({
        "customer_id": customer_id,
        "sn_id": sn_id,
        "amount_usd": amount_usd
    }).execute()
    return resp.data[0] if resp.data else None

def delete_investment(investment_id: str) -> bool:
    sb = get_supabase()
    sb.table("investments").delete().eq("id", investment_id).execute()
    return True

# ============================================================
# 統計資料
# ============================================================

def get_dashboard_stats() -> dict:
    sb = get_supabase()
    try:
        customers = sb.table("customers").select("id", count="exact").execute()
        sns_active = sb.table("structured_notes").select("id", count="exact").eq("status", "active").execute()
        investments = sb.table("investments").select("amount_usd").execute()

        total_usd = sum(i["amount_usd"] for i in (investments.data or []) if i.get("amount_usd"))

        return {
            "total_customers": customers.count or 0,
            "active_sns": sns_active.count or 0,
            "total_investment_usd": total_usd,
        }
    except Exception as e:
        return {"total_customers": 0, "active_sns": 0, "total_investment_usd": 0}

def save_daily_price(ticker: str, price: float) -> None:
    sb = get_supabase()
    from datetime import date
    try:
        sb.table("daily_prices").upsert({
            "ticker": ticker,
            "price_date": date.today().isoformat(),
            "close_price": price
        }, on_conflict="ticker,price_date").execute()
    except:
        pass

def save_alert(sn_id: str, alert_type: str, message: str) -> None:
    sb = get_supabase()
    try:
        sb.table("alerts").insert({
            "sn_id": sn_id,
            "alert_type": alert_type,
            "message": message
        }).execute()
    except:
        pass

def get_setting(key: str, default: str = "") -> str:
    try:
        sb = get_supabase()
        res = sb.table("app_settings").select("value").eq("key", key).execute()
        if res.data:
            return res.data[0]["value"]
    except Exception:
        pass
    return default

def upsert_setting(key: str, value: str) -> bool:
    try:
        sb = get_supabase()
        sb.table("app_settings").upsert({"key": key, "value": value}, on_conflict="key").execute()
        return True
    except Exception:
        return False
