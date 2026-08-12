"""Render a Data Quality Report to markdown (chat), TXT and PDF (export).

The PDF uses ReportLab Platypus to produce a professional, reusable layout:
headings, a summary table, per-section finding tables with status colours and
actionable recommendations. The TXT export mirrors the exact report content.
"""
from io import BytesIO

from app.schemas.quality import QualityReport, QualityStatus

STATUS_ICON = {
    QualityStatus.PASSED: "✓",
    QualityStatus.WARNING: "⚠",
    QualityStatus.FAILED: "✗",
    QualityStatus.NOT_EVALUATED: "–",
}

STATUS_LABEL = {
    QualityStatus.PASSED: "PASSED",
    QualityStatus.WARNING: "WARNING",
    QualityStatus.FAILED: "FAILED",
    QualityStatus.NOT_EVALUATED: "NOT EVALUATED",
}


def _rating_of(score: int) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Fair"
    return "Poor"


# Profiling sub-sections that roll up under the single "Profiling" category in
# the executive summary so the default response stays on one screen.
_PROFILING_SECTION_KEYS = {
    "completeness", "uniqueness", "validity", "consistency", "freshness",
}

_GROUP_LABELS = (
    ("Metadata", ("metadata",)),
    ("Schema", ("schema",)),
    ("Profiling", tuple(_PROFILING_SECTION_KEYS)),
    ("Lineage", ("lineage",)),
)


def _group_sections(report: QualityReport) -> list[tuple[str, list]]:
    """Roll report sections into the four summary categories."""
    groups: list[tuple[str, list]] = []
    for label, keys in _GROUP_LABELS:
        sections = [s for s in report.sections if s.key in keys]
        if sections:
            groups.append((label, sections))
    return groups


def _worst_status(sections: list) -> QualityStatus:
    order = {
        QualityStatus.FAILED: 3,
        QualityStatus.WARNING: 2,
        QualityStatus.NOT_EVALUATED: 1,
        QualityStatus.PASSED: 0,
    }
    return max((s.status for s in sections), key=lambda st: order.get(st, 0))


def _issue_count(sections: list) -> int:
    return sum(
        1 for s in sections for f in s.findings
        if f.status in (QualityStatus.FAILED, QualityStatus.WARNING)
    )


def render_summary_markdown(report: QualityReport) -> str:
    """Compact executive summary (default chat answer body).

    Shows only: dataset, overall score/rating, a one-line summary per major
    category, the top issues, and the top recommendations. The complete audit
    stays available through the collapsible "View Full Report" UI or a
    follow-up question asking for the full report.
    """
    lines: list[str] = []
    lines.append(f"# 📊 Data Quality Report: {report.dataset}")
    lines.append("")
    lines.append(f"**{report.overall_score}/100 — {report.rating}**"
                 + (f" · tạo bởi {report.generated_by}" if report.generated_by else ""))
    lines.append("")

    # Category roll-up (no repeated findings, just the outcome per category).
    lines.append("**Tổng quan từng khía cạnh:**")
    for label, sections in _group_sections(report):
        worst = _worst_status(sections)
        issues = _issue_count(sections)
        if worst == QualityStatus.NOT_EVALUATED:
            summary = "Chưa đánh giá (thiếu dữ liệu)"
        elif issues == 0:
            summary = "Đạt"
        else:
            summary = f"{issues} vấn đề"
        lines.append(f"- **{label}**: {summary} ({STATUS_LABEL[worst]})")
    if not report.profiling_available and report.not_evaluated_checks:
        lines.append("  *Profiling metrics unavailable*")
    lines.append("")

    # Top issues across all sections (failed first, then warnings), capped.
    issues: list = []
    for s in report.sections:
        for f in s.findings:
            if f.status in (QualityStatus.FAILED, QualityStatus.WARNING):
                issues.append((f.status == QualityStatus.FAILED, s.title, f))
    issues.sort(key=lambda t: (not t[0], t[2].name))
    top_issues = issues[:5]
    if top_issues:
        lines.append(f"**Vấn đề quan trọng ({len(issues)}):**")
        for is_failed, _sec, f in top_issues:
            marker = "✗" if is_failed else "⚠"
            value = f" [{f.value}]" if f.value else ""
            lines.append(f"- {marker} **{f.name}**{value} — {f.detail}")
        lines.append("")
    else:
        lines.append("**Vấn đề quan trọng:** Không có vấn đề đáng chú ý.")
        lines.append("")

    # Top recommendations (already deduped upstream; high priority first).
    prio = {"high": 0, "medium": 1, "low": 2}
    recs = sorted(report.recommendations, key=lambda r: prio.get(r.priority, 1))[:5]
    if recs:
        lines.append(f"**Khuyến nghị hàng đầu ({len(report.recommendations)}):**")
        for r in recs:
            lines.append(f"- [{r.priority.upper()}] {r.text}")
        lines.append("")

    lines.append("> Chi tiết đầy đủ từng mục kiểm tra có trong **View Full Report** "
                 "hoặc hỏi *\"xem báo cáo đầy đủ\"*.")
    return "\n".join(lines).strip()


