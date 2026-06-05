"""
PPT export — generates a presentation with one chart slide per ticker.
"""
import io
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

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


def _make_chart_png(ticker: str, period: str = "6mo") -> bytes | None:
    try:
        import yfinance as yf
        import mplfinance as mpf
        import numpy as np

        hist = yf.Ticker(ticker).history(period=period)
        if hist.empty or len(hist) < 30:
            return None

        hist.index = hist.index.tz_localize(None)
        ohlcv = hist[["Open", "High", "Low", "Close", "Volume"]].copy()
        close = ohlcv["Close"]

        # ── RSI (14) ──────────────────────────────────────────────
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + gain / loss))

        # ── MACD (12, 26, 9) ──────────────────────────────────────
        macd_line   = close.ewm(span=12, adjust=False).mean() - \
                      close.ewm(span=26, adjust=False).mean()
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist   = macd_line - signal_line
        hist_colors = ["#26a69a" if v >= 0 else "#ef5350"
                       for v in macd_hist.fillna(0)]

        # ── Price info for title ──────────────────────────────────
        last  = close.iloc[-1]
        prev  = close.iloc[-2] if len(close) > 1 else last
        chg   = last - prev
        chg_p = chg / prev * 100
        sign  = "+" if chg >= 0 else ""
        title_str = (f"\n{ticker}   ${last:,.2f}   "
                     f"{sign}{chg:.2f} ({sign}{chg_p:.2f}%)")

        # ── mplfinance style (TradingView light) ─────────────────
        mc = mpf.make_marketcolors(
            up="#26a69a", down="#ef5350",
            wick={"up": "#26a69a", "down": "#ef5350"},
            edge={"up": "#26a69a", "down": "#ef5350"},
            volume={"up": "#26a69a", "down": "#ef5350"},
        )
        style = mpf.make_mpf_style(
            marketcolors=mc,
            gridstyle="--",
            gridcolor="#E2E8F0",
            gridaxis="both",
            facecolor="white",
            figcolor="white",
            rc={
                "axes.labelcolor": "#64748B",
                "xtick.color": "#64748B",
                "ytick.color": "#64748B",
                "font.size": 9,
            },
        )

        # ── Extra indicators ──────────────────────────────────────
        apds = [
            # RSI overbought/oversold reference lines
            mpf.make_addplot([70] * len(rsi), panel=2,
                             color="#E2E8F0", linestyle="--", width=0.7),
            mpf.make_addplot([30] * len(rsi), panel=2,
                             color="#E2E8F0", linestyle="--", width=0.7),
            mpf.make_addplot(rsi, panel=2, color="#9333ea",
                             width=1.4, ylabel="RSI 14"),
            # MACD
            mpf.make_addplot(macd_hist, panel=3, type="bar",
                             color=hist_colors, alpha=0.7, ylabel="MACD"),
            mpf.make_addplot(macd_line,   panel=3, color="#3B82F6", width=1.2),
            mpf.make_addplot(signal_line, panel=3, color="#F97316", width=1.2),
        ]

        fig, axes = mpf.plot(
            ohlcv,
            type="candle",
            style=style,
            volume=True,
            addplot=apds,
            returnfig=True,
            figsize=(14, 9),
            panel_ratios=(4, 1.2, 1.5, 1.5),
            title=title_str,
        )

        # Title colour
        axes[0].title.set_color("#1E3A8A")
        axes[0].title.set_fontsize(13)
        axes[0].title.set_fontweight("bold")

        # RSI shaded zones
        rsi_ax = axes[4]  # panel 2 = axes index 4 (candle,vol,rsi,macd)
        try:
            rsi_ax.axhspan(70, 100, alpha=0.07, color="#ef5350", zorder=0)
            rsi_ax.axhspan(0, 30,   alpha=0.07, color="#26a69a", zorder=0)
            rsi_ax.set_ylim(0, 100)
        except Exception:
            pass

        fig.tight_layout(pad=1.0)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150,
                    bbox_inches="tight", facecolor="white")
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    except Exception as e:
        print(f"[chart error] {ticker}: {e}")
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
