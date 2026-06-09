"""
全站主題 — premium minimal (Apple / Nike inspired)
乾淨、留白、細線、強烈字級層次；綠色僅作為重點色 (accent)。
Light / Dark 由 st.session_state['ui_mode'] 控制，dog_header() 在每頁注入。
"""
import streamlit as st

LIGHT = {
    "bg": "#ffffff", "bg2": "#fafafa",
    "surface": "#ffffff", "surface2": "#f6f7f6",
    "text": "#0b0f0d", "muted": "#6b7280",
    "accent": "#15a34a", "accent_press": "#0f7d3b",
    "border": "#ececec", "on_accent": "#ffffff",
    "sidebar": "#ffffff", "sidebar_text": "#0b0f0d",
}
DARK = {
    "bg": "#0a0c0b", "bg2": "#0d100e",
    "surface": "#121413", "surface2": "#171a18",
    "text": "#f4f6f5", "muted": "#9aa39e",
    "accent": "#2fd47e", "accent_press": "#27b86c",
    "border": "#1f2220", "on_accent": "#05140d",
    "sidebar": "#0c0e0d", "sidebar_text": "#f4f6f5",
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
}}

/* ── base / typography ── */
.stApp {{ background: var(--bg); color: var(--text); }}
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
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 18px; padding: 18px 20px;
}}
[data-testid="stMetricValue"] {{ color: var(--text); font-weight: 800; letter-spacing: -.02em; }}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {{
  color: var(--muted) !important; text-transform: uppercase;
  font-size: .72rem !important; letter-spacing: .08em;
}}

/* ── containers ── */
[data-testid="stExpander"] {{
  border: 1px solid var(--border); border-radius: 16px; overflow: hidden; background: var(--surface);
}}
[data-testid="stExpander"] summary {{ color: var(--text); font-weight: 600; }}
[data-testid="stDataFrame"], [data-testid="stTable"] {{
  border-radius: 16px; overflow: hidden; border: 1px solid var(--border);
}}
[data-testid="stAlert"] {{ border-radius: 14px; border: 1px solid var(--border); }}
.stProgress > div > div > div {{ background: var(--accent); }}
[data-testid="stSlider"] [role="slider"] {{ background: var(--accent); }}
[data-testid="stDecoration"] {{ display: none; }}

/* ── header card (used by dog_header) ── */
.dh-wrap {{ margin: 0 0 2.2rem; }}
.dh-eyebrow {{
  font-size: .72rem; font-weight: 700; letter-spacing: .22em;
  text-transform: uppercase; color: var(--accent); margin-bottom: .35rem;
}}
.dh-title {{ font-size: 2.3rem; font-weight: 800; letter-spacing: -.03em; color: var(--text); line-height: 1.05; }}
.dh-rule {{ height: 1px; background: var(--border); margin-top: 1.1rem; }}
</style>
""", unsafe_allow_html=True)
