"""
投資管理 Platform — REST API (FastAPI, multi-tenant)
本地啟動: uvicorn api.main:app --reload --port 8000  (從 repo 根目錄)
需要環境變數: SUPABASE_URL, SUPABASE_KEY, JWT_SECRET
此服務為「新平台後端」，與現有 Streamlit / LINE bot 互不影響。
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import auth, customers, products, investments, dashboard, reports, market, risk, calendar, settings, coupons, admin_tenants, invite, import_data, export_data

app = FastAPI(title="Investment Platform API", version="0.1.0")

# 用 Bearer token (非 cookie) → allow_credentials=False 才能搭配 "*" (避免 prod 跨網域被擋)。
# 可用環境變數 CORS_ORIGINS (逗號分隔) 限制來源；未設則允許全部。
_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(products.router)
app.include_router(investments.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(market.router)
app.include_router(risk.router)
app.include_router(calendar.router)
app.include_router(settings.router)
app.include_router(coupons.router)
app.include_router(admin_tenants.router)
app.include_router(invite.router)
app.include_router(import_data.router)
app.include_router(export_data.router)


@app.get("/")
def root():
    return {"status": "platform API running", "version": "0.1.0"}


@app.get("/health")
def health():
    return {"ok": True}
