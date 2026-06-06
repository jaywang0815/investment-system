"""
PPT export — generates a presentation with one chart slide per ticker.
"""
import io
import math
import unicodedata
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle as MplRect

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


def _clean_ticker(t: str) -> str:
    """Normalize full-width chars (ＡＮＥＴ→ANET), strip $, uppercase."""
    return unicodedata.normalize("NFKC", t).lstrip("$").strip().upper()


def _is_valid(val) -> bool:
    """Return True only if val is a real non-NaN number."""
    if val is None:
        return False
    try:
        return not math.isnan(float(val))
    except (TypeError, ValueError):
        return bool(val)


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
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        left, top, width, height
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_rgb
    shape.line.fill.background()
    return shape


# ── indicator helpers ─────────────────────────────────────────────
def _calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    return 100 - (100 / (1 + gain / loss))


def _calc_macd(close, fast=12, slow=26, signal=9):
    macd_line   = close.ewm(span=fast, adjust=False).mean() - \
                  close.ewm(span=slow, adjust=False).mean()
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist        = macd_line - signal_line
    return macd_line, signal_line, hist


def _strip_tz(idx):
    """Remove timezone from DatetimeIndex safely."""
    if hasattr(idx, "tz") and idx.tz is not None:
        try:
            return idx.tz_localize(None)
        except Exception:
            return idx.tz_convert(None)
    return idx


