"""
用 Claude 把中文文章翻成英文 + 潤稿 + 產生摘要/slug
需要 ANTHROPIC_API_KEY (st.secrets 或環境變數，可從 LINE bot 沿用)
"""
import os
import json


def _get_key() -> str:
    try:
        import streamlit as st
        k = st.secrets.get("ANTHROPIC_API_KEY", "")
        if k:
            return k
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY", "")


def translate_article(title_zh: str, excerpt_zh: str, body_zh: str) -> dict:
    """
    回傳 dict: {title_en, excerpt_en, body_en, excerpt_zh, slug}
    (body 保留 Markdown 格式)
    """
    key = _get_key()
    if not key:
        raise RuntimeError("尚未設定 ANTHROPIC_API_KEY")

    import anthropic
    client = anthropic.Anthropic(api_key=key)

    prompt = f"""You localize a Traditional-Chinese investment/wealth-management article for a bilingual website.
Return ONLY a JSON object (no code fences) with these keys:
- "title_en": natural, professional English title
- "excerpt_en": 1-2 sentence English summary
- "excerpt_zh": 1-2 句繁體中文摘要 (若原文已提供摘要則沿用並潤飾)
- "body_en": full English translation, KEEP the original Markdown structure/formatting
- "slug": short lowercase hyphenated english slug derived from the title

Tone: clear, trustworthy, professional — not hypey.

[Title 標題]
{title_zh}

[Excerpt 摘要]
{excerpt_zh or "(none)"}

[Body 內文 (Markdown)]
{body_zh}
"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = (msg.content[0].text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]
    return json.loads(text)
