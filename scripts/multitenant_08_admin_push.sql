-- ============================================================
-- multitenant_08_admin_push.sql
-- 目的：ให้เลือกได้ว่า admin คนไหน "รับ LINE push" (日報/เตือนปฏิทิน)。
-- ค่าเริ่มต้น = รับ (true); ตั้ง false เพื่อหยุดรับ → ลดจำนวนข้อความ (ประหยัดโควต้า LINE)。
-- 執行方式：Supabase → SQL Editor → 貼上 → Run。รันซ้ำได้ปลอดภัย (idempotent)。
-- ============================================================

alter table admins add column if not exists receive_push boolean default true;

-- JAY ไม่รับ push (ส่งเข้า DOUU คนเดียว) — แก้ชื่อตรงนี้ได้ตามต้องการ
update admins set receive_push = false where name = 'JAY';

select name, receive_push from admins order by name;
