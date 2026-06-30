-- รองรับฟอร์แมตเต็มของ 統一證券 (庫存查詢) — เก็บคอลัมน์ที่ขาด 9 ตัวต่อ SN
alter table structured_notes add column if not exists issue_date date;                  -- 發行日
alter table structured_notes add column if not exists final_pricing_date date;          -- 期末訂價日
alter table structured_notes add column if not exists tenor_months int;                 -- 天期(月)
alter table structured_notes add column if not exists ko_type text;                      -- 提前出場型式 (Daily Memory)
alter table structured_notes add column if not exists ki_type text;                      -- 下限型式 (AKI/EKI)
alter table structured_notes add column if not exists settlement_days int;              -- 交割日 (T+N วัน, เช่น 7)
alter table structured_notes add column if not exists guaranteed_coupon_months int;     -- 保證配息月數
alter table structured_notes add column if not exists counterparty text;                -- 成交上手 (UBS/SG/BNP…)
alter table structured_notes add column if not exists price_type text;                  -- 價格 (收盤價/開盤價)
