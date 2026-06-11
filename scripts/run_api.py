"""
本地啟動 Platform API (開發用) — 自動讀 .streamlit/secrets.toml 設好環境變數。
用法 (在 repo 根目錄):  python scripts/run_api.py
然後開 http://localhost:8000/docs 看 API。
"""
import os
import re
import sys
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    s = open(os.path.join(ROOT, ".streamlit", "secrets.toml"), encoding="utf-8").read()
    os.environ["SUPABASE_URL"] = re.search(r'SUPABASE_URL\s*=\s*"([^"]+)"', s).group(1)
    os.environ["SUPABASE_KEY"] = re.search(r'SUPABASE_KEY\s*=\s*"([^"]+)"', s).group(1)
    os.environ.setdefault("JWT_SECRET", "dev-secret-change-me")
    # 用同一個 python 跑 uvicorn 模組，避免 'uvicorn' CLI 不在 PATH 的問題
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--reload", "--port", "8000"],
        cwd=ROOT,
    )


if __name__ == "__main__":
    main()