# ── mplfinance chart ──────────────────────────────────────────────
def _chart_mplfinance(ohlcv, ticker, hlines: dict | None = None) -> bytes | None:
    try:
        import mplfinance as mpf

        close = ohlcv["Close"].astype(float)
        rsi = _calc_rsi(close).fillna(50)
        macd_line, signal_line, macd_hist = _calc_macd(close)
        macd_line   = macd_line.fillna(0)
        signal_line = signal_line.fillna(0)
        macd_hist   = macd_hist.fillna(0)
        hist_colors = ["#26a69a" if v >= 0 else "#ef5350"
                       for v in macd_hist]

        last  = close.iloc[-1]
        prev  = close.iloc[-2] if len(close) > 1 else last
        chg   = last - prev
        chg_p = chg / prev * 100
        sign  = "+" if chg >= 0 else ""
        title_str = (f"\n{ticker}   ${last:,.2f}   "
                     f"{sign}{chg:.2f} ({sign}{chg_p:.2f}%)")

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

        apds = [
            mpf.make_addplot([70] * len(rsi), panel=2,
                             color="#cbd5e1", linestyle="--", width=0.7),
            mpf.make_addplot([30] * len(rsi), panel=2,
                             color="#cbd5e1", linestyle="--", width=0.7),
            mpf.make_addplot(rsi, panel=2, color="#9333ea",
                             width=1.4, ylabel="RSI 14"),
            mpf.make_addplot(macd_hist, panel=3, type="bar",
                             color=hist_colors, alpha=0.75, ylabel="MACD"),
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

        axes[0].title.set_color("#1E3A8A")
        axes[0].title.set_fontsize(13)
        axes[0].title.set_fontweight("bold")

        _draw_hlines(axes[0], hlines, len(ohlcv))

        # RSI shaded zones — axes order: [candle, candle_twin, vol, vol_twin, rsi, ...]
        try:
            rsi_ax = axes[4]
            rsi_ax.axhspan(70, 100, alpha=0.07, color="#ef5350", zorder=0)
            rsi_ax.axhspan(0,  30,  alpha=0.07, color="#26a69a", zorder=0)
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
        print(f"[mplfinance error] {e}")
        return None


# ── fallback: pure matplotlib candlestick + RSI + MACD ───────────
def _chart_matplotlib(ohlcv, ticker, hlines: dict | None = None) -> bytes | None:
    try:
        close  = ohlcv["Close"].astype(float)
        opens  = ohlcv["Open"].astype(float)
        highs  = ohlcv["High"].astype(float)
        lows   = ohlcv["Low"].astype(float)
        volume = ohlcv["Volume"].fillna(0).astype(float)
        dates  = ohlcv.index
        n      = len(dates)
        xs     = list(range(n))

        rsi = _calc_rsi(close).fillna(50)           # neutral while warming up
        macd_line, signal_line, macd_hist = _calc_macd(close)
        macd_line   = macd_line.fillna(0)
        signal_line = signal_line.fillna(0)
        macd_hist   = macd_hist.fillna(0)

        last  = float(close.iloc[-1])
        prev  = float(close.iloc[-2]) if n > 1 else last
        chg   = last - prev
        chg_p = chg / prev * 100 if prev != 0 else 0
        sign  = "+" if chg >= 0 else ""

        fig, axes = plt.subplots(
            4, 1, figsize=(14, 9),
            gridspec_kw={"height_ratios": [4, 1.2, 1.5, 1.5]},
            facecolor="white", sharex=True,
        )
        ax1, ax2, ax3, ax4 = axes
        fig.suptitle(
            f"{ticker}   ${last:,.2f}   {sign}{chg:.2f} ({sign}{chg_p:.2f}%)",
            fontsize=13, color="#1E3A8A", fontweight="bold", y=0.98,
        )

        for ax in axes:
            ax.set_facecolor("white")
            ax.grid(axis="y", color="#E2E8F0", linewidth=0.7, linestyle="--")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.tick_params(colors="#64748B", labelsize=8)

        # ── Candlestick ──────────────────────────────────────────
        cl_arr = close.values
        op_arr = opens.values
        hi_arr = highs.values
        lo_arr = lows.values
        for i in xs:
            is_up   = cl_arr[i] >= op_arr[i]
            col     = "#26a69a" if is_up else "#ef5350"
            body_lo = min(op_arr[i], cl_arr[i])
            body_hi = max(op_arr[i], cl_arr[i])
            ax1.plot([i, i], [lo_arr[i], hi_arr[i]], color=col, linewidth=0.8)
            ax1.add_patch(MplRect(
                (i - 0.35, body_lo), 0.7, max(body_hi - body_lo, 0.001),
                color=col, zorder=2,
            ))
        ax1.set_xlim(-1, n)
        ax1.yaxis.tick_right()
        _draw_hlines(ax1, hlines, n)

        # ── Volume ───────────────────────────────────────────────
        vol_cols = ["#26a69a" if cl_arr[i] >= op_arr[i] else "#ef5350"
                    for i in xs]
        ax2.bar(xs, volume.values, color=vol_cols, alpha=0.6, width=0.7)
        ax2.yaxis.tick_right()
        ax2.set_ylabel("Vol", color="#94A3B8", fontsize=8)

        # ── RSI ──────────────────────────────────────────────────
        ax3.plot(xs, rsi.values, color="#9333ea", linewidth=1.3)
        ax3.axhline(70, color="#ef5350", linestyle="--", linewidth=0.7)
        ax3.axhline(30, color="#26a69a", linestyle="--", linewidth=0.7)
        ax3.axhspan(70, 100, alpha=0.06, color="#ef5350")
        ax3.axhspan(0,  30,  alpha=0.06, color="#26a69a")
        ax3.set_ylim(0, 100)
        ax3.yaxis.tick_right()
        ax3.set_ylabel("RSI 14", color="#9333ea", fontsize=8)

        # ── MACD ─────────────────────────────────────────────────
        mh = macd_hist.values
        bar_cols = ["#26a69a" if v >= 0 else "#ef5350" for v in mh]
        ax4.bar(xs, mh, color=bar_cols, alpha=0.65, width=0.7)
        ax4.plot(xs, macd_line.values,   color="#3B82F6", linewidth=1.2)
        ax4.plot(xs, signal_line.values, color="#F97316", linewidth=1.2)
        ax4.axhline(0, color="#CBD5E1", linewidth=0.7)
        ax4.yaxis.tick_right()
        ax4.set_ylabel("MACD", color="#64748B", fontsize=8)

        # x-axis date labels
        tick_step = max(1, n // 8)
        tick_pos  = list(range(0, n, tick_step))
        ax4.set_xticks(tick_pos)
        ax4.set_xticklabels(
            [dates[i].strftime("%m/%d") for i in tick_pos],
            rotation=0, fontsize=8, color="#64748B",
        )

        plt.tight_layout(pad=0.8)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150,
                    bbox_inches="tight", facecolor="white")
        plt.close(fig)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        print(f"[matplotlib chart error] {ticker}: {type(e).__name__}: {e}")
        return None


# ── last-resort: simple line chart ───────────────────────────────
def _chart_simple(ohlcv, ticker, hlines: dict | None = None) -> bytes | None:
    try:
        close = ohlcv["Close"].astype(float)
        dates = ohlcv.index
        n     = len(dates)
        xs    = list(range(n))

        last  = float(close.iloc[-1])
        prev  = float(close.iloc[-2]) if n > 1 else last
        chg_p = (last - prev) / prev * 100 if prev != 0 else 0
        sign  = "+" if chg_p >= 0 else ""
        color = "#26a69a" if chg_p >= 0 else "#ef5350"

        fig, ax = plt.subplots(figsize=(14, 6), facecolor="white")
        ax.set_facecolor("white")
        ax.plot(xs, close.values, color=color, linewidth=2)
        ax.fill_between(xs, close.values, close.min() * 0.995,
                        alpha=0.1, color=color)
        ax.set_title(
            f"{ticker}   ${last:,.2f}   {sign}{chg_p:.2f}%",
            fontsize=13, color="#1E3A8A", fontweight="bold",
        )
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="y", color="#E2E8F0", linewidth=0.7, linestyle="--")
        ax.tick_params(colors="#64748B", labelsize=8)
        ax.yaxis.tick_right()
        tick_step = max(1, n // 8)
        tick_pos  = list(range(0, n, tick_step))
        ax.set_xticks(tick_pos)
        ax.set_xticklabels(
            [dates[i].strftime("%m/%d") for i in tick_pos],
            rotation=0, fontsize=8, color="#64748B",
        )
        _draw_hlines(ax, hlines, n)
        plt.tight_layout(pad=0.8)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150,
                    bbox_inches="tight", facecolor="white")
        plt.close(fig)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        print(f"[simple chart error] {ticker}: {e}")
        return None


