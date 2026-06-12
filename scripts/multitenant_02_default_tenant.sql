-- ============================================================
-- multitenant_02_default_tenant.sql
-- 目的：讓「舊版 Streamlit 匯入」自動帶上 tenant_id，
--       使匯入的資料立即出現在新平台 (FastAPI + Next.js)。
--
-- 背景：目前只有 1 個 tenant (Justin / 統一證券)。
--       舊匯入流程不知道 tenant_id → 新資料會是 NULL → 新平台看不到。
--       設定欄位 DEFAULT = 該 tenant，即可自動補上。
--
-- 安全性：只新增 DEFAULT + 回填 NULL，不刪除、不修改既有有效資料。
--          將來真的多租戶時，移除 DEFAULT 並改走「新平台的租戶感知匯入」。
--
-- 執行方式：Supabase → SQL Editor → 貼上 → Run (一次即可)。
-- ============================================================

-- Justin / 統一證券 的 tenant id
-- (來源：select id, name from tenants;)
do $$
declare t uuid := '3da82a79-8ef5-4f8c-9df3-faed33e75b64';
begin
  -- 1) 設定每張表 tenant_id 的 DEFAULT
  execute format('alter table customers        alter column tenant_id set default %L', t);
  execute format('alter table structured_notes alter column tenant_id set default %L', t);
  execute format('alter table investments      alter column tenant_id set default %L', t);
  execute format('alter table admins           alter column tenant_id set default %L', t);
  execute format('alter table articles         alter column tenant_id set default %L', t);
  -- alerts 可能不存在，包在 exception 內
  begin
    execute format('alter table alerts alter column tenant_id set default %L', t);
  exception when undefined_table then null;
  end;

  -- 2) 回填任何仍為 NULL 的列 (保險)
  update customers        set tenant_id = t where tenant_id is null;
  update structured_notes set tenant_id = t where tenant_id is null;
  update investments      set tenant_id = t where tenant_id is null;
  update admins           set tenant_id = t where tenant_id is null;
  update articles         set tenant_id = t where tenant_id is null;
  begin
    update alerts set tenant_id = t where tenant_id is null;
  exception when undefined_table then null;
  end;
end $$;

-- 3) 驗證：default 已設定 + 無 NULL
select table_name, column_default
from information_schema.columns
where column_name = 'tenant_id'
  and table_name in ('customers','structured_notes','investments','admins','articles')
order by table_name;

select 'customers null'        as label, count(*) from customers        where tenant_id is null
union all select 'SN null',          count(*) from structured_notes where tenant_id is null
union all select 'investments null', count(*) from investments      where tenant_id is null;
