-- ════════════════════════════════════════════════════════════════
-- Multi-tenant  Phase 1 — 基礎 schema (ADDITIVE，現有 app 不受影響)
-- 在 Supabase → SQL Editor 貼上執行。可重複執行 (idempotent)。
-- 執行前請先跑 backup: python scripts/backup_supabase.py
-- ════════════════════════════════════════════════════════════════

-- 1) 租戶表
create table if not exists tenants (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  created_at  timestamptz default now()
);

-- 2) 建立第一個租戶 (= 目前所有資料的擁有者 Justin)
insert into tenants (name)
select 'Justin / 統一證券'
where not exists (select 1 from tenants);

-- 3) 後台登入帳號 (Email + 密碼雜湊 + 所屬租戶)
create table if not exists app_users (
  id            uuid primary key default gen_random_uuid(),
  email         text unique not null,
  password_hash text not null,
  tenant_id     uuid not null references tenants(id),
  role          text default 'admin',
  active        boolean default true,
  created_at    timestamptz default now()
);

-- 4) 在所有資料表加上 tenant_id (可為 null → 之後 backfill)
alter table customers        add column if not exists tenant_id uuid references tenants(id);
alter table structured_notes add column if not exists tenant_id uuid references tenants(id);
alter table investments      add column if not exists tenant_id uuid references tenants(id);
alter table admins           add column if not exists tenant_id uuid references tenants(id);
alter table articles         add column if not exists tenant_id uuid references tenants(id);
alter table alerts           add column if not exists tenant_id uuid references tenants(id);

-- 5) 既有資料全部歸到第一個租戶
do $$
declare t uuid;
begin
  select id into t from tenants order by created_at limit 1;
  update customers        set tenant_id = t where tenant_id is null;
  update structured_notes set tenant_id = t where tenant_id is null;
  update investments      set tenant_id = t where tenant_id is null;
  update admins           set tenant_id = t where tenant_id is null;
  update articles         set tenant_id = t where tenant_id is null;
  begin
    update alerts set tenant_id = t where tenant_id is null;
  exception when others then null;
  end;
end $$;

-- 6) 加索引 (依租戶查詢加速)
create index if not exists idx_customers_tenant        on customers(tenant_id);
create index if not exists idx_structured_notes_tenant on structured_notes(tenant_id);
create index if not exists idx_investments_tenant      on investments(tenant_id);

-- 7) 檢查結果
select 'tenants' as tbl, count(*) from tenants
union all select 'app_users', count(*) from app_users
union all select 'customers w/ tenant', count(*) from customers where tenant_id is not null
union all select 'SN w/ tenant', count(*) from structured_notes where tenant_id is not null
union all select 'investments w/ tenant', count(*) from investments where tenant_id is not null;