def _draw_hlines(ax, hlines: dict, n: int) -> None:
    """Draw 期初/KO/KI reference lines on a price axis."""
    if not hlines:
        return
    cfg = [
        ("initial", "#F97316", ":", "期初"),
        ("ko",      "#16A34A", "--", "KO"),
        ("ki",      "#DC2626", "--", "KI"),
    ]
    for key, color, ls, label in cfg:
        price = hlines.get(key)
        if price and _is_valid(price):
            ax.axhline(float(price), color=color, linestyle=ls,
                       linewidth=1.3, alpha=0.85, zorder=3)
            ax.text(n - 1, float(price),
                    f" {label} ${float(price):,.2f}",
                    va="bottom", ha="right",
                    color=color, fontsize=8, fontweight="bold",
                    zorder=4)


def _make_chart_png(ticker: str, period: str = "6mo",
                    hlines: dict | None = None) -> bytes | None:
    try:
        import yfinance as yf
        from datetime import datetime, timedelta
        ticker = _clean_ticker(ticker)
        tk = yf.Ticker(ticker)
        if period == "18mo":
            start = (datetime.today() - timedelta(days=548)).strftime("%Y-%m-%d")
            hist = tk.history(start=start)
        else:
            hist = tk.history(period=period)
        if hist.empty or len(hist) < 10:
            print(f"[chart] {ticker}: not enough data ({len(hist)} rows)")
            return None

        hist.index = _strip_tz(hist.index)
        hist = hist.dropna(subset=["Close", "Open", "High", "Low"])
        if len(hist) < 10:
            print(f"[chart] {ticker}: not enough clean data after dropna")
            return None

        ohlcv = hist[["Open", "High", "Low", "Close", "Volume"]].copy()
        ohlcv["Volume"] = ohlcv["Volume"].fillna(0)

        result = _chart_mplfinance(ohlcv, ticker, hlines=hlines)
        if result is None:
            print(f"[chart] {ticker}: mplfinance failed, trying matplotlib")
            result = _chart_matplotlib(ohlcv, ticker, hlines=hlines)
        if result is None:
            print(f"[chart] {ticker}: matplotlib failed, trying simple line")
            result = _chart_simple(ohlcv, ticker, hlines=hlines)
        if result is None:
            print(f"[chart] {ticker}: all chart methods failed")
        return result
    except Exception as e:
        print(f"[chart error] {ticker}: {type(e).__name__}: {e}")
        return None


def build_ppt(tickers: list[str], sn_info: dict | None = None,
              period: str = "6mo") -> bytes:
    """
    tickers  : list of stock symbols
    sn_info  : dict[ticker] = {ko, ki, product_code, ...}  (optional)
    period   : yfinance period string e.g. "1mo", "3mo", "6mo", "1y", "2y"
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

        _rect(s, 0, 0, W, Inches(0.85), _BLUE)

        _textbox(s, Inches(0.3), Inches(0.08), Inches(6), Inches(0.7),
                 ticker, 28, bold=True, color=_WHITE)

        _textbox(s, Inches(8), Inches(0.15), Inches(5), Inches(0.55),
                 date.today().strftime("%Y/%m/%d"),
                 14, color=RGBColor(0xBF, 0xDB, 0xFF), align=PP_ALIGN.RIGHT)

        # KO / KI badge — skip NaN values
        info      = (sn_info or {}).get(ticker, {})
        ko        = info.get("ko")
        ki        = info.get("ki")
        init_p    = info.get("initial_price")
        code      = info.get("product_code", "")
        badge_parts = []
        if code and str(code).strip():
            badge_parts.append(str(code))
        if _is_valid(init_p):
            badge_parts.append(f"期初 ${float(init_p):,.2f}")
        if _is_valid(ko):
            badge_parts.append(f"KO {float(ko)*100:.0f}%")
        if _is_valid(ki):
            badge_parts.append(f"KI {float(ki)*100:.0f}%")
        if badge_parts:
            _textbox(s, Inches(0.3), Inches(0.88), Inches(12), Inches(0.45),
                     "  ·  ".join(badge_parts),
                     11, color=_GRAY)

        # คำนวณ hlines จาก initial_price
        hlines = {}
        if _is_valid(init_p):
            hlines["initial"] = float(init_p)
            if _is_valid(ko):
                hlines["ko"] = round(float(init_p) * float(ko), 2)
            if _is_valid(ki):
                hlines["ki"] = round(float(init_p) * float(ki), 2)

        img_bytes = _make_chart_png(ticker, period=period, hlines=hlines or None)
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
