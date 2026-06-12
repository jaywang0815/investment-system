"""資料匯入 — 讀標準範本 (依「標題」非位置)，預覽後確認，寫入登入者自己的 tenant。
無 AI、不外傳資料；% 欄 ÷100；日期 ISO；配息頻率/狀態 中→英 對應。"""
import io
import unicodedata
from datetime import datetime, date
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from ..deps import repo
from ..db import Repo

router = APIRouter(prefix="/api/import", tags=["import"])


def _norm(s) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", str(s))
    return s.replace("*", "").replace(" ", "").replace("\n", "").strip().lower()


# field -> header aliases (normalized compare)
CUST = {
    "name": ["姓名", "戶名", "客戶姓名", "name", "客戶"],
    "usd_amount": ["美元額度", "金額", "usd", "amount", "美金"],
    "currency": ["幣別", "currency", "幣"],
    "unified_account": ["統一帳號", "帳號", "account", "統一開戶"],
    "notes": ["備註", "備注", "notes", "note"],
}
PROD = {
    "product_code": ["商品代號", "代號", "code", "product"],
    "category": ["類別", "category", "類型"],
    "underlying_1": ["標的1", "標的一", "underlying1", "標的"],
    "initial_price_1": ["期初價1", "期初價格1", "初始價1", "initial1"],
    "underlying_2": ["標的2", "標的二", "underlying2"],
    "initial_price_2": ["期初價2", "期初價格2", "initial2"],
    "underlying_3": ["標的3", "標的三", "underlying3"],
    "initial_price_3": ["期初價3", "期初價格3", "initial3"],
    "ko_barrier": ["ko障壁", "ko水位", "ko提前", "ko"],
    "ki_barrier": ["ki障壁", "ki水位", "ki下限", "ki"],
    "strike_pct": ["履約價", "執行價", "strike", "履約"],
    "coupon_pct": ["票息", "配息", "coupon"],
    "coupon_freq": ["配息頻率", "頻率", "freq"],
    "trade_date": ["成交日", "交易日", "trade"],
    "observation_date": ["比價日", "比價", "觀察日", "obs"],
    "exit_date": ["到期日", "出場日", "到期", "exit", "maturity"],
    "status": ["狀態", "status"],
}
INV = {
    "customer": ["客戶姓名", "姓名", "戶名", "客戶", "customer"],
    "product_code": ["商品代號", "代號", "code"],
    "amount_usd": ["投資金額", "金額", "amount", "下單金額"],
    "currency": ["幣別", "currency"],
}
FREQ_MAP = {"月配": "monthly", "季配": "quarterly", "半年配": "semiannual", "年配": "annual", "到期一次": "maturity"}
STATUS_MAP = {"進行中": "active", "已出場": "exited", "暫停": "inactive"}
SHEET_HINT = {"客戶": "cust", "投資人": "cust", "customer": "cust",
              "商品": "prod", "product": "prod", "sn": "prod",
              "投資": "inv", "持倉": "inv", "holding": "inv"}


def _to_date(v):
    if v is None or v == "":
        return None
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d")
    s = str(v)[:10]
    return s or None


def _to_pct(v):
    """填的是百分比數字 (KO=100) → 0..1 fraction。"""
    if v is None or v == "":
        return None
    try:
        return round(float(v) / 100.0, 6)
    except (TypeError, ValueError):
        return None


def _to_num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _map_headers(ws, aliases: dict):
    """หาแถวหัวตาราง + แมพ field -> column index。คืน (header_row_idx, {field: col})。"""
    best_row, best_map = None, {}
    for r in range(1, min(ws.max_row, 8) + 1):
        colmap = {}
        for c in range(1, ws.max_column + 1):
            h = _norm(ws.cell(r, c).value)
            if not h:
                continue
            for field, al in aliases.items():
                if field in colmap:
                    continue
                if any(_norm(a) == h or _norm(a) in h for a in al):
                    colmap[field] = c
                    break
        if len(colmap) > len(best_map):
            best_map, best_row = colmap, r
    return best_row, best_map


