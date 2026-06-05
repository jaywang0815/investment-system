#!/bin/bash
# ดับเบิลคลิกไฟล์นี้เพื่อเปิดระบบ
cd "$(dirname "$0")"

echo "🏦 กำลังเปิดระบบบริหารการลงทุน..."
echo ""

# ตรวจสอบว่ามี secrets.toml หรือยัง
if [ ! -f ".streamlit/secrets.toml" ]; then
    echo "⚠️  ยังไม่ได้ตั้งค่าระบบ"
    echo "   ระบบจะเปิดขึ้นมาและพาไปหน้าตั้งค่าอัตโนมัติ"
    echo ""
fi

echo "🌐 กำลังเปิด http://localhost:8501"
echo "   กด Ctrl+C เพื่อปิดระบบ"
echo ""

# เปิดเบราว์เซอร์หลังจาก 3 วินาที
sleep 3 && open http://localhost:8501 &

# เปิดแอป
/Users/jay/Library/Python/3.9/bin/streamlit run app.py \
    --server.port 8501 \
    --server.headless false \
    --browser.gatherUsageStats false
