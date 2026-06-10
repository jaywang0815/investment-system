"""
PDF 報表產生模組 - 繁體中文
使用 reportlab + macOS 內建 PingFang 字型
"""
from __future__ import annotations
import io
import os
import re
from datetime import date, datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage, KeepTogether
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── 字型設定 ──────────────────────────────────────────────
def _register_font():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    regular = os.path.join(base_dir, "assets", "NotoSansTC-Regular.ttf")
    bold    = os.path.join(base_dir, "assets", "NotoSansTC-Bold.ttf")
    if os.path.exists(regular):
        try:
            pdfmetrics.registerFont(TTFont("ChineseFont", regular))
            pdfmetrics.registerFont(TTFont("ChineseFontBold", bold if os.path.exists(bold) else regular))
            return True
        except Exception:
            pass
    # macOS fallback
    for path in ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc"]:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("ChineseFont", path, subfontIndex=0))
                pdfmetrics.registerFont(TTFont("ChineseFontBold", path, subfontIndex=0))
                return True
            except Exception:
                continue
    return False

_font_registered = _register_font()
FONT = "ChineseFont" if _font_registered else "Helvetica"
FONT_BOLD = "ChineseFontBold" if _font_registered else "Helvetica-Bold"

# ── 顏色 (整份報表的主題色) — 統一證券 品牌紅，集中於 utils/branding ──
from utils import branding as B
BLUE_DARK  = colors.HexColor(B.hx(B.C_PRIMARY))   # 主色 — 標題/表頭/區塊標題 (深品牌紅)
BLUE_MID   = colors.HexColor(B.hx(B.C_ACCENT))    # 強調 — 品牌紅
BLUE_LIGHT = colors.HexColor(B.hx(B.C_TINT))      # 淺色底 (標籤格/淺列) — 淺紅
GRAY       = colors.HexColor("#" + B.C_MUTED)
GRAY_LIGHT = colors.HexColor(B.hx(B.C_ZEBRA))     # 斑馬列中性暖灰
RED        = colors.HexColor(B.hx(B.C_RED))
GREEN      = colors.HexColor(B.hx(B.C_GREEN))
ORANGE     = colors.HexColor("#EA580C")
WHITE      = colors.white

_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FFFF\U00002600-\U000027BF\U0000FE00-\U0000FE0F]+",
    flags=re.UNICODE,
)

def _clean(text) -> str:
    """Strip emoji characters that the font cannot render"""
    return _EMOJI_RE.sub("", str(text) if text is not None else "").strip()

_PERIOD_DAYS = {
    "3mo": 90, "6mo": 180, "1y": 365, "18mo": 548,
    "2y": 730, "2y6mo": 912, "3y": 1095, "3y6mo": 1277,
    "4y": 1460, "4y6mo": 1642, "5y": 1825,
}

# 圖表標題用英文 (matplotlib 無中文字型，避免變成方塊)
_PERIOD_LABELS = {
    "3mo": "3-Month", "6mo": "6-Month", "1y": "1-Year", "18mo": "18-Month",
    "2y": "2-Year", "2y6mo": "2.5-Year", "3y": "3-Year", "3y6mo": "3.5-Year",
    "4y": "4-Year", "4y6mo": "4.5-Year", "5y": "5-Year",
}

