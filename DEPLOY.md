# Deploy คู่มือ — Justinvestment platform

ระบบมี 3 ส่วน:
```
Supabase (DB, cloud อยู่แล้ว)
   ├── API (FastAPI)      → Render        [repo: investment-system]
   └── Back-office (Next) → Vercel        [repo: justinvestment-backoffice]
```
> LINE bot เดิมบน Render = คนละ service ไม่ต้องแตะ

---

## 0) เตรียม (ครั้งเดียว)
- **rotate GitHub token เก่า** (ที่ฝังใน git remote) ที่ GitHub → Settings → Developer settings → Personal access tokens
- ค่าที่จะใช้ (เอาจาก `.streamlit/secrets.toml`): `SUPABASE_URL`, `SUPABASE_KEY`
- `JWT_SECRET` (สร้างใหม่): ใช้ค่าที่น้องให้ในแชต หรือรัน `openssl rand -hex 32`

---

## A) API → Render
1. Render → **New → Web Service** → เลือก repo `jaywang0815/investment-system`
2. ตั้งค่า:
   - **Name:** `justinvestment-api`
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements-api.txt`
   - **Start Command:** `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
3. **Environment** (Add Environment Variable):
   - `SUPABASE_URL` = (จาก secrets.toml)
   - `SUPABASE_KEY` = (จาก secrets.toml)
   - `JWT_SECRET` = (ค่าที่สร้างไว้ ≥ 32 ตัวอักษร)
   - `PYTHON_VERSION` = `3.11.9`  ← สำคัญ (ให้ numpy/pandas/matplotlib ลงได้)
   - `CORS_ORIGINS` = (เว้นไว้ก่อน = อนุญาตทุก origin; ทีหลังใส่ domain Vercel เพื่อจำกัด)
4. Create → รอ build เสร็จ → จด **URL** เช่น `https://justinvestment-api.onrender.com`
5. ทดสอบ: เปิด `https://<api-url>/health` ต้องได้ `{"ok": true}`

> หมายเหตุ: Render free tier "หลับ" เมื่อไม่มีคนใช้ → เปิดครั้งแรกอาจช้า ~30 วิ (อัปเกรดเป็น paid ถ้าต้องการให้ตื่นตลอด)

---

## B) Back-office → Vercel
**B1. push ขึ้น GitHub ก่อน** (repo ยังไม่มี remote)
1. สร้าง repo ใหม่ที่ github.com (เช่น `justinvestment-backoffice`, private)
2. ในเครื่อง:
   ```
   cd /Users/jay/Desktop/justinvestment-backoffice
   git remote add origin https://github.com/jaywang0815/justinvestment-backoffice.git
   git push -u origin main
   ```

**B2. Vercel**
1. Vercel → **Add New → Project** → import repo `justinvestment-backoffice`
2. Framework = Next.js (ตรวจจับอัตโนมัติ) — ไม่ต้องตั้ง build อะไรเพิ่ม
3. **Environment Variables:**
   - `NEXT_PUBLIC_API_URL` = URL ของ Render API (ข้อ A4) เช่น `https://justinvestment-api.onrender.com`
4. Deploy → จด **domain** เช่น `https://justinvestment-backoffice.vercel.app`

---

## C) เชื่อม + ทดสอบ
1. เปิด domain Vercel → login ด้วย email/รหัสของพี่ → ต้องเห็นข้อมูลเหมือน localhost
2. (แนะนำ) กลับไป Render ใส่ `CORS_ORIGINS` = domain Vercel เพื่อจำกัดให้เฉพาะเว็บเราเรียก API
3. **ทดสอบลิงก์เชิญจากมือถือ:** หน้า 會員 → 邀請使用者 → ลิงก์จะเป็น domain Vercel อัตโนมัติ → เปิดในมือถือได้เลย
4. **ติดตั้ง PWA บน iPhone:** Safari เปิด domain → แชร์ → 加入主畫面

---

## หมายเหตุ
- **redeploy:** push ขึ้น GitHub → Render/Vercel deploy อัตโนมัติ
- **custom domain** (เช่น app.justinvestment.co): ตั้งใน Vercel → Domains (ทีหลังได้)
- **ความลับ:** secrets อยู่ใน env ของ Render/Vercel เท่านั้น ไม่ commit ลง repo
