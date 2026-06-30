-- ลบ 中信部位 (ctbc_position) ออกจากระบบ — ไม่ใช้แล้ว
-- เหตุผล: ตัวเลขนี้ทำให้นักลงทุนสับสน (ไม่ตรงยอดลงทุนจริง) เสี่ยง advisor ถูกถามจนเกิดเรื่อง
-- ลบออกจากรายงาน/import/แสดงผลในโค้ดแล้ว (new platform) ; old Streamlit เลิกใช้แล้ว
-- ⚠️ DESTRUCTIVE: ลบข้อมูล 19 ลูกค้าที่มีค่า (ของ DOUU) ถาวร
-- backup ก่อนรัน: backups/20260630_225457/  (รัน scripts/backup_db.py)

alter table customers drop column if exists ctbc_position;
