"""
建立後台登入帳號 (app_users) — 在跑完 multitenant_01_schema.sql 之後執行。

用法:
    python scripts/create_app_user.py <email> <password> [tenant_name]
不指定 tenant_name → 掛在第一個租戶 (Justin)。
讀取 .streamlit/secrets.toml 的 SUPABASE_URL / SUPABASE_KEY。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _creds():
    s = open(os.path.join(ROOT, ".streamlit", "secrets.toml"), encoding="utf-8").read()
    return (re.search(r'SUPABASE_URL\s*=\s*"([^"]+)"', s).group(1),
            re.search(r'SUPABASE_KEY\s*=\s*"([^"]+)"', s).group(1))


def main():
    if len(sys.argv) < 3:
        print("用法: python scripts/create_app_user.py <email> <password> [tenant_name]")
        sys.exit(1)
    email, pw = sys.argv[1], sys.argv[2]
    tenant_name = sys.argv[3] if len(sys.argv) > 3 else None

    from supabase import create_client
    from utils.auth import create_user, first_tenant_id
    url, key = _creds()
    sb = create_client(url, key)

    if tenant_name:
        rows = sb.table("tenants").select("id").eq("name", tenant_name).execute().data or []
        tid = rows[0]["id"] if rows else sb.table("tenants").insert({"name": tenant_name}).execute().data[0]["id"]
    else:
        tid = first_tenant_id(sb)
    if not tid:
        print("找不到租戶，請先執行 multitenant_01_schema.sql")
        sys.exit(1)

    # 防呆: email 已存在就不重建
    exists = sb.table("app_users").select("id").eq("email", email.strip().lower()).execute().data or []
    if exists:
        print(f"帳號已存在: {email}")
        sys.exit(0)

    u = create_user(sb, email, pw, tid)
    print(f"✓ 已建立帳號: {u['email']}  (tenant_id={u['tenant_id']})")


if __name__ == "__main__":
    main()