def _generate_price_chart(ticker: str, initial_price: float,
                          ko_barrier: float, ki_barrier: float,
                          strike_pct: float, width_mm: float = 155,
                          period: str = "6mo") -> bytes | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        import matplotlib.patches as mpatches
        import matplotlib.ticker as mticker
        import yfinance as yf
        import numpy as np
        from datetime import timedelta

        days = _PERIOD_DAYS.get(period, 180)
        period_label = _PERIOD_LABELS.get(period, "Performance")
        start = datetime.today() - timedelta(days=days)
        hist = yf.Ticker(ticker).history(start=start)
        if hist.empty:
            return None

        closes = hist["Close"]
        dates  = hist.index

        LINE = B.hx(B.C_PRIMARY)   # 深品牌紅 price line
        # ── 畫布設定 ──────────────────────────────────────────
        fig, ax = plt.subplots(figsize=(width_mm / 25.4, 3.2),
                               facecolor="white")
        ax.set_facecolor("white")

        # ── 價格線 + 陰影 ─────────────────────────────────────
        ax.plot(dates, closes, color=LINE, linewidth=1.6, zorder=4,
                solid_capstyle="round")
        ax.fill_between(dates, closes, closes.min() * 0.97,
                        alpha=0.10, color=LINE, zorder=3)

        # ── KO / KI / 執行價 水平線 ────────────────────────────
        barrier_lines = []
        if initial_price and initial_price > 0:
            if ko_barrier:
                kop = initial_price * ko_barrier
                ax.axhline(kop, color="#16A34A", linestyle="--",
                           linewidth=1.4, zorder=5, alpha=0.9)
                ax.text(dates[-1], kop, f" KO ${kop:,.0f}",
                        color="#16A34A", fontsize=6.5, va="center", zorder=6,
                        bbox=dict(boxstyle="round,pad=0.15", fc="#F0FDF4", ec="#16A34A", lw=0.5))
                barrier_lines.append(mpatches.Patch(color="#16A34A", label=f"KO {ko_barrier*100:.0f}%  ${kop:,.0f}"))
            if ki_barrier:
                kip = initial_price * ki_barrier
                ax.axhline(kip, color="#DC2626", linestyle="--",
                           linewidth=1.4, zorder=5, alpha=0.9)
                ax.text(dates[-1], kip, f" KI ${kip:,.0f}",
                        color="#DC2626", fontsize=6.5, va="center", zorder=6,
                        bbox=dict(boxstyle="round,pad=0.15", fc="#FEF2F2", ec="#DC2626", lw=0.5))
                barrier_lines.append(mpatches.Patch(color="#DC2626", label=f"KI {ki_barrier*100:.0f}%  ${kip:,.0f}"))
            if strike_pct:
                sp = initial_price * strike_pct
                ax.axhline(sp, color="#6366F1", linestyle=":",
                           linewidth=1.1, zorder=5, alpha=0.85)
                barrier_lines.append(mpatches.Patch(color="#6366F1", label=f"Strike ${sp:,.0f}"))

            # ── KI 危險帶背景 ───────────────────────────────────
            if ki_barrier:
                ax.axhspan(0, initial_price * ki_barrier,
                           alpha=0.06, color="#DC2626", zorder=2)

        # ── 最新收盤標記 ──────────────────────────────────────
        last_price = float(closes.iloc[-1])
        ax.annotate(f"${last_price:,.2f}",
                    xy=(dates[-1], last_price),
                    xytext=(-40, 9), textcoords="offset points",
                    fontsize=7, color="white", zorder=7, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.3", fc=LINE, ec="none"),
                    arrowprops=dict(arrowstyle="-", color=LINE, lw=0.8))

        # ── 軸設定 (自動挑選刻度，避免日期重疊) ─────────────────
        loc = mdates.AutoDateLocator(minticks=4, maxticks=7)
        ax.xaxis.set_major_locator(loc)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
        ax.tick_params(labelsize=7, colors="#64748B", length=0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_edgecolor("#E2E8F0")
            ax.spines[s].set_linewidth(0.6)
        ax.grid(True, axis="y", alpha=0.6, linewidth=0.4, color="#E2E8F0")
        ax.set_axisbelow(True)
        ax.margins(x=0.01)

        # ── 標題 & 圖例 ───────────────────────────────────────
        ax.set_title(f"{ticker}    {period_label} Performance",
                     fontsize=9.5, color="#0F172A", fontweight="bold",
                     pad=8, loc="left")
        if barrier_lines:
            ax.legend(handles=barrier_lines, fontsize=6, loc="upper left",
                      framealpha=0.0, edgecolor="none", labelcolor="#475569",
                      handlelength=1.4)

        fig.tight_layout(pad=0.6)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        buf.seek(0)
        return buf.read()
    except Exception:
        return None


def _style(name, **kw):
    kw.setdefault("fontName", FONT)
    return ParagraphStyle(name, **kw)

def _valid(v):
    import math
    try:
        return v is not None and not math.isnan(float(v))
    except (TypeError, ValueError):
        return False


def _brand_header(W, title: str, sub: str = ""):
    """統一證券 報表頁首：logo + 標題 + 報告人署名 (回傳 flowable)。"""
    logo = ""
    if B.has_logo():
        try:
            logo = RLImage(B.LOGO_PATH, width=15 * mm, height=15 * mm)
        except Exception:
            logo = ""
    title_p = Paragraph(
        f'<font size="9" color="#{B.C_ACCENT}">{B.COMPANY}</font><br/>'
        f'<font size="19">{title}</font>'
        + (f'<br/><font size="8.5" color="#{B.C_MUTED}">{sub}</font>' if sub else ""),
        _style("BTitle", fontName=FONT_BOLD, textColor=BLUE_DARK, leading=21))
    rep_p = Paragraph(
        f'<font size="8" color="#{B.C_MUTED}">報告人</font><br/>'
        f'<font size="11">{B.REPORTER}</font>',
        _style("BRep", fontName=FONT_BOLD, textColor=BLUE_DARK, alignment=2, leading=14))
    t = Table([[logo, title_p, rep_p]], colWidths=[19 * mm, W - 19 * mm - 34 * mm, 34 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("LEFTPADDING", (1, 0), (1, 0), 6),
        ("RIGHTPADDING", (-1, 0), (-1, 0), 0),
    ]))
    return t


