"""
全站主題 — premium minimal (Apple / Nike inspired)
乾淨、留白、細線、強烈字級層次；綠色僅作為重點色 (accent)。
Light / Dark 由 st.session_state['ui_mode'] 控制，dog_header() 在每頁注入。
"""
import streamlit as st

# 統一證券 名片配色 — 紅 / 白 / 金 / 黑 (與公開網站、匯出檔一致)
LIGHT = {
    "bg": "#ffffff", "bg2": "#faf6f3",
    "surface": "#ffffff", "surface2": "#faf6f4",
    "text": "#1a1413", "muted": "#6f635f",
    "accent": "#d11a22", "accent_press": "#a8141b",
    "border": "#ece3e0", "on_accent": "#ffffff",
    "sidebar": "#ffffff", "sidebar_text": "#1a1413",
    "glass": "rgba(255,255,255,0.55)", "glass_brd": "rgba(255,255,255,0.65)",
    "glow": "rgba(120,30,40,0.10)", "gold": "#b9822f",
    "blob": ("radial-gradient(38% 32% at 8% 6%, rgba(209,26,34,0.13), transparent 70%),"
             "radial-gradient(34% 30% at 92% 8%, rgba(185,130,47,0.13), transparent 70%),"
             "radial-gradient(46% 40% at 80% 94%, rgba(209,26,34,0.10), transparent 72%)"),
}
DARK = {
    "bg": "#0e0b0b", "bg2": "#151010",
    "surface": "#1a1414", "surface2": "#201818",
    "text": "#f4efed", "muted": "#a89a96",
    "accent": "#f04a4f", "accent_press": "#d23a40",
    "border": "#2a2120", "on_accent": "#1a0c0c",
    "sidebar": "#140f0f", "sidebar_text": "#f4efed",
    "glass": "rgba(34,24,26,0.45)", "glass_brd": "rgba(255,255,255,0.10)",
    "glow": "rgba(0,0,0,0.45)", "gold": "#e2a85c",
    "blob": ("radial-gradient(40% 34% at 8% 6%, rgba(240,74,79,0.14), transparent 70%),"
             "radial-gradient(36% 32% at 92% 8%, rgba(226,168,92,0.13), transparent 70%),"
             "radial-gradient(48% 42% at 80% 94%, rgba(240,74,79,0.11), transparent 72%)"),
}


def current_mode() -> str:
    return st.session_state.get("ui_mode", "light")


def theme_toggle():
    mode = current_mode()
    with st.sidebar:
        choice = st.radio(
            "Appearance",
            ["Light", "Dark"],
            index=0 if mode == "light" else 1,
            horizontal=True,
            key="ui_mode_radio",
            label_visibility="collapsed",
        )
    new_mode = choice.lower()
    if new_mode != mode:
        st.session_state["ui_mode"] = new_mode
        st.rerun()
    st.session_state["ui_mode"] = new_mode