def render_markdown(report: QualityReport) -> str:
    """Full report as a markdown table (shown when the user asks for the complete audit)."""
    lines: list[str] = []
    lines.append(f"# 📊 Data Quality Report: {report.dataset}")
    lines.append("")
    lines.append(
        f"**{report.overall_score}/100 — {report.rating}** · "
        f"Profiling: {'có' if report.profiling_available else 'không có'}"
        + (f" · tạo bởi {report.generated_by}" if report.generated_by else "")
        + (f" · {report.generated_at}" if report.generated_at else "")
    )
    lines.append("")
    lines.append("| Section | Score | Status | Checks |")
    lines.append("|---|---|---|---|")
    for section in report.sections:
        checks = "; ".join(
            f"{STATUS_ICON[f.status]} {f.name}"
            + (f" ({f.value})" if f.value else "")
            for f in section.findings
        ) or "—"
        lines.append(
            f"| {section.title} | {section.score}/100 | "
            f"{STATUS_LABEL[section.status]} | {checks} |"
        )
    lines.append("")
    if report.recommendations:
        lines.append("**Recommendations**")
        for r in report.recommendations:
            lines.append(f"- [{r.priority.upper()}] {r.text}")
        lines.append("")
    if report.not_evaluated_checks:
        lines.append("**Not evaluated (thiếu dữ liệu profiling):**")
        lines.append("· ".join(report.not_evaluated_checks))
    return "\n".join(lines).strip()


def render_txt(report: QualityReport) -> str:
    """Clean plain-text export mirroring the displayed report."""
    sep = "=" * 72
    sub = "-" * 72
    out: list[str] = []
    out.append(sep)
    out.append("DATA QUALITY REPORT".center(72))
    out.append(sep)
    out.append(f"Dataset          : {report.dataset}")
    out.append(f"Overall score    : {report.overall_score}/100")
    out.append(f"Rating           : {report.rating}")
    out.append(f"Profiling data   : {'available' if report.profiling_available else 'unavailable'}")
    out.append(f"Generated at     : {report.generated_at}")
    out.append(f"Generated by     : {report.generated_by or '-'}")
    out.append(sep)
    for section in report.sections:
        out.append("")
        out.append(f"[{STATUS_LABEL[section.status]}] {section.title} "
                   f"({section.score}/100)")
        out.append(sub)
        for f in section.findings:
            icon = STATUS_ICON[f.status]
            value = f" [{f.value}]" if f.value else ""
            out.append(f"  {icon} {f.name}{value}")
            out.append(f"     {f.detail}")
    if report.recommendations:
        out.append("")
        out.append("RECOMMENDATIONS")
        out.append(sub)
        for r in report.recommendations:
            out.append(f"  [{r.priority.upper()}] {r.text}")
    if report.not_evaluated_checks:
        out.append("")
        out.append("NOT EVALUATED (missing profiling data)")
        out.append(sub)
        for c in report.not_evaluated_checks:
            out.append(f"  - {c}")
    out.append("")
    out.append(sep)
    out.append(f"Generated by DataAtlas AI at {report.generated_at}"
               + (f" for {report.generated_by}" if report.generated_by else ""))
    out.append(sep)
    return "\n".join(out)


