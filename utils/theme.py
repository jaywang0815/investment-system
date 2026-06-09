"""
全站主題 (Light / Dark) — 綠色系、現代、圓潤、乾淨
透過 dog_header() 在每頁注入；以 st.session_state['ui_mode'] 切換。
"""
import streamlit as st

# ── 調色盤 ────────────────────────────────────────────────────────
LIGHT = {
    "bg1": "#f2faf5", "bg2": "#e8f7ef",
    "surface": "#ffffff", "surface_soft": "#f4fbf7",
    "text": "#173029", "muted": "#5b7268",
    "primary": "#15a35a", "primary2": "#2bd47e", "accent": "#14b8a6",
    "border": "#dcefe4", "shadow": "rgba(20,80,55,.10)",
    "sidebar1": "#0f8a4d", "sidebar2": "#16a35a", "on_primary": "#ffffff",
}
DARK = {
    "bg1": "#0c1714", "bg2": "#0a1a14",
    "surface": "#13211c", "surface_soft": "#16271f",
    "text": "#e7f2ec", "muted": "#9fb6aa",
    "primary": "#34d399", "primary2": "#10b981", "accent": "#2dd4bf",
    "border": "#22352c", "shadow": "rgba(0,0,0,.40)",
    "sidebar1": "#0c1f18", "sidebar2": "#103027", "on_primary": "#06241a",
}


def current_mode() -> str:
    return st.session_state.get("ui_mode", "light")


def theme_toggle():
    """側邊欄 Light / Dark 切換"""
    mode = current_mode()
    with st.sidebar:
        choice = st.radio(
            "外觀",
            ["☀  Light", "☾  Dark"],
            index=0 if mode == "light" else 1,
            horizontal=True,
            key="ui_mode_radio",
            label_visibility="collapsed",
        )
    new_mode = "dark" if "Dark" in choice else "light"
    if new_mode != mode:
        st.session_state["ui_mode"] = new_mode
        st.rerun()
    st.session_state["ui_mode"] = new_mode


def apply_theme():
    """注入全站 CSS"""
    c = DARK if current_mode() == "dark" else LIGHT
    st.markdown(f"""
<style>
:root {{
  --bg1:{c['bg1']}; --bg2:{c['bg2']}; --surface:{c['surface']}; --surface-soft:{c['surface_soft']};
  --text:{c['text']}; --muted:{c['muted']}; --primary:{c['primary']}; --primary2:{c['primary2']};
  --accent:{c['accent']}; --border:{c['border']}; --shadow:{c['shadow']}; --on-primary:{c['on_primary']};
}}

/* ── base ── */
.stApp {{
  background: linear-gradient(160deg, var(--bg1) 0%, var(--bg2) 100%);
  color: var(--text);
}}
.block-container {{ padding-top: 2.2rem; max-width: 1280px; }}
html, body, [class*="css"] {{
  font-family: "Inter", "Noto Sans TC", -apple-system, "Segoe UI", sans-serif;
}}
h1, h2, h3, h4, h5, h6 {{ color: var(--text); letter-spacing:.2px; }}
p, span, label, li, div {{ color: var(--text); }}
small, .stCaption, [data-testid="stCaptionContainer"] {{ color: var(--muted) !important; }}
a {{ color: var(--primary); }}
hr {{ border-color: var(--border); }}

/* ── sidebar ── */
section[data-testid="stSidebar"] > div {{
  background: linear-gradient(180deg, {c['sidebar1']} 0%, {c['sidebar2']} 100%);
  border-right: 1px solid var(--border);
}}
section[data-testid="stSidebar"] * {{ color: #eafff4 !important; }}
section[data-testid="stSidebar"] a {{ border-radius: 12px; }}

/* ── buttons (rounded pill, green gradient) ── */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
  border-radius: 999px;
  border: 1px solid transparent;
  background: var(--surface);
  color: var(--text);
  font-weight: 600;
  padding: .5rem 1.3rem;
  box-shadow: 0 1px 3px var(--shadow);
  transition: all .18s ease;
}}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {{
  transform: translateY(-1px);
  box-shadow: 0 6px 16px var(--shadow);
  border-color: var(--primary);
}}
/* primary buttons */
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {{
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary2) 100%);
  color: var(--on-primary);
  border: none;
}}

/* ── inputs / selects ── */
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input, .stTextArea textarea {{
  border-radius: 12px !important;
  background: var(--surface) !important;
  color: var(--text) !important;
  border: 1px solid var(--border) !important;
}}
div[data-baseweb="select"] > div {{
  border-radius: 12px !important;
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
}}
div[data-baseweb="select"] * {{ color: var(--text) !important; }}

/* ── tabs (pill) ── */
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; border-bottom: none; }}
.stTabs [data-baseweb="tab"] {{
  border-radius: 999px; padding: 6px 16px; background: var(--surface-soft);
  color: var(--muted); border: 1px solid var(--border);
}}
.stTabs [aria-selected="true"] {{
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary2) 100%) !important;
  color: var(--on-primary) !important; border-color: transparent !important;
}}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ background: transparent !important; }}

/* ── metrics as cards ── */
[data-testid="stMetric"] {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 14px 18px;
  box-shadow: 0 2px 10px var(--shadow);
}}
[data-testid="stMetricValue"] {{ color: var(--primary); font-weight: 800; }}
[data-testid="stMetricLabel"] {{ color: var(--muted) !important; }}

/* ── expander / containers ── */
[data-testid="stExpander"] {{
  border: 1px solid var(--border); border-radius: 16px; overflow: hidden;
  background: var(--surface); box-shadow: 0 1px 6px var(--shadow);
}}
[data-testid="stExpander"] summary {{ color: var(--text); }}

/* ── dataframe ── */
[data-testid="stDataFrame"], [data-testid="stTable"] {{
  border-radius: 16px; overflow: hidden; border: 1px solid var(--border);
  box-shadow: 0 2px 10px var(--shadow);
}}

/* ── alerts rounded ── */
[data-testid="stAlert"] {{ border-radius: 14px; }}

/* progress bar */
.stProgress > div > div > div {{ background: linear-gradient(90deg, var(--primary), var(--primary2)); }}

/* slider */
[data-testid="stSlider"] [role="slider"] {{ background: var(--primary); }}

/* hide default top deco bar for cleaner look */
[data-testid="stDecoration"] {{ background: linear-gradient(90deg, var(--primary), var(--accent)); }}
</style>
""", unsafe_allow_html=True)
