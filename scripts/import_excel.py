"""
匯入 Excel 資料到 Supabase (Command-Line 版)
使用方法: python3 scripts/import_excel.py [檔案路徑]

現在使用 utils/excel_parser.py 的共用解析器
"""
import sys
import os

# เพิ่ม project root ใน Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.excel_parser import parse_excel_file, get_summary

# ── 設定 ──────────────────────────────────────────────────────
DEFAULT_EXCEL = "/Users/jay/Desktop/開戶明細 金額.xlsx"

print("=" * 55)
print("  投資管理系統 - Excel 資料匯入工具")
print("=" * 55)

# 選擇檔案
if len(sys.argv) > 1:
    excel_path = sys.argv[1]
else:
    default_shown = f" [{DEFAULT_EXCEL}]" if os.path.exists(DEFAULT_EXCEL) else ""
    excel_path = input(f"\n請輸入 Excel 檔案路徑{default_shown}: ").strip()
    if not excel_path and os.path.exists(DEFAULT_EXCEL):
        excel_path = DEFAULT_EXCEL

if not os.path.exists(excel_path):
    print(f"❌ 找不到檔案: {excel_path}")
    sys.exit(1)

# Supabase 設定
print("\n--- Supabase 連線設定 ---")
supabase_url = input("Supabase URL: ").strip()
supabase_key = input("Supabase Service Key: ").strip()

if not supabase_url or not supabase_key:
    print("❌ 請填寫 Supabase 設定")
    sys.exit(1)

from supabase import create_client
sb = create_client(supabase_url, supabase_key)

# ── 解析 Excel ─────────────────────────────────────────────────
print(f"\n📂 解析檔案: {os.path.basename(excel_path)}")
parsed = parse_excel_file(excel_path)
summary = get_summary(parsed)

print(f"\n📊 解析結果:")
print(f"   客戶資料: {summary['customers']} 筆")
print(f"   偵測月份: {', '.join(sorted(summary['months'])) if summary['months'] else '無'}")
print(f"   SN 商品:  {summary['total_sns']} 筆")
print(f"   投資記錄: {summary['total_investments']} 筆")

# 顯示月份明細
for month, sns in sorted(parsed["sn_by_month"].items()):
    print(f"   → {month}: {len(sns)} 筆 SN")
    for sn in sns:
        tickers = " / ".join([sn.get(f"underlying_{i}", "") for i in range(1, 4)
                               if sn.get(f"underlying_{i}")])
        print(f"      {sn['product_code']} ({tickers}): {len(sn['investments'])} 個客戶")

confirm = input("\n確認匯入? (y/N): ").strip().lower()
if confirm != 'y':
    print("已取消")
    sys.exit(0)

# ── 匯入客戶 ──────────────────────────────────────────────────
print("\n👥 匯入客戶資料...")
customer_name_to_id = {}

# 先載入現有客戶
try:
    resp = sb.table("customers").select("id,name").execute()
    for c in (resp.data or []):
        customer_name_to_id[c["name"]] = c["id"]
    print(f"   已有 {len(customer_name_to_id)} 位客戶在資料庫")
except Exception as e:
    print(f"⚠️ 無法載入現有客戶: {e}")

customers_added = 0
for cust in parsed["customers"]:
    name = cust["name"]
    if name in customer_name_to_id:
        print(f"   跳過 (重複): {name}")
        continue
    try:
        resp = sb.table("customers").insert(cust).execute()
        if resp.data:
            customer_name_to_id[name] = resp.data[0]["id"]
            customers_added += 1
            print(f"   ✅ {name}")
    except Exception as e:
        print(f"   ❌ {name}: {e}")

print(f"   → 新增 {customers_added} 位客戶")

# ── 匯入 SN 商品 ───────────────────────────────────────────────
print("\n📊 匯入 SN 商品...")
sns_added = 0
investments_added = 0

for month, sns in sorted(parsed["sn_by_month"].items()):
    print(f"\n   [{month}]")
    for sn in sns:
        investments = sn.pop("investments", [])
        code = sn["product_code"]

        # 檢查重複
        sn_id = None
        try:
            resp = sb.table("structured_notes").select("id").eq("product_code", code).execute()
            if resp.data:
                sn_id = resp.data[0]["id"]
                print(f"   跳過 (重複): {code}")
        except Exception:
            pass

        if sn_id is None:
            try:
                resp = sb.table("structured_notes").insert(sn).execute()
                if resp.data:
                    sn_id = resp.data[0]["id"]
                    sns_added += 1
                    tickers = " / ".join([sn.get(f"underlying_{i}", "") for i in range(1, 4)
                                           if sn.get(f"underlying_{i}")])
                    print(f"   ✅ {code} ({tickers})")
            except Exception as e:
                print(f"   ❌ {code}: {e}")
                continue

        # 投資記錄
        if sn_id:
            for inv in investments:
                cname = inv["customer_name"]
                amount = inv["amount_usd"]

                # 找客戶 ID
                customer_id = customer_name_to_id.get(cname)
                if not customer_id:
                    name_clean = cname.replace("*", "").replace("＊", "")
                    for k, v in customer_name_to_id.items():
                        k_clean = k.replace("*", "").replace("＊", "")
                        if name_clean in k_clean or k_clean in name_clean:
                            customer_id = v
                            break

                if not customer_id:
                    # 自動建立
                    try:
                        resp = sb.table("customers").insert({"name": cname}).execute()
                        if resp.data:
                            customer_id = resp.data[0]["id"]
                            customer_name_to_id[cname] = customer_id
                    except Exception:
                        pass

                if customer_id:
                    try:
                        sb.table("investments").insert({
                            "customer_id": customer_id,
                            "sn_id": sn_id,
                            "amount_usd": amount
                        }).execute()
                        investments_added += 1
                        print(f"      💰 {cname}: USD {amount:,.0f}")
                    except Exception as e:
                        if "duplicate" not in str(e).lower():
                            print(f"      ⚠️ {cname}: {e}")
                else:
                    print(f"      ❓ 找不到客戶: {cname}")

# ── 結果 ──────────────────────────────────────────────────────
print(f"\n{'='*55}")
print(f"✅ 匯入完成!")
print(f"   新增客戶:    {customers_added} 人")
print(f"   新增 SN:     {sns_added} 筆")
print(f"   新增投資:    {investments_added} 筆")
print(f"{'='*55}")
print("\n現在可以啟動系統:")
print("  python3 -m streamlit run app.py")