def apply_theme():
    c = DARK if current_mode() == "dark" else LIGHT
    st.markdown(f"""
<style>
:root {{
  --bg:{c['bg']}; --bg2:{c['bg2']}; --surface:{c['surface']}; --surface2:{c['surface2']};
  --text:{c['text']}; --muted:{c['muted']}; --accent:{c['accent']}; --accent-press:{c['accent_press']};
  --border:{c['border']}; --on-accent:{c['on_accent']};
  --gold:{c['gold']};
  --glass:{c['glass']}; --glass-brd:{c['glass_brd']}; --glow:{c['glow']};
}}

/* ── base / typography ── */
.stApp {{ background: linear-gradient(160deg, var(--bg) 0%, var(--bg2) 100%); color: var(--text); }}
[data-testid="stAppViewContainer"]::before {{
  content:""; position:fixed; inset:0; z-index:0; pointer-events:none;
  background: {c['blob']};
}}
[data-testid="stAppViewContainer"] > .main {{ position:relative; z-index:1; }}
.block-container {{ padding-top: 2.6rem; padding-bottom: 4rem; max-width: 1180px; }}
html, body, [class*="css"] {{
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Inter",
               "Noto Sans TC", "Segoe UI", sans-serif;
  -webkit-font-smoothing: antialiased;
}}
h1 {{ font-size: 2.4rem; font-weight: 800; letter-spacing: -.03em; color: var(--text); }}
h2 {{ font-size: 1.5rem; font-weight: 700; letter-spacing: -.02em; color: var(--text); }}
h3 {{ font-size: 1.1rem; font-weight: 700; letter-spacing: -.01em; color: var(--text); }}
p, span, label, li {{ color: var(--text); }}
small, [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {{ color: var(--muted) !important; }}
a {{ color: var(--accent); text-decoration: none; }}
hr {{ border: none; border-top: 1px solid var(--border); margin: 1.4rem 0; }}

/* ── sidebar (minimal) ── */
section[data-testid="stSidebar"] > div {{
  background: {c['sidebar']}; border-right: 1px solid var(--border);
}}
section[data-testid="stSidebar"] * {{ color: {c['sidebar_text']} !important; }}
[data-testid="stSidebarNavLink"] {{
  border-radius: 10px; margin: 2px 6px; padding: 8px 12px;
  font-weight: 500; transition: background .15s ease;
}}
[data-testid="stSidebarNavLink"]:hover {{ background: var(--surface2); }}
[data-testid="stSidebarNavLink"][aria-current="page"],
[data-testid="stSidebarNavLink"][aria-selected="true"] {{
  background: var(--surface2);
  box-shadow: inset 3px 0 0 var(--accent);
}}

/* ── buttons ── */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
  border-radius: 999px; font-weight: 600; padding: .55rem 1.4rem;
  background: var(--surface); color: var(--text);
  border: 1px solid var(--border); box-shadow: none;
  transition: border-color .15s ease, background .15s ease, transform .12s ease;
}}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {{
  border-color: var(--text); transform: translateY(-1px);
}}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
  background: var(--accent); color: var(--on-accent); border: 1px solid var(--accent);
}}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{
  background: var(--accent-press); border-color: var(--accent-press);
}}

/* ── inputs ── */
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input, .stTextArea textarea {{
  border-radius: 12px !important; background: var(--surface) !important;
  color: var(--text) !important; border: 1px solid var(--border) !important;
}}
[data-testid="stTextInput"] input:focus, [data-testid="stNumberInput"] input:focus {{
  border-color: var(--accent) !important; box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 18%, transparent) !important;
}}
div[data-baseweb="select"] > div {{
  border-radius: 12px !important; background: var(--surface) !important;
  border: 1px solid var(--border) !important;
}}
div[data-baseweb="select"] * {{ color: var(--text) !important; }}

/* ── tabs (clean underline) ── */
.stTabs [data-baseweb="tab-list"] {{ gap: 26px; border-bottom: 1px solid var(--border); }}
.stTabs [data-baseweb="tab"] {{
  background: transparent; padding: 8px 2px; color: var(--muted); font-weight: 600;
}}
.stTabs [aria-selected="true"] {{ color: var(--text) !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background: var(--accent) !important; height: 2px; }}
.stTabs [data-baseweb="tab-border"] {{ background: transparent !important; }}

/* ── metrics (clean cards) ── */
[data-testid="stMetric"] {{
  background: var(--glass);
  -webkit-backdrop-filter: blur(16px) saturate(155%);
  backdrop-filter: blur(16px) saturate(155%);
  border: 1px solid var(--glass-brd);
  border-radius: 20px; padding: 18px 20px;
  box-shadow: 0 10px 30px var(--glow), inset 0 1px 0 rgba(255,255,255,0.55);
}}
[data-testid="stMetricValue"] {{ color: var(--text); font-weight: 800; letter-spacing: -.02em;
  overflow: visible !important; font-size: clamp(1.1rem, 1.6vw, 1.7rem); }}
[data-testid="stMetricValue"] > div {{ overflow: visible !important; text-overflow: clip !important; white-space: nowrap; }}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {{
  color: var(--muted) !important; text-transform: uppercase;
  font-size: .72rem !important; letter-spacing: .08em;
}}

/* ── containers ── */
[data-testid="stExpander"] {{
  border: 1px solid var(--glass-brd); border-radius: 18px; overflow: hidden;
  background: var(--glass);
  -webkit-backdrop-filter: blur(16px) saturate(150%);
  backdrop-filter: blur(16px) saturate(150%);
  box-shadow: 0 8px 26px var(--glow);
}}
[data-testid="stExpander"] summary {{ color: var(--text); font-weight: 600; }}
[data-testid="stDataFrame"], [data-testid="stTable"] {{
  border-radius: 18px; overflow: hidden; border: 1px solid var(--glass-brd);
  box-shadow: 0 8px 26px var(--glow);
}}
[data-testid="stAlert"] {{
  border-radius: 16px; border: 1px solid var(--glass-brd); background: var(--glass);
  -webkit-backdrop-filter: blur(12px) saturate(150%); backdrop-filter: blur(12px) saturate(150%);
}}
.stProgress > div > div > div {{ background: var(--accent); }}
[data-testid="stSlider"] [role="slider"] {{ background: var(--accent); }}
[data-testid="stDecoration"] {{ display: none; }}

/* ── flair: motion & micro-interactions ── */
@keyframes flairRise {{ from {{ opacity:0; transform: translateY(16px); }} to {{ opacity:1; transform: none; }} }}
[data-testid="stMetric"] {{ animation: flairRise .55s cubic-bezier(.22,1,.36,1) both; transition: transform .2s ease, box-shadow .2s ease; }}
[data-testid="column"]:nth-child(2) [data-testid="stMetric"] {{ animation-delay: .07s; }}
[data-testid="column"]:nth-child(3) [data-testid="stMetric"] {{ animation-delay: .14s; }}
[data-testid="column"]:nth-child(4) [data-testid="stMetric"] {{ animation-delay: .21s; }}
[data-testid="stMetric"]:hover {{ transform: translateY(-4px); box-shadow: 0 14px 32px color-mix(in srgb, var(--accent) 16%, transparent); }}
.stButton > button:active, .stFormSubmitButton > button:active {{ transform: scale(.97); }}
[data-testid="stExpander"], [data-testid="stAlert"] {{ animation: flairRise .5s cubic-bezier(.22,1,.36,1) both; }}
.dh-wrap {{ animation: flairRise .5s cubic-bezier(.22,1,.36,1) both; }}

/* ── header card (used by dog_header) ── */
.dh-wrap {{ margin: 0 0 2.2rem; }}
.dh-eyebrow {{
  font-size: .72rem; font-weight: 700; letter-spacing: .22em;
  text-transform: uppercase; color: var(--gold); margin-bottom: .35rem;
}}
.dh-title {{ font-size: 2.3rem; font-weight: 800; letter-spacing: -.03em; color: var(--text); line-height: 1.05; }}
.dh-rule {{ height: 3px; width: 48px; border-radius: 999px; background: var(--gold); margin-top: 1.1rem; }}
</style>
""", unsafe_allow_html=True)
