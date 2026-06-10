"""
Supabase 資料備份 — 匯出所有資料表為一份帶時間戳的 JSON (read-only, 不改任何資料)。

用法:
    python scripts/backup_supabase.py
讀取 .streamlit/secrets.toml 的 SUPABASE_URL / SUPABASE_KEY (或同名環境變數)。
輸出: backups/backup_YYYYMMDD_HHMMSS.json  (已被 .gitignore 排除，內含客戶金額資料勿外流)
"""
import os
import re
import json
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 系統用到的所有資料表 (不存在的會自動略過)
TABLES = [
    "customers",
    "structured_notes",
    "investments",
    "admins",
    "months",
    "articles",
    "alerts",
    "app_settings",
    "daily_prices",
]


def _creds():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if url and key:
        return url, key
    path = os.path.join(ROOT, ".streamlit", "secrets.toml")
    s = open(path, encoding="utf-8").read()
    url = re.search(r'SUPABASE_URL\s*=\s*"([^"]+)"', s).group(1)
    key = re.search(r'SUPABASE_KEY\s*=\s*"([^"]+)"', s).group(1)
    return url, key


def _fetch_all(sb, table):
    """分頁抓全部 (PostgREST 單次上限 1000)。"""
    rows, start, page = [], 0, 1000
    while True:
        resp = sb.table(table).select("*").range(start, start + page - 1).execute()
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < page:
            break
        start += page
    return rows


def main():
    from supabase import create_client
    url, key = _creds()
    sb = create_client(url, key)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump = {"_backed_up_at": datetime.now().isoformat(), "_tables": {}}
    summary = []

    for t in TABLES:
        try:
            rows = _fetch_all(sb, t)
            dump["_tables"][t] = rows
            summary.append((t, len(rows)))
        except Exception as e:
            summary.append((t, f"skip ({str(e)[:40]})"))

    out_dir = os.path.join(ROOT, "backups")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"backup_{stamp}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(dump, f, ensure_ascii=False, indent=2, default=str)

    size_kb = os.path.getsize(out_path) // 1024
    print(f"\n✓ Backup saved: {out_path} ({size_kb} KB)")
    print("─" * 40)
    for t, n in summary:
        print(f"  {t:<20} {n}")
    print("─" * 40)


if __name__ == "__main__":
    main()
