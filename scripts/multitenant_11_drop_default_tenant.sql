-- ลบ DEFAULT tenant_id (= ของ DOUU) ออกจากทุกตาราง
-- เหตุผล: กันข้อมูลของ tenant ใหม่ตกไปอยู่บัญชี DOUU โดยไม่ตั้งใจ ถ้ามี insert ที่ไม่ระบุ tenant_id
-- ปลอดภัย: FastAPI (Repo.create) + LINE bot (sb_post) ใส่ tenant_id ให้เสมอแล้ว
alter table customers        alter column tenant_id drop default;
alter table structured_notes alter column tenant_id drop default;
alter table investments      alter column tenant_id drop default;
alter table admins           alter column tenant_id drop default;
alter table calendar_events  alter column tenant_id drop default;
-- (ถ้าตารางไหนไม่มี default อยู่แล้ว PostgreSQL จะไม่ error)
