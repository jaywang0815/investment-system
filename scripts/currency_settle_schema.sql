-- 多幣別 + 結算可手動調整 — 貼到 Supabase SQL Editor 執行一次
alter table investments add column if not exists currency      text default 'USD';
alter table investments add column if not exists settle_coupon numeric;   -- 手動調整後的配息 (空=用系統計算)
alter table investments add column if not exists settle_note   text;      -- 結算備註
alter table customers    add column if not exists currency      text default 'USD';
