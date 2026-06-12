-- ============================================================
-- multitenant_05_tenant_logo.sql
-- 目的：每個 tenant 可上傳自己的報表 logo (存 base64 data URL)。
--   logo: text — "data:image/png;base64,...."；空=用預設檔案 logo。
-- 安全：只新增欄位，不動既有資料。執行：Supabase SQL Editor → Run。
-- 備註：建議 logo 圖檔 < 200KB (前端會壓縮/限制)。
-- ============================================================

alter table tenants add column if not exists logo text;

select id, name, company_name, reporter, (logo is not null) as has_logo from tenants;
