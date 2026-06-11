#!/bin/bash
cd "$(dirname "$0")"
echo "════════════════════════════════════════"
echo "  สร้างบัญชี login สำหรับ back-office ใหม่"
echo "════════════════════════════════════════"
echo ""
read -p "พิมพ์ Email แล้วกด Enter: " EMAIL
read -p "พิมพ์ Password แล้วกด Enter: " PW
echo ""
python3 scripts/create_app_user.py "$EMAIL" "$PW"
echo ""
echo "เสร็จแล้ว — จดอีเมล/รหัสไว้สำหรับ login นะครับ"
read -p "กด Enter เพื่อปิดหน้านี้..." x
