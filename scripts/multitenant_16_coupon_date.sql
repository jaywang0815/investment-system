-- 配息日 (วันจ่ายดอกจริง) — auto = 比價日 T+3 (ข้ามเสาร์อาทิตย์ + 國定假日), advisor แก้ได้
-- ใช้ override anchor ของตารางจ่ายดอกในปฏิทิน (行事曆); ว่าง = คิดจาก 比價日 T+3 อัตโนมัติ
alter table structured_notes add column if not exists coupon_date date;
