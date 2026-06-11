"""
Supabase 連線 + 租戶限定的資料存取層 (Repo)。
**所有讀寫都自動加 .eq("tenant_id", ...) → 是 multi-tenant 不外洩的唯一閘門。**
不依賴 streamlit (供 FastAPI 使用)。
"""
import os
from functools import lru_cache
from supabase import create_client, Client


@lru_cache(maxsize=1)
def get_sb() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


class Repo:
    """每個 request 依登入者的 tenant_id 建立；CRUD 一律限定該租戶。"""

    def __init__(self, sb: Client, tenant_id: str):
        self.sb = sb
        self.tenant_id = tenant_id

    def list(self, table: str, select: str = "*", order: str = None, desc: bool = False):
        q = self.sb.table(table).select(select).eq("tenant_id", self.tenant_id)
        if order:
            q = q.order(order, desc=desc)
        return q.execute().data or []

    def find(self, table: str, select: str = "*", order: str = None, desc: bool = False, **eq):
        """list + 額外等值條件 (一律含 tenant_id)。"""
        q = self.sb.table(table).select(select).eq("tenant_id", self.tenant_id)
        for k, v in eq.items():
            q = q.eq(k, v)
        if order:
            q = q.order(order, desc=desc)
        return q.execute().data or []

    def count(self, table: str, **eq) -> int:
        q = self.sb.table(table).select("id", count="exact").eq("tenant_id", self.tenant_id)
        for k, v in eq.items():
            q = q.eq(k, v)
        return q.execute().count or 0

    def get(self, table: str, row_id: str):
        rows = (self.sb.table(table).select("*")
                .eq("tenant_id", self.tenant_id).eq("id", row_id)
                .execute().data or [])
        return rows[0] if rows else None

    def create(self, table: str, payload: dict):
        payload = {k: v for k, v in payload.items() if k != "id"}
        payload["tenant_id"] = self.tenant_id          # 強制掛上租戶
        return self.sb.table(table).insert(payload).execute().data[0]

    def update(self, table: str, row_id: str, payload: dict):
        payload = {k: v for k, v in payload.items() if k not in ("id", "tenant_id")}
        return (self.sb.table(table).update(payload)
                .eq("tenant_id", self.tenant_id).eq("id", row_id)
                .execute().data)

    def delete(self, table: str, row_id: str):
        return (self.sb.table(table).delete()
                .eq("tenant_id", self.tenant_id).eq("id", row_id)
                .execute())
