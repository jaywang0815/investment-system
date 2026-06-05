"""
PPT export — generates a presentation with one chart slide per ticker.
"""
import io
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN


# ── colours ──────────────────────────────────────────────────────
_NAVY  = RGBColor(0x0F, 0x25, 0x57)
_BLUE  = RGBColor(0x1E, 0x3A, 0x8A)
_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
_GRAY  = RGBColor(0x64, 0x74, 0x8B)
_GREEN = RGBColor(0x16, 0xA3, 0x4A)
_RED   = RGBColor(0xDC, 0x26, 0x26)


def _textbox(slide, left, top, width, height, text, size,
             bold=False, color=_WHITE, align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def _rect(slide, left, top, width, height, fill_rgb):
    from pptx.util import Emu
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        left, top, width, height
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_rgb
    shape.line.fill.background()
    return shape


def _make_chart_png(ticker: str, period: str = "3mo") -> bytes | None:
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period=period)
        if hist.empty:
            return None

        close = hist["Close"]
        up = close.iloc[-1] >= close.iloc[0]
        color = "#16A34A" if up else "#DC2626"
        chg = (close.iloc[-1] / close.iloc[0] - 1) * 100
        sign = "+" if chg >= 0 else ""

        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(11, 5.5),
            gridspec_kw={"height_ratios": [3, 1]},
            facecolor="white"
        )
        # Price
        ax1.set_facecolor("white")
        ax1.plot(hist.index, close, color=color, linewidth=2)
        ax1.fill_between(hist.index, close, close.min() * 0.995,
                         alpha=0.12, color=color)
        ax1.set_title(
            f"{ticker}   ${close.iloc[-1]:,.2f}   {sign}{chg:.1f}%  (3 months)",
            fontsize=13, color="#1E3A8A", pad=8, fontweight="bold"
        )
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        ax1.grid(axis="y", color="#E2E8F0", linewidth=0.8)
        ax1.spines[["top", "right"]].set_visible(False)
        ax1.tick_params(colors="#64748B", labelsize=9)
        ax1.yaxis.tick_right()
        ax1.set_xlim(hist.index[0], hist.index[-1])

        # Volume
        ax2.set_facecolor("white")
        ax2.bar(hist.index, hist["Volume"], color=color, alpha=0.45, width=0.8)
        ax2.spines[["top", "right"]].set_visible(False)
        ax2.tick_params(colors="#64748B", labelsize=8)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        ax2.set_xlim(hist.index[0], hist.index[-1])
        ax2.set_ylabel("Vol", color="#94A3B8", fontsize=8)

        plt.tight_layout(pad=1.2)
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150,
                    bbox_inches="tight", facecolor="white")
        plt.close(fig)
        buf.seek(0)
        return buf.read()
    except Exception:
        return None


def build_ppt(tickers: list[str], sn_info: dict | None = None) -> bytes:
    """
    tickers  : list of stock symbols
    sn_info  : dict[ticker] = {ko, ki, product_code, ...}  (optional)
    Returns  : PPT file as bytes
    """
    W = Inches(13.33)
    H = Inches(7.5)

    prs = Presentation()
    prs.slide_width  = W
    prs.slide_height = H
    blank = prs.slide_layouts[6]  # fully blank

    # ── Title slide ───────────────────────────────────────────────
    s = prs.slides.add_slide(blank)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = _NAVY

    # Logo image (optional)
    logo_path = Path(__file__).parent.parent / "assets" / "logo.png"
    if logo_path.exists():
        s.shapes.add_picture(str(logo_path),
                             Inches(5.67), Inches(1.2),
                             Inches(2.0), Inches(2.0))

    _textbox(s, Inches(0), Inches(3.5), W, Inches(1.2),
             "DOUU WORK", 52, bold=True, color=_WHITE, align=PP_ALIGN.CENTER)
    _textbox(s, Inches(0), Inches(4.7), W, Inches(0.7),
             f"持倉標的走勢報告  ·  {date.today().strftime('%Y / %m / %d')}",
             18, color=RGBColor(0x94, 0xA3, 0xB8), align=PP_ALIGN.CENTER)
    _textbox(s, Inches(0), Inches(5.6), W, Inches(0.5),
             f"共 {len(tickers)} 個標的",
             13, color=RGBColor(0x64, 0x74, 0x8B), align=PP_ALIGN.CENTER)

    # ── One slide per ticker ──────────────────────────────────────
    for ticker in tickers:
        s = prs.slides.add_slide(blank)
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = _WHITE

        # Header bar
        _rect(s, 0, 0, W, Inches(0.85), _BLUE)

        # Ticker name in header
        _textbox(s, Inches(0.3), Inches(0.08), Inches(6), Inches(0.7),
                 ticker, 28, bold=True, color=_WHITE)

        # Date in header (right side)
        _textbox(s, Inches(8), Inches(0.15), Inches(5), Inches(0.55),
                 date.today().strftime("%Y/%m/%d"),
                 14, color=RGBColor(0xBF, 0xDB, 0xFF), align=PP_ALIGN.RIGHT)

        # KO / KI info (if available)
        info = (sn_info or {}).get(ticker, {})
        ko = info.get("ko")
        ki = info.get("ki")
        code = info.get("product_code", "")
        badge_parts = []
        if code:
            badge_parts.append(code)
        if ko:
            badge_parts.append(f"KO {ko*100:.0f}%")
        if ki:
            badge_parts.append(f"KI {ki*100:.0f}%")
        if badge_parts:
            _textbox(s, Inches(0.3), Inches(0.88), Inches(12), Inches(0.45),
                     "  ·  ".join(badge_parts),
                     11, color=_GRAY)

        # Chart image
        img_bytes = _make_chart_png(ticker)
        if img_bytes:
            img_stream = io.BytesIO(img_bytes)
            s.shapes.add_picture(img_stream,
                                 Inches(0.2), Inches(1.35),
                                 Inches(12.9), Inches(5.9))
        else:
            _textbox(s, Inches(1), Inches(3), Inches(11), Inches(1),
                     f"無法取得 {ticker} 圖表資料",
                     18, color=_GRAY, align=PP_ALIGN.CENTER)

    out = io.BytesIO()
    prs.save(out)
    out.seek(0)
    return out.read()
