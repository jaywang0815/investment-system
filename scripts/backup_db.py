"""DIY backup (free tier safety net) — ดึงทุกตารางผ่าน Supabase REST เก็บเป็น JSON ลง backups/<timestamp>/
ใช้: python3 scripts/backup_db.py   (กดก่อนจะแก้อะไรเสี่ยงๆ ทุกครั้ง)
กู้คืน: ดู restore_db.py (โพสต์กลับเข้า table) — แต่ทางที่ดีคืออัป Supabase Pro ให้มี backup อัตโนมัติ
อ่าน SUPABASE_URL/KEY จาก env หรือ .streamlit/secrets.toml
"""
import os
import re
import json
import sys
from datetime import datetime, timezone, timedelta

import requests

# ตารางที่ต้อง backup (ครอบคลุมข้อมูลลูกค้า + ตั้งค่าระบบทั้งหมด)
TABLES = [
    "tenants", "app_users", "invites",
    "customers", "structured_notes", "investments",
    "admins", "calendar_events", "alerts", "articles",
]
PAGE = 1000  # REST ดึงทีละ 1000 แถว


def _creds():
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if url and key:
        return url.rstrip("/"), key
    # fallback: อ่านจาก secrets.toml
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".streamlit", "secrets.toml")
    txt = open(p, encoding="utf-8").read()

    def g(k):
        m = re.search(rf'^{k}\s*=\s*"([^"]+)"', txt, re.M) or re.search(rf'^{k}\s*=\s*([^\s#]+)', txt, re.M)
        return m.group(1) if m else ""
    return g("SUPABASE_URL").rstrip("/"), g("SUPABASE_KEY")


def dump_table(url, headers, table):
    rows, offset = [], 0
    while True:
        r = requests.get(f"{url}/rest/v1/{table}", headers=headers,
                         params={"select": "*", "limit": PAGE, "offset": offset}, timeout=30)
        if r.status_code != 200:
            return None, r.status_code  # ตารางไม่มี/error → ข้าม
        batch = r.json()
        rows.extend(batch)
        if len(batch) < PAGE:
            break
        offset += PAGE
    return rows, 200


def main():
    url, key = _creds()
    if not url or not key:
        print("❌ ไม่พบ SUPABASE_URL/KEY"); sys.exit(1)
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    ts = datetime.now(timezone(timedelta(hours=7))).strftime("%Y%m%d_%H%M%S")
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups", ts)
    os.makedirs(base, exist_ok=True)

    total = 0
    summary = {}
    for t in TABLES:
        rows, status = dump_table(url, headers, t)
        if rows is None:
            print(f"  ⚠️  {t:18} skip (status {status})")
            continue
        with open(os.path.join(base, f"{t}.json"), "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        summary[t] = len(rows)
        total += len(rows)
        print(f"  ✅ {t:18} {len(rows)} rows")

    with open(os.path.join(base, "_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"timestamp": ts, "tables": summary, "total_rows": total}, f, ensure_ascii=False, indent=2)
    print(f"\n💾 backup เสร็จ: backups/{ts}/  ({total} rows รวม {len(summary)} ตาราง)")


if __name__ == "__main__":
    main()
