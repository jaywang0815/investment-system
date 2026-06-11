"""客戶 CRUD — 全部經由 Repo，自動限定登入者的 tenant_id。"""
from fastapi import APIRouter, Depends, HTTPException
from ..deps import repo
from ..db import Repo

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("")
def list_customers(r: Repo = Depends(repo)):
    return r.list("customers", order="name")


@router.post("")
def create_customer(body: dict, r: Repo = Depends(repo)):
    if not (body.get("name") or "").strip():
        raise HTTPException(status_code=422, detail="缺少客戶姓名")
    return r.create("customers", body)


@router.get("/{cid}")
def get_customer(cid: str, r: Repo = Depends(repo)):
    c = r.get("customers", cid)
    if not c:
        raise HTTPException(status_code=404, detail="找不到客戶")
    return c


@router.put("/{cid}")
def update_customer(cid: str, body: dict, r: Repo = Depends(repo)):
    if not r.get("customers", cid):
        raise HTTPException(status_code=404, detail="找不到客戶")
    return r.update("customers", cid, body)


@router.delete("/{cid}")
def delete_customer(cid: str, r: Repo = Depends(repo)):
    if not r.get("customers", cid):
        raise HTTPException(status_code=404, detail="找不到客戶")
    r.delete("customers", cid)
    return {"ok": True}