def _rows(ws, hr, colmap):
    out = []
    for r in range(hr + 1, ws.max_row + 1):
        rec = {f: ws.cell(r, c).value for f, c in colmap.items()}
        if all(v is None or str(v).strip() == "" for v in rec.values()):
            continue
        out.append(rec)
    return out


def parse_workbook(data: bytes) -> dict:
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(data), data_only=True)
    customers, products, investments, warnings = [], [], [], []

    # หา sheet ของแต่ละชนิดจากชื่อ
    kind_sheets = {"cust": None, "prod": None, "inv": None}
    for sn in wb.sheetnames:
        n = _norm(sn)
        for hint, kind in SHEET_HINT.items():
            if _norm(hint) in n and kind_sheets[kind] is None:
                kind_sheets[kind] = sn

    # 客戶
    if kind_sheets["cust"]:
        ws = wb[kind_sheets["cust"]]
        hr, cm = _map_headers(ws, CUST)
        if "name" in cm:
            for rec in _rows(ws, hr, cm):
                nm = rec.get("name")
                if not nm or _norm(nm) in ("姓名", "戶名"):
                    continue
                customers.append({
                    "name": str(nm).strip(),
                    "usd_amount": _to_num(rec.get("usd_amount")),
                    "currency": (str(rec.get("currency")).strip() if rec.get("currency") else "USD"),
                    "unified_account": (str(rec.get("unified_account")).strip() if rec.get("unified_account") else None),
                    "notes": (str(rec.get("notes")).strip() if rec.get("notes") else None),
                })
        else:
            warnings.append("「客戶」分頁找不到姓名欄")

    # 商品
    if kind_sheets["prod"]:
        ws = wb[kind_sheets["prod"]]
        hr, cm = _map_headers(ws, PROD)
        if "product_code" in cm:
            for rec in _rows(ws, hr, cm):
                code = rec.get("product_code")
                if not code or _norm(code) in ("代號", "商品代號", "期初價格"):
                    continue
                fr = rec.get("coupon_freq")
                st = rec.get("status")
                products.append({
                    "product_code": str(code).strip(),
                    "category": (str(rec.get("category")).strip() if rec.get("category") else "SN"),
                    "underlying_1": (str(rec.get("underlying_1")).strip().upper() if rec.get("underlying_1") else None),
                    "underlying_2": (str(rec.get("underlying_2")).strip().upper() if rec.get("underlying_2") else None),
                    "underlying_3": (str(rec.get("underlying_3")).strip().upper() if rec.get("underlying_3") else None),
                    "initial_price_1": _to_num(rec.get("initial_price_1")),
                    "initial_price_2": _to_num(rec.get("initial_price_2")),
                    "initial_price_3": _to_num(rec.get("initial_price_3")),
                    "ko_barrier": _to_pct(rec.get("ko_barrier")),
                    "ki_barrier": _to_pct(rec.get("ki_barrier")),
                    "strike_pct": _to_pct(rec.get("strike_pct")),
                    "coupon_pct": _to_pct(rec.get("coupon_pct")),
                    "coupon_freq": FREQ_MAP.get(str(fr).strip(), "monthly") if fr else "monthly",
                    "trade_date": _to_date(rec.get("trade_date")),
                    "observation_date": _to_date(rec.get("observation_date")),
                    "exit_date": _to_date(rec.get("exit_date")),
                    "status": STATUS_MAP.get(str(st).strip(), "active") if st else "active",
                })
        else:
            warnings.append("「商品」分頁找不到商品代號欄")

    # 投資
    if kind_sheets["inv"]:
        ws = wb[kind_sheets["inv"]]
        hr, cm = _map_headers(ws, INV)
        if "customer" in cm and "product_code" in cm:
            for rec in _rows(ws, hr, cm):
                cu = rec.get("customer"); pc = rec.get("product_code")
                if not cu or not pc:
                    continue
                investments.append({
                    "customer": str(cu).strip(),
                    "product_code": str(pc).strip(),
                    "amount_usd": _to_num(rec.get("amount_usd")) or 0,
                    "currency": (str(rec.get("currency")).strip() if rec.get("currency") else "USD"),
                })
        else:
            warnings.append("「投資」分頁找不到 客戶姓名/商品代號 欄")

    if not any(kind_sheets.values()):
        warnings.append("找不到 客戶/商品/投資 分頁，請使用標準範本")

    return {"customers": customers, "products": products, "investments": investments, "warnings": warnings}


