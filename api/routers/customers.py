"""客戶 CRUD — 全部經由 Repo，自動限定登入者的 tenant_id。"""
import math
from fastapi import APIRouter, Depends, HTTPException
from ..deps import repo
from ..db import Repo

router = APIRouter(prefix="/api/customers", tags=["customers"])


def _f(v):
    try:
        f = float(v) if v not in (None, "") else 0.0
        return 0.0 if math.isnan(f) else f
    except (TypeError, ValueError):
        return 0.0


@router.get("")
def list_customers(r: Repo = Depends(repo)):
    custs = r.list("customers", order="name")
    invested: dict = {}
    try:
        for i in r.list("investments", select="customer_id,amount_usd"):
            cid = i.get("customer_id")
            if cid:
                invested[cid] = invested.get(cid, 0.0) + _f(i.get("amount_usd"))
    except Exception:
        pass
    for c in custs:
        cid = c.get("id")
        c["has_investments"] = cid in invested
        c["invested_total"] = invested.get(cid, 0.0)
    return custs


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


@router.post("/{cid}/merge-into/{target_id}")
def merge_customer(cid: str, target_id: str, r: Repo = Depends(repo)):
    """รวมลูกค้า cid (เช่นชื่อเล่น 莫姐) เข้ากับ target (ชื่อเต็ม 莫新鳳)：
    ย้ายการลงทุนไป target (ตัดที่ซ้ำ sn) แล้วลบ cid。"""
    if cid == target_id:
        raise HTTPException(status_code=400, detail="不能合併自己")
    if not r.get("customers", cid) or not r.get("customers", target_id):
        raise HTTPException(status_code=404, detail="找不到客戶")
    moved = 0
    dst_sns = {i.get("sn_id") for i in r.find("investments", customer_id=target_id)}
    for iv in r.find("investments", customer_id=cid):
        if iv.get("sn_id") in dst_sns:
            r.delete("investments", iv["id"])
        else:
            r.update("investments", iv["id"], {"customer_id": target_id})
            dst_sns.add(iv.get("sn_id"))
            moved += 1
    r.delete("customers", cid)
    return {"merged": cid, "into": target_id, "moved": moved}
