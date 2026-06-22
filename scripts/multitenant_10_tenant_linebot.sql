-- Per-tenant LINE bot: เก็บ channel secret + access token ของแต่ละ tenant
-- แต่ละ advisor สร้าง LINE Messaging API channel ของตัวเอง แล้ววาง secret/token ผ่านหน้า 設定
-- บอตใช้ค่าเหล่านี้ validate signature + reply/push ของ tenant นั้น ๆ
alter table tenants add column if not exists line_channel_secret       text;
alter table tenants add column if not exists line_channel_access_token text;

-- (ไม่ตั้ง DEFAULT, ไม่ backfill — tenant ที่ยังไม่ตั้ง = ยังไม่เปิดบอต; DOUU ใช้ env เดิมต่อได้)