def _brand_footer(report_date: str):
    """頁尾署名 (flowable list)。"""
    out = [HRFlowable(width="100%", thickness=1, color=GRAY, spaceAfter=4, spaceBefore=2)]
    out.append(Paragraph(
        f"{B.SIGNATURE}　·　報表日期 {report_date}",
        _style("Footer", fontSize=8, textColor=GRAY, alignment=1)))
    return out

# ============================================================
# 主函數: 產生客戶投資報表 PDF
# ============================================================

def generate_customer_report(customer: dict, investments: list, prices: dict,
                             chart_period: str = "6mo",
                             columns: list = None, show_info: bool = True,
                             show_amount: bool = True, show_charts: bool = True) -> bytes:
    """
    產生單一客戶的完整投資報表

    Args:
        customer: 客戶資料 dict
        investments: 投資記錄 list (含 structured_notes 欄位)
        prices: 目前股票價格 dict {ticker: price}

    Returns:
        PDF bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=15*mm,
        bottomMargin=15*mm,
        leftMargin=18*mm,
        rightMargin=18*mm,
    )

    W = A4[0] - 36*mm  # 可用寬度

    story = []
    report_date = date.today().strftime("%Y 年 %m 月 %d 日")

    # ── 封面標題 (logo + 報告人) ────────────────────────────
    story.append(_brand_header(W, "結構型商品投資報表"))
    story.append(Spacer(1, 3*mm))
    story.append(HRFlowable(width="100%", thickness=2, color=BLUE_DARK))
    story.append(Spacer(1, 6*mm))

    # ── 客戶資訊區 ──────────────────────────────────────────

    def _fmt_usd(val):
        try:
            v = float(val)
            import math
            return "—" if math.isnan(v) or v == 0 else f"USD {v:,.0f}"
        except (TypeError, ValueError):
            return "—"

    info_data = [
        ["客戶姓名", customer.get("name", "—"), "報表日期", report_date],
        ["美元總額度", _fmt_usd(customer.get("usd_amount")),
         "中信部位",  _fmt_usd(customer.get("ctbc_position"))],
    ]
    info_table = Table(info_data, colWidths=[35*mm, 65*mm, 35*mm, 40*mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
        ("FONTNAME", (2, 0), (2, -1), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (0, -1), BLUE_LIGHT),
        ("BACKGROUND", (2, 0), (2, -1), BLUE_LIGHT),
        ("TEXTCOLOR", (0, 0), (0, -1), BLUE_DARK),
        ("TEXTCOLOR", (2, 0), (2, -1), BLUE_DARK),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, GRAY_LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 8*mm))

    # ── 投資概覽 ────────────────────────────────────────────
    total_invested = sum(inv.get("amount_usd", 0) or 0 for inv in investments)
    active_count = len([inv for inv in investments
                        if inv.get("structured_notes", {}).get("status") == "active"])

    story.append(Paragraph("【投資概覽】",
        _style("H2", fontSize=13, fontName=FONT_BOLD, textColor=BLUE_DARK, spaceAfter=4)))

    overview_data = [
        ["持倉商品數", "總投資金額", "有效持倉"],
        [str(len(investments)), f"USD {total_invested:,.0f}", f"{active_count} 筆有效"],
    ]
    ov_table = Table(overview_data, colWidths=[W/3, W/3, W/3])
    ov_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("FONTSIZE", (0, 1), (-1, -1), 14),
        ("BACKGROUND", (0, 0), (-1, 0), BLUE_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("BACKGROUND", (0, 1), (-1, -1), BLUE_LIGHT),
        ("TEXTCOLOR", (0, 1), (-1, -1), BLUE_DARK),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWHEIGHT", (0, 1), (-1, -1), 14*mm),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, WHITE),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    story.append(ov_table)
    story.append(Spacer(1, 8*mm))

    # ── 各持倉明細 ──────────────────────────────────────────
    story.append(Paragraph("【持倉明細】",
        _style("H2", fontSize=13, fontName=FONT_BOLD, textColor=BLUE_DARK, spaceAfter=6)))

    for idx, inv in enumerate(investments, 1):
        sn = inv.get("structured_notes") or {}
        if not sn:
            continue

        _add_sn_detail(story, idx, inv, sn, prices, W, chart_period,
                       columns, show_info, show_amount, show_charts)
        story.append(Spacer(1, 5*mm))

    # ── 頁尾 (報告人署名) ───────────────────────────────────
    for f in _brand_footer(report_date):
        story.append(f)

    doc.build(story)
    return buffer.getvalue()


def _add_sn_detail(story, idx, inv, sn, prices, W, chart_period="6mo",
                   columns=None, show_info=True, show_amount=True, show_charts=True):
    """產生單一 SN 商品的詳細區塊"""
    from utils.stock_prices import analyze_sn_status, get_sn_underlyings

    product_code = sn.get("product_code", "—")
    underlyings = get_sn_underlyings(sn)
    ticker_names = " / ".join([u["ticker"] for u in underlyings])
    obs_date = sn.get("observation_date", "—")
    trade_date = sn.get("trade_date", "—")
    strike_pct = sn.get("strike_pct")
    coupon_pct = sn.get("coupon_pct")
    ko_barrier = sn.get("ko_barrier")
    ki_barrier = sn.get("ki_barrier")
    from utils.money import format_money
    amount_usd = inv.get("amount_usd", 0) or 0
    ccy = inv.get("currency", "USD") or "USD"

    # 取得各標的現價並分析
    ticker_list = [u["ticker"] for u in underlyings]
    current_prices = {t: prices.get(t) for t in ticker_list}
    analysis = analyze_sn_status(sn, current_prices)

    status_color = {
        "ko_triggered": GREEN,
        "ko_risk":      colors.HexColor("#CA8A04"),
        "ki_triggered": RED,
        "ki_risk":      ORANGE,
        "normal":       BLUE_DARK,
        "unknown":      GRAY,
    }.get(analysis["overall_status"], GRAY)

    # 商品標頭
    status_text = {
        "ko_triggered": "[KO觸發]",
        "ko_risk":      "[接近KO]",
        "ki_triggered": "[KI觸發]",
        "ki_risk":      "[接近KI]",
        "normal":       "[正常]",
        "unknown":      "[未知]",
    }.get(analysis["overall_status"], "")
    header_data = [[
        f"#{idx}  {product_code}",
        f"{status_text} {analysis['status_label']}",
        f"投資金額: {format_money(amount_usd, ccy)}" if show_amount else ""
    ]]
    header_table = Table(header_data, colWidths=[W*0.45, W*0.30, W*0.25])
    header_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, -1), status_color),
        ("TEXTCOLOR", (0, 0), (-1, -1), WHITE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("RIGHTPADDING", (2, 0), (2, 0), 8),
    ]))
    story.append(header_table)

    # 商品基本資訊 (可關閉)
    if show_info:
        info_rows = [
            ["標的股票", ticker_names,
             "下單日期", str(trade_date)[:10] if trade_date else "—"],
            ["執行價格", f"{strike_pct*100:.2f}%" if strike_pct else "—",
             "比價日期", str(obs_date)[:10] if obs_date else "—"],
            ["配息率(年化)", f"{coupon_pct*100:.2f}%" if coupon_pct else "—",
             "KO 水位", f"{ko_barrier*100:.0f}%" if ko_barrier else "無"],
            ["投資金額", format_money(amount_usd, ccy) if show_amount else "—",
             "KI 水位", f"{ki_barrier*100:.0f}%" if ki_barrier else "無"],
        ]
        info_table = Table(info_rows, colWidths=[35*mm, 65*mm, 35*mm, 40*mm])
        info_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), FONT),
            ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
            ("FONTNAME", (2, 0), (2, -1), FONT_BOLD),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (0, -1), GRAY_LIGHT),
            ("BACKGROUND", (2, 0), (2, -1), GRAY_LIGHT),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(info_table)

    # 各標的現價明細 (欄位可勾選；標的名稱固定顯示)
    if analysis["details"]:
        ALL_COLS = [
            ("期初價格", lambda d: f"${d['initial_price']:,.2f}" if _valid(d.get("initial_price")) else "—"),
            ("現價",     lambda d: f"${d['current_price']:,.2f}" if _valid(d.get("current_price")) else "取得中"),
            ("漲跌幅",   lambda d: f"{d['change_pct']:+.2f}%" if _valid(d.get("change_pct")) else "—"),
            ("執行價",   lambda d: f"${d['strike_price']:,.2f}" if _valid(d.get("strike_price")) else "—"),
            ("KO 水位",  lambda d: f"${d['ko_price']:,.2f}" if _valid(d.get("ko_price")) else "無"),
            ("KI 水位",  lambda d: f"${d['ki_price']:,.2f}" if _valid(d.get("ki_price")) else "無"),
            ("狀態",     lambda d: _clean(f"{d['ko_status']} {d['ki_status']}")),
        ]
        sel = [c for c in ALL_COLS if (columns is None or c[0] in columns)]

        price_header = ["標的股票"] + [c[0] for c in sel]
        price_rows = [price_header]
        for d in analysis["details"]:
            price_rows.append([d["ticker"]] + [fn(d) for _, fn in sel])

        tw = 24.0  # ticker column (mm)
        rest = max((W / mm - tw) / max(len(sel), 1), 16.0)
        col_w = [tw * mm] + [rest * mm] * len(sel)
        price_table = Table(price_rows, colWidths=col_w)
        price_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), FONT),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (-1, 0), BLUE_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(price_table)

    # ── 價格走勢圖 (每張圖上方加標的數據摘要) ──────────────────
    if not show_charts:
        story.append(Spacer(1, 4 * mm))
        return
    detail_by_ticker = {d["ticker"]: d for d in analysis.get("details", [])}
    for u in underlyings:
        chart_bytes = _generate_price_chart(
            ticker=u["ticker"],
            initial_price=u.get("initial_price") or 0,
            ko_barrier=sn.get("ko_barrier"),
            ki_barrier=sn.get("ki_barrier"),
            strike_pct=sn.get("strike_pct"),
            width_mm=W / mm,
            period=chart_period,
        )
        if not chart_bytes:
            continue

        d = detail_by_ticker.get(u["ticker"], {})
        chg = d.get("change_pct")
        chg_col = GREEN if (_valid(chg) and chg >= 0) else RED if _valid(chg) else GRAY
        cap = [[
            u["ticker"],
            f"期初 ${d['initial_price']:,.2f}" if _valid(d.get("initial_price")) else "期初 —",
            f"現價 ${d['current_price']:,.2f}" if _valid(d.get("current_price")) else "現價 —",
            f"{chg:+.2f}%" if _valid(chg) else "—",
            _clean(f"{d.get('ko_status','')} {d.get('ki_status','')}").strip() or "—",
        ]]
        cap_table = Table(cap, colWidths=[W*0.14, W*0.24, W*0.24, W*0.14, W*0.24])
        cap_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), FONT),
            ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("BACKGROUND", (0, 0), (-1, -1), BLUE_LIGHT),
            ("TEXTCOLOR", (0, 0), (0, 0), BLUE_DARK),
            ("TEXTCOLOR", (3, 0), (3, 0), chg_col),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (0, 0), 8),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, BLUE_MID),
        ]))

        img_buf = io.BytesIO(chart_bytes)
        rl_img = RLImage(img_buf, width=W, height=W * 0.36)
        story.append(Spacer(1, 3*mm))
        story.append(KeepTogether([cap_table, rl_img]))


# ============================================================
# 投資績效明細表 (全部客戶) — 仿 投資績效明細表.xlsx 格式
# ============================================================

def _detail_to_date(v):
    if v is None or v == "":
        return None
    s = str(v)[:10]
    try:
        from datetime import date as _d
        return _d.fromisoformat(s)
    except Exception:
        return None


def _tenor(trade, obs):
    td, od = _detail_to_date(trade), _detail_to_date(obs)
    if td and od and od > td:
        m = max(round((od - td).days / 30), 1)
        return f"{m}M"
    return "—"


def _roc(d):
    """民國紀年: 2026-04-24 -> 115/04/24"""
    if d is None:
        return "—"
    return f"{d.year - 1911}/{d.month:02d}/{d.day:02d}"


def generate_portfolio_detail(items: list, report_date: str = "") -> bytes:
    """
    items: list of dict {customer, trade_date, product_code, observation_date,
                         coupon_pct, amount, currency, exit_date}
    產生「投資績效明細表」: 依客戶分組，每組明細 + 小計(原幣)，最後總計。
    """
    from utils.money import format_money

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=14 * mm,
                            bottomMargin=14 * mm, leftMargin=16 * mm, rightMargin=16 * mm)
    W = A4[0] - 32 * mm
    story = []

    story.append(_brand_header(W, "投資績效明細表",
                 sub=(f"報表日期 {report_date}" if report_date else "")))
    story.append(Spacer(1, 2 * mm))
    story.append(HRFlowable(width="100%", thickness=2, color=BLUE_DARK, spaceAfter=8, spaceBefore=2))

    # group by customer (preserve order of first appearance)
    groups = {}
    for it in items:
        groups.setdefault(it.get("customer") or "—", []).append(it)

    def _ccy_totals(rows):
        agg = {}
        for r in rows:
            amt = r.get("amount") or 0
            agg[r.get("currency") or "USD"] = agg.get(r.get("currency") or "USD", 0) + amt
        return agg

    def _fmt_totals(agg):
        return "　".join(format_money(v, c) for c, v in sorted(agg.items())) or "—"

    def _combo(r):
        ten = _tenor(r.get("trade_date"), r.get("observation_date"))
        cp = r.get("coupon_pct")
        cps = f"{cp*100:g}%" if cp else ""
        if ten != "—" and cps:
            return f"{ten} / {cps}"
        return cps or (ten if ten != "—" else "—")

    today = date.today()
    col_w = [24 * mm, 34 * mm, 28 * mm, 40 * mm, W - 126 * mm]   # 日期 代號 期間/配息 金額 備註
    EXIT_BG = colors.HexColor(B.hx(B.C_EXIT_BG))
    NEW_BG  = colors.HexColor(B.hx(B.C_NEW_BG))
    grand = {}

    for cust, rows in groups.items():
        sub = _ccy_totals(rows)
        for c, v in sub.items():
            grand[c] = grand.get(c, 0) + v
        # 客戶群組標頭帶: 姓名 | 小計
        head = Table([[cust, f"小計　{_fmt_totals(sub)}"]], colWidths=[W * 0.42, W * 0.58])
        head.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), FONT_BOLD),
            ("FONTSIZE", (0, 0), (0, 0), 12), ("FONTSIZE", (1, 0), (1, 0), 10),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(B.hx(B.C_HEADER))),
            ("TEXTCOLOR", (0, 0), (-1, -1), WHITE),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))

        data = [["日期", "代號", "期間 / 配息", "金額", "備註"]]
        row_bg = []
        for r in rows:
            td = _detail_to_date(r.get("trade_date"))
            # 編輯後的顯示值優先 (date_str/combo/note/exited/is_new)，否則自動計算
            exited = bool(r["exited"]) if r.get("exited") is not None else bool(r.get("exit_date"))
            is_new = (bool(r["is_new"]) if r.get("is_new") is not None
                      else bool(td and td.year == today.year and td.month == today.month))
            note = r.get("note") or ("出場" if exited else "")
            data.append([
                r.get("date_str") or _roc(td),
                r.get("product_code") or "—",
                r.get("combo") or _combo(r),
                format_money(r.get("amount"), r.get("currency") or "USD"),
                note,
            ])
            ri = len(data) - 1
            if exited:
                row_bg.append((ri, EXIT_BG))
            elif is_new:
                row_bg.append((ri, NEW_BG))

        ts = [
            ("FONTNAME", (0, 0), (-1, -1), FONT),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("FONTNAME", (1, 1), (1, -1), FONT_BOLD),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), BLUE_LIGHT),
            ("TEXTCOLOR", (0, 0), (-1, 0), BLUE_DARK),
            ("TEXTCOLOR", (1, 1), (1, -1), colors.HexColor(B.hx(B.C_PRIMARY))),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (2, 0), (2, -1), "CENTER"),
            ("ALIGN", (3, 0), (3, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, BLUE_MID),
            ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor(B.hx(B.C_BORDER))),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ]
        for ri, col in row_bg:
            ts.append(("BACKGROUND", (0, ri), (-1, ri), col))
        t = Table(data, colWidths=col_w, repeatRows=1)
        t.setStyle(TableStyle(ts))
        story.append(KeepTogether([head, t]))
        story.append(Spacer(1, 6 * mm))

    # ── 總計帶 ───────────────────────────────────────────────
    grand_band = Table([["總計　TOTAL", _fmt_totals(grand)]], colWidths=[W * 0.4, W * 0.6])
    grand_band.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_BOLD), ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_DARK), ("TEXTCOLOR", (0, 0), (-1, -1), WHITE),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(grand_band)

    # 圖例
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        f'<font color="#{B.C_GREEN}">■</font> 本月新增　'
        f'<font color="#D9A300">■</font> 已出場　'
        f'<font color="#{B.C_MUTED}">金額以原幣顯示・日期為民國紀年</font>',
        _style("Legend", fontSize=8, textColor=GRAY)))

    for f in _brand_footer(report_date or today.strftime("%Y-%m-%d")):
        story.append(f)

    doc.build(story)
    return buffer.getvalue()
