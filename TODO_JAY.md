# 📋 สิ่งที่พี่ต้องทำเอง (น้องทำให้ไม่ได้ ต้องรอพี่)

อัปเดตล่าสุด: รอบกลางคืน (น้องรันงานต่อระหว่างพี่นอน)

## 🔴 ต้องทำ (ปลดล็อกฟีเจอร์)
1. **รัน SQL ปฏิทิน** — Supabase → SQL Editor → วางไฟล์ `scripts/multitenant_07_calendar.sql` → Run
   - (น้องอัปเกรดให้รองรับ "เวลา + ตั้งเตือนล่วงหน้า" แล้ว — ไฟล์เดียวกัน รันซ้ำได้ปลอดภัย idempotent)
2. **ตั้ง cron เตือนปฏิทิน** — cron-job.org → เพิ่ม job ใหม่
   - URL: `https://<line-bot-url>.onrender.com/trigger-calendar-reminder?secret=<REPORT_SECRET เดิม>`
   - ความถี่: **ทุก 15 นาที** (เพื่อให้เตือนตามเวลาที่ตั้งได้แม่น ±15 นาที)

## 🟡 ถ้าอยากได้เมล/ลืมรหัส (Resend) — optional
3. สมัคร https://resend.com (ฟรี) → เอา **API key**
4. ใส่ env บน Render (service API `justinvestment-api`): `RESEND_API_KEY=...`, `MAIL_FROM=onboarding@resend.dev` (หรือโดเมนตัวเองถ้ายืนยัน DNS)
   - พอใส่แล้ว: คำเชิญจะส่งเข้าเมลอัตโนมัติ + ปุ่ม "ลืมรหัส" ในหน้า login ใช้ได้
   - (น้องเขียนโค้ดเตรียมไว้ให้แล้ว ทำงานเองเมื่อเจอ key)

## 🟢 ความปลอดภัย
5. **เปลี่ยน GitHub token** ที่ฝังใน git remote (เก่ารั่ว) — สร้าง token ใหม่ที่ github.com/settings/tokens แล้ว:
   `git remote set-url origin https://<NEW_TOKEN>@github.com/jaywang0815/investment-system.git`
   (ทำทั้ง investment-system และ justinvestment-backoffice)

## 🔵 ตอนสะดวก
6. **เชิญเพื่อน** douu@livemail.tw → หน้า 會員 → 邀請使用者 → copy ลิงก์ส่ง LINE
7. **LINE myid** → พิมพ์ `myid` กับบอท → ได้ ID → เอาไปใส่ในหน้า **設定 → LINE 管理員** (น้องกำลังสร้างช่องให้)

---
*งานที่น้องทำเสร็จระหว่างคืน จะเขียนสรุปไว้ท้ายไฟล์นี้*

## ✅ น้องทำเสร็จแล้ว (รอบนี้)
- (กำลังอัปเดต...)
