"""
投資管理 Platform — REST API (FastAPI, multi-tenant)
本地啟動: uvicorn api.main:app --reload --port 8000  (從 repo 根目錄)
需要環境變數: SUPABASE_URL, SUPABASE_KEY, JWT_SECRET
此服務為「新平台後端」，與現有 Streamlit / LINE bot 互不影響。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import auth, customers, products, investments, dashboard, reports, market

app = FastAPI(title="Investment Platform API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # 上線後改為 Next.js 後台網域
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(products.router)
app.include_router(investments.router)
app.include_router(dashboard.router)
app.include_router(reports.router)


@app.get("/")
def root():
    return {"status": "platform API running", "version": "0.1.0"}


@app.get("/health")
def health():
    return {"ok": True}
