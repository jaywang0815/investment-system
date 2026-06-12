-- ============================================================
-- multitenant_06_invites.sql
-- 目的：多租戶「邀請制」開通 — 超級管理員(平台擁有者)建立租戶+寄邀請，
--       新「客戶(advisor/tenant)」開邀請連結自行設定密碼 (hands-off)。
-- 安全：只新增表/欄位 + 設定既有使用者為 superadmin，不動既有資料。
-- 執行：Supabase → SQL Editor → Run。
-- ============================================================

-- 1) 邀請表
create table if not exists invites (
  id           uuid primary key default gen_random_uuid(),
  token        text unique not null,
  email        text not null,
  tenant_id    uuid references tenants(id),
  company_name text,
  reporter     text,
  created_at   timestamptz default now(),
  expires_at   timestamptz,
  used         boolean default false
);
create index if not exists idx_invites_token on invites(token);

-- 2) 確保 tenants 有品牌欄位 (與 03/05 idempotent)
alter table tenants add column if not exists company_name text;
alter table tenants add column if not exists reporter     text;
alter table tenants add column if not exists logo         text;

-- 3) 設平台擁有者為 superadmin (建立租戶/寄邀請的權限)
update app_users set role = 'superadmin' where email = 'pmjatu1508@gmail.com';

select email, role from app_users;