@router.post("/preview")
async def preview(file: UploadFile = File(...), r: Repo = Depends(repo)):
    try:
        data = await file.read()
        return parse_workbook(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"讀取檔案失敗: {e}")


@router.post("/commit")
def commit(body: dict, r: Repo = Depends(repo)):
    """寫入登入者自己的 tenant，去重 (依姓名/代號)，連結投資。"""
    custs = body.get("customers") or []
    prods = body.get("products") or []
    invs = body.get("investments") or []
    res = {"customers_created": 0, "customers_updated": 0,
           "products_created": 0, "products_updated": 0,
           "investments_created": 0, "investments_skipped": 0, "warnings": []}

    # customers (upsert by name within tenant)
    name2id = {}
    for cu in custs:
        nm = (cu.get("name") or "").strip()
        if not nm:
            continue
        payload = {k: cu.get(k) for k in ("name", "usd_amount", "currency", "unified_account", "notes")}
        existing = r.find("customers", name=nm)
        if existing:
            cid = existing[0]["id"]
            r.update("customers", cid, payload)
            res["customers_updated"] += 1
        else:
            cid = r.create("customers", payload)["id"]
            res["customers_created"] += 1
        name2id[nm] = cid

    # products (upsert by product_code)
    code2id = {}
    PFIELDS = ("product_code", "category", "underlying_1", "underlying_2", "underlying_3",
               "initial_price_1", "initial_price_2", "initial_price_3", "ko_barrier", "ki_barrier",
               "strike_pct", "coupon_pct", "coupon_freq", "trade_date", "observation_date", "exit_date", "status")
    from .products import _safe_write  # reuse column-resilient writer
    for p in prods:
        code = (p.get("product_code") or "").strip()
        if not code:
            continue
        payload = {k: p.get(k) for k in PFIELDS if p.get(k) is not None}
        existing = r.find("structured_notes", product_code=code)
        if existing:
            pid = existing[0]["id"]
            _safe_write(lambda b, _pid=pid: r.update("structured_notes", _pid, b), payload)
            res["products_updated"] += 1
        else:
            pid = _safe_write(lambda b: r.create("structured_notes", b), payload)["id"]
            res["products_created"] += 1
        code2id[code] = pid

    # resolve names/codes not in this import from existing DB
    def cust_id(nm):
        if nm in name2id:
            return name2id[nm]
        ex = r.find("customers", name=nm)
        if ex:
            name2id[nm] = ex[0]["id"]; return ex[0]["id"]
        return None

    def prod_id(code):
        if code in code2id:
            return code2id[code]
        ex = r.find("structured_notes", product_code=code)
        if ex:
            code2id[code] = ex[0]["id"]; return ex[0]["id"]
        return None

    for iv in invs:
        cid = cust_id((iv.get("customer") or "").strip())
        pid = prod_id((iv.get("product_code") or "").strip())
        if not cid or not pid:
            res["investments_skipped"] += 1
            res["warnings"].append(f"連結失敗: {iv.get('customer')} / {iv.get('product_code')}")
            continue
        dup = [x for x in r.find("investments", customer_id=cid) if x.get("sn_id") == pid]
        if dup:
            res["investments_skipped"] += 1
            continue
        r.create("investments", {"customer_id": cid, "sn_id": pid,
                                 "amount_usd": iv.get("amount_usd") or 0,
                                 "currency": iv.get("currency") or "USD"})
        res["investments_created"] += 1

    return res
