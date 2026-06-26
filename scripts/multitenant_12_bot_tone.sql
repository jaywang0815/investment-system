-- โทนการพูดของ LINE bot แยกราย tenant
-- default 'polite' (สุภาพมืออาชีพ) → ลูกค้าใหม่ทุกคนได้อันนี้อัตโนมัติ
-- DOUU เคยตั้งโทน "เพื่อนหยอก" ไว้ → ตั้งกลับเป็น 'casual'
alter table tenants add column if not exists bot_tone text default 'polite';
update tenants set bot_tone = 'casual' where id = '3da82a79-8ef5-4f8c-9df3-faed33e75b64';