def render_pdf_bytes(report: QualityReport) -> bytes:
    """Professionally formatted PDF export built with ReportLab Platypus."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    color_for = {
        QualityStatus.PASSED: colors.HexColor("#166534"),
        QualityStatus.WARNING: colors.HexColor("#92400e"),
        QualityStatus.FAILED: colors.HexColor("#991b1b"),
        QualityStatus.NOT_EVALUATED: colors.HexColor("#6b7280"),
    }
    bg_for = {
        QualityStatus.PASSED: colors.HexColor("#dcfce7"),
        QualityStatus.WARNING: colors.HexColor("#fef3c7"),
        QualityStatus.FAILED: colors.HexColor("#fee2e2"),
        QualityStatus.NOT_EVALUATED: colors.HexColor("#f3f4f6"),
    }

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("TitleX", parent=styles["Title"], fontSize=20, spaceAfter=2)
    h2 = ParagraphStyle("SecX", parent=styles["Heading2"], fontSize=13,
                        spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#1f2937"))
    meta = ParagraphStyle("MetaX", parent=styles["Normal"], fontSize=10,
                          textColor=colors.HexColor("#374151"))
    cell = ParagraphStyle("CellX", parent=styles["Normal"], fontSize=9, leading=11)
    note = ParagraphStyle("NoteX", parent=styles["Italic"], fontSize=9,
                          textColor=colors.HexColor("#6b7280"))
    rec = ParagraphStyle("RecX", parent=styles["Normal"], fontSize=10, spaceAfter=2)

    story: list = []

    story.append(Paragraph("Data Quality Report", h1))
    story.append(Paragraph(report.dataset, ParagraphStyle(
        "SubX", parent=styles["Heading3"], fontSize=13,
        textColor=colors.HexColor("#2563eb"), spaceAfter=8)))

    summary = Table(
        [
            ["Overall Score", f"{report.overall_score}/100",
             "Rating", report.rating],
            ["Profiling data", "Available" if report.profiling_available else "Unavailable",
             "Generated at", report.generated_at],
            ["Generated by", report.generated_by or "-", "", ""],
        ],
        colWidths=[28 * mm, 40 * mm, 28 * mm, 40 * mm],
    )
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary)
    story.append(Spacer(1, 6))

    for section in report.sections:
        story.append(Paragraph(
            f"{section.title}  —  {section.score}/100  ({STATUS_LABEL[section.status]})", h2))
        if section.findings:
            rows = [
                [Paragraph("<b>Status</b>", cell), Paragraph("<b>Check</b>", cell),
                 Paragraph("<b>Value</b>", cell), Paragraph("<b>Finding</b>", cell)],
            ]
            for f in section.findings:
                status_cell = Paragraph(
                    f'<font color="{color_for[f.status].hexval()}"><b>'
                    f'{STATUS_LABEL[f.status]}</b></font>', cell)
                rows.append([
                    status_cell,
                    Paragraph(f.name, cell),
                    Paragraph(f.value or "-", cell),
                    Paragraph(f.detail, cell),
                ])
            t = Table(rows, colWidths=[24 * mm, 44 * mm, 32 * mm, 56 * mm], repeatRows=1)
            style = [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
            for i, f in enumerate(section.findings, start=1):
                style.append(("BACKGROUND", (0, i), (0, i), bg_for[f.status]))
            t.setStyle(TableStyle(style))
            story.append(t)
        else:
            story.append(Paragraph("No findings recorded for this section.", meta))
        story.append(Spacer(1, 4))

    if report.recommendations:
        story.append(Paragraph("Recommendations", h2))
        for r in report.recommendations:
            story.append(Paragraph(f"• <b>[{r.priority.upper()}]</b> {r.text}", rec))
    if report.not_evaluated_checks:
        story.append(Spacer(1, 4))
        story.append(Paragraph("Not evaluated (missing profiling data)", h2))
        for c in report.not_evaluated_checks:
            story.append(Paragraph(f"• {c}", note))

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        f"Generated by DataAtlas AI on {report.generated_at}"
        + (f" for {report.generated_by}" if report.generated_by else ""),
        ParagraphStyle("Foot", parent=styles["Normal"], fontSize=8,
                       alignment=TA_CENTER, textColor=colors.HexColor("#9ca3af"))))

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=16 * mm, leftMargin=16 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm,
                            title=f"Data Quality Report - {report.dataset}")
    doc.build(story)
    return buffer.getvalue()
