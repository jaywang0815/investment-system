"""投資記錄 (investments) — tenant-scoped。可依客戶或商品查詢。"""
from fastapi import APIRouter, Depends, HTTPException
from ..deps import repo
from ..db import Repo

router = APIRouter(prefix="/api/investments", tags=["investments"])

_SEL = "id,amount_usd,currency,customer_id,sn_id,structured_notes(*),customers(name)"


@router.get("")
def list_investments(customer_id: str = None, sn_id: str = None, r: Repo = Depends(repo)):
    eq = {}
    if customer_id:
        eq["customer_id"] = customer_id
    if sn_id:
        eq["sn_id"] = sn_id
    return r.find("investments", select=_SEL, **eq)


@router.post("")
def create_investment(body: dict, r: Repo = Depends(repo)):
    for k in ("customer_id", "sn_id"):
        if not body.get(k):
            raise HTTPException(status_code=422, detail=f"缺少 {k}")
    # 防越權: customer / SN 必須屬於同一租戶
    if not r.get("customers", body["customer_id"]):
        raise HTTPException(status_code=403, detail="客戶不屬於此租戶")
    if not r.get("structured_notes", body["sn_id"]):
        raise HTTPException(status_code=403, detail="商品不屬於此租戶")
    return r.create("investments", {
        "customer_id": body["customer_id"],
        "sn_id": body["sn_id"],
        "amount_usd": body.get("amount_usd") or 0,
        "currency": body.get("currency", "USD"),
    })


@router.delete("/{iid}")
def delete_investment(iid: str, r: Repo = Depends(repo)):
    if not r.get("investments", iid):
        raise HTTPException(status_code=404, detail="找不到投資記錄")
    r.delete("investments", iid)
    return {"ok": True}
