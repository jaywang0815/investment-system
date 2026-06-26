-- ช่องโน้ตต่อ SN ในหน้า 到期管理 (เช่น "รอลูกค้าตอบ", "นัดคุย 7/1")
alter table structured_notes add column if not exists maturity_note text;
