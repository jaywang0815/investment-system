-- ============================================================
-- multitenant_04_coupon_config.sql
-- 目的：讓「配息計算方式」可per-SN設定 (未來不同商品/公司可不同算法)。
--   coupon_freq  : 配息頻率 monthly / quarterly / semiannual / annual / maturity
--   coupon_basis : 計息方式 annualized (年化, 需 ÷頻率) / per_period (每期, 直接用)
-- 預設沿用目前邏輯 (月配 + 年化)，符合客戶確認的 FCN 結構。
-- 安全：只新增欄位 + 回填預設，不動既有資料。執行：Supabase SQL Editor → Run。
-- ============================================================

alter table structured_notes add column if not exists coupon_freq  text default 'monthly';
alter table structured_notes add column if not exists coupon_basis text default 'annualized';

update structured_notes set coupon_freq  = coalesce(coupon_freq, 'monthly');
update structured_notes set coupon_basis = coalesce(coupon_basis, 'annualized');

select product_code, coupon_pct, coupon_freq, coupon_basis from structured_notes limit 20;
