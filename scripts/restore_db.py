"""กู้คืนจาก backup (ดู backup_db.py) — upsert กลับเข้า table ตามลำดับ FK
ใช้: python3 scripts/restore_db.py backups/<timestamp>
⚠️ upsert ตาม id (PK) — แถวที่มีอยู่จะถูกเขียนทับด้วยค่าจาก backup; แถวที่ถูกลบไปหลัง backup จะ "ไม่" ถูกลบกลับ
อ่าน SUPABASE_URL/KEY จาก env หรือ .streamlit/secrets.toml
"""
import os
import re
import sys
import json

import requests

# ลำดับ FK: พ่อก่อนลูก (tenants → อ้าง tenant → investments อ้าง customer+sn)
ORDER = [
    "tenants", "app_users", "invites",
    "customers", "structured_notes", "investments",
    "admins", "calendar_events", "alerts", "articles",
]


def _creds():
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if url and key:
        return url.rstrip("/"), key
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".streamlit", "secrets.toml")
    txt = open(p, encoding="utf-8").read()

    def g(k):
        m = re.search(rf'^{k}\s*=\s*"([^"]+)"', txt, re.M) or re.search(rf'^{k}\s*=\s*([^\s#]+)', txt, re.M)
        return m.group(1) if m else ""
    return g("SUPABASE_URL").rstrip("/"), g("SUPABASE_KEY")


def main():
    if len(sys.argv) < 2:
        print("ใช้: python3 scripts/restore_db.py backups/<timestamp>"); sys.exit(1)
    folder = sys.argv[1]
    if not os.path.isdir(folder):
        print(f"❌ ไม่พบโฟลเดอร์ {folder}"); sys.exit(1)

    url, key = _creds()
    headers = {"apikey": key, "Authorization": f"Bearer {key}",
               "Content-Type": "application/json",
               "Prefer": "resolution=merge-duplicates,return=minimal"}

    print(f"⚠️  กำลังจะ upsert จาก {folder} กลับเข้า DB จริง")
    if input("พิมพ์ 'yes' เพื่อยืนยัน: ").strip().lower() != "yes":
        print("ยกเลิก"); return

    for t in ORDER:
        path = os.path.join(folder, f"{t}.json")
        if not os.path.exists(path):
            continue
        rows = json.load(open(path, encoding="utf-8"))
        if not rows:
            print(f"  – {t:18} (ว่าง ข้าม)"); continue
        r = requests.post(f"{url}/rest/v1/{t}", headers=headers, json=rows, timeout=60)
        ok = "✅" if r.ok else f"❌ {r.status_code} {r.text[:120]}"
        print(f"  {ok} {t:18} {len(rows)} rows")
    print("\nเสร็จ — ตรวจสอบข้อมูลในระบบอีกครั้ง")


if __name__ == "__main__":
    main()
