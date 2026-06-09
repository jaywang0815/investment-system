"""
PDF 報表產生模組 - 繁體中文
使用 reportlab + macOS 內建 PingFang 字型
"""
import io
import os
import re
from datetime import date, datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage
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

# ── 顏色 ──────────────────────────────────────────────────
BLUE_DARK  = colors.HexColor("#1E3A8A")
BLUE_MID   = colors.HexColor("#3B82F6")
BLUE_LIGHT = colors.HexColor("#EFF6FF")
GRAY       = colors.HexColor("#64748B")
GRAY_LIGHT = colors.HexColor("#F1F5F9")
RED        = colors.HexColor("#DC2626")
GREEN      = colors.HexColor("#16A34A")
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
        import yfinance as yf
        import numpy as np
        from datetime import timedelta

        days = _PERIOD_DAYS.get(period, 180)
        start = datetime.today() - timedelta(days=days)
        hist = yf.Ticker(ticker).history(start=start)
        if hist.empty:
            return None

        closes = hist["Close"]
        dates  = hist.index

        # ── 畫布設定 ──────────────────────────────────────────
        fig, ax = plt.subplots(figsize=(width_mm / 25.4, 3.0),
                               facecolor="#F8FAFC")
        ax.set_facecolor("#F8FAFC")

        # ── 價格線 + 陰影 ─────────────────────────────────────
        ax.plot(dates, closes, color="#1E3A8A", linewidth=1.5, zorder=4)
        ax.fill_between(dates, closes, closes.min() * 0.97,
                        alpha=0.12, color="#3B82F6", zorder=3)

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
                    xytext=(-38, 8), textcoords="offset points",
                    fontsize=7, color="white", zorder=7,
                    bbox=dict(boxstyle="round,pad=0.3", fc="#1E3A8A", ec="none"),
                    arrowprops=dict(arrowstyle="-", color="#1E3A8A", lw=0.8))

        # ── 軸設定 ────────────────────────────────────────────
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.tick_params(labelsize=6.5, colors="#475569")
        for spine in ax.spines.values():
            spine.set_edgecolor("#CBD5E1")
            spine.set_linewidth(0.5)
        ax.grid(True, alpha=0.4, linewidth=0.4, color="#CBD5E1")
        ax.set_axisbelow(True)

        # ── 標題 & 圖例 ───────────────────────────────────────
        ax.set_title(f"{ticker}  —  6-Month Performance",
                     fontsize=9, color="#1E3A8A", fontweight="bold", pad=6)
        if barrier_lines:
            ax.legend(handles=barrier_lines, fontsize=6,
                      loc="upper left", framealpha=0.85,
                      edgecolor="#CBD5E1", labelcolor="#1E293B")

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

# ============================================================
# 主函數: 產生客戶投資報表 PDF
# ============================================================

def generate_customer_report(customer: dict, investments: list, prices: dict,
                             chart_period: str = "6mo") -> bytes:
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

    # ── 封面標題 ────────────────────────────────────────────
    story.append(Paragraph(
        "結構型商品投資報表",
        _style("Title", fontSize=22, fontName=FONT_BOLD, textColor=BLUE_DARK, alignment=1)
    ))
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width="100%", thickness=2, color=BLUE_DARK))
    story.append(Spacer(1, 6*mm))

    # ── 客戶資訊區 ──────────────────────────────────────────
    report_date = date.today().strftime("%Y 年 %m 月 %d 日")

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

        _add_sn_detail(story, idx, inv, sn, prices, W, chart_period)
        story.append(Spacer(1, 5*mm))

    # ── 頁尾 ────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=GRAY, spaceAfter=4))
    story.append(Paragraph(
        f"報表日期: {report_date}",
        _style("Footer", fontSize=8, textColor=GRAY, alignment=1)
    ))

    doc.build(story)
    return buffer.getvalue()


def _add_sn_detail(story, idx, inv, sn, prices, W, chart_period="6mo"):
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
    amount_usd = inv.get("amount_usd", 0) or 0

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
        f"投資金額: USD {amount_usd:,.0f}"
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

    # 商品基本資訊
    info_rows = [
        ["標的股票", ticker_names,
         "下單日期", str(trade_date)[:10] if trade_date else "—"],
        ["執行價格", f"{strike_pct*100:.2f}%" if strike_pct else "—",
         "比價日期", str(obs_date)[:10] if obs_date else "—"],
        ["配息率(年化)", f"{coupon_pct*100:.2f}%" if coupon_pct else "—",
         "KO 水位", f"{ko_barrier*100:.0f}%" if ko_barrier else "無"],
        ["投資金額", f"USD {amount_usd:,.0f}",
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

    # 各標的現價明細
    if analysis["details"]:
        price_header = ["標的股票", "期初價格", "現價", "漲跌幅", "執行價", "KO 水位", "KI 水位", "狀態"]
        price_rows = [price_header]
        for d in analysis["details"]:
            row = [
                d["ticker"],
                f"${d['initial_price']:,.2f}" if _valid(d.get("initial_price")) else "—",
                f"${d['current_price']:,.2f}" if _valid(d.get("current_price")) else "取得中",
                f"{d['change_pct']:+.2f}%" if _valid(d.get("change_pct")) else "—",
                f"${d['strike_price']:,.2f}" if _valid(d.get("strike_price")) else "—",
                f"${d['ko_price']:,.2f}" if _valid(d.get("ko_price")) else "無",
                f"${d['ki_price']:,.2f}" if _valid(d.get("ki_price")) else "無",
                _clean(f"{d['ko_status']} {d['ki_status']}"),
            ]
            price_rows.append(row)

        col_w = [22*mm, 22*mm, 22*mm, 20*mm, 22*mm, 22*mm, 22*mm, 23*mm]
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

    # ── 價格走勢圖 ──────────────────────────────────────────
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
        if chart_bytes:
            img_buf = io.BytesIO(chart_bytes)
            rl_img = RLImage(img_buf, width=W, height=W * 0.36)
            story.append(Spacer(1, 2*mm))
            story.append(rl_img)
