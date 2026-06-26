-- สถานะจัดการตอนใกล้ครบกำหนด (到期管理) ต่อ SN
-- pending=待處理 (default) / contacted=已聯絡客戶 / rolled=已轉倉
alter table structured_notes add column if not exists maturity_status text default 'pending';
