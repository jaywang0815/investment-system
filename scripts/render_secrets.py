"""
Render 啟動前置：把環境變數 STREAMLIT_SECRETS_TOML 的內容寫成 .streamlit/secrets.toml
(在 Render 不提交 secrets 檔，改由環境變數提供整份 toml — 支援 [auth]/list/JSON 等複雜結構)
"""
import os
import pathlib

content = os.environ.get("STREAMLIT_SECRETS_TOML", "")
out = pathlib.Path(".streamlit")
out.mkdir(exist_ok=True)
(out / "secrets.toml").write_text(content, encoding="utf-8")
print(f"[render_secrets] wrote .streamlit/secrets.toml ({len(content)} bytes)")
if not content:
    print("[render_secrets] WARNING: STREAMLIT_SECRETS_TOML is empty — set it in Render env vars")
