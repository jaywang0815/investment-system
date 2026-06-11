#!/bin/bash
cd "$(dirname "$0")"
echo "════════════════════════════════════════"
echo "  API กำลังทำงาน — อย่าปิดหน้าต่างนี้"
echo "  (http://localhost:8000)"
echo "════════════════════════════════════════"
python3 scripts/run_api.py
