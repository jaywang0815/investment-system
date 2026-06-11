#!/bin/bash
export PATH="/Users/jay/.nvm/versions/node/v24.16.0/bin:$PATH"
cd /Users/jay/Desktop/justinvestment-backoffice || { echo "ไม่พบโฟลเดอร์ justinvestment-backoffice"; read x; exit 1; }
echo "════════════════════════════════════════"
echo "  เว็บ back-office กำลังเปิด — อย่าปิดหน้านี้"
echo "  เปิดเบราว์เซอร์ไปที่ http://localhost:3000"
echo "════════════════════════════════════════"
npm run dev
