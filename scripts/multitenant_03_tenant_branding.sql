-- ============================================================
-- multitenant_03_tenant_branding.sql
-- 目的：每個 tenant 可自訂報表品牌 (公司名稱 / 報告人)，
--       匯出 PDF 時依登入者所屬 tenant 套用。
-- 安全性：只新增欄位 + 回填現有 tenant，不動既有資料。
-- 執行：Supabase → SQL Editor → 貼上 → Run。
-- ============================================================

alter table tenants add column if not exists company_name text;
alter table tenants add column if not exists reporter     text;

-- 回填第一個 tenant (Justin / 統一證券) 的預設值
update tenants
set company_name = coalesce(company_name, '統一證券'),
    reporter     = coalesce(reporter, '秦聖鈞')
where id = '3da82a79-8ef5-4f8c-9df3-faed33e75b64';

select id, name, company_name, reporter from tenants;
