-- ============================================================
-- multitenant_09_product_type.sql
-- 目的：แยกประเภทสินค้า FCN vs DRA (區間計息/Range Accrual)。
--   FCN = คูปองการันตีรายเดือน (ระบบคิดอัตโนมัติ)
--   DRA = Callable Range Accrual อิง rate — คูปอง path-dependent (ยังไม่คิดอัตโนมัติ เฟส 1)
-- 執行方式：Supabase → SQL Editor → 貼上 → Run。รันซ้ำได้ปลอดภัย (idempotent)。
-- ============================================================

alter table structured_notes add column if not exists product_type text default 'FCN';

-- ของเดิมทั้งหมดเป็น FCN (รายเดือน) → backfill ให้ค่าที่ยังว่างเป็น FCN
update structured_notes set product_type = 'FCN' where product_type is null;

select product_type, count(*) from structured_notes group by product_type;
