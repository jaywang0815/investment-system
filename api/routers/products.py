"""SN 商品 (structured_notes) CRUD — tenant-scoped。"""
from fastapi import APIRouter, Depends, HTTPException
from ..deps import repo
from ..db import Repo

router = APIRouter(prefix="/api/products", tags=["products"])


# 公司業務分類 (來自名片) + SN
CATEGORIES = ["SN", "台股", "期貨", "美股", "港股", "國內外基金",
              "ELN", "PGN", "儲蓄險", "旅平險", "車險", "意外險"]


@router.get("/categories")
def categories():
    return {"categories": CATEGORIES}


@router.get("")
def list_products(status: str = None, category: str = None, r: Repo = Depends(repo)):
    eq = {}
    if status:
        eq["status"] = status
    if category:
        eq["category"] = category
    if eq:
        return r.find("structured_notes", order="observation_date", **eq)
    return r.list("structured_notes", order="observation_date")


@router.post("")
def create_product(body: dict, r: Repo = Depends(repo)):
    if not (body.get("product_code") or "").strip():
        raise HTTPException(status_code=422, detail="缺少商品代號")
    return r.create("structured_notes", body)


@router.get("/{pid}")
def get_product(pid: str, r: Repo = Depends(repo)):
    p = r.get("structured_notes", pid)
    if not p:
        raise HTTPException(status_code=404, detail="找不到商品")
    return p


@router.put("/{pid}")
def update_product(pid: str, body: dict, r: Repo = Depends(repo)):
    if not r.get("structured_notes", pid):
        raise HTTPException(status_code=404, detail="找不到商品")
    return r.update("structured_notes", pid, body)


@router.delete("/{pid}")
def delete_product(pid: str, r: Repo = Depends(repo)):
    if not r.get("structured_notes", pid):
        raise HTTPException(status_code=404, detail="找不到商品")
    r.delete("structured_notes", pid)
    return {"ok": True}
