"""Publication-quality multi-page PDF report generator built on ReportLab.

Consumes structured column names and tabular rows only — never accesses SQLite
or executes SQL queries directly.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence
from xml.sax.saxutils import escape as xml_escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, LETTER, landscape, portrait
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .report_manager import (
    ReportHistoryManager,
    ReportMetadata,
    ReportValidationError,
    normalize_tabular_data,
    resolve_safe_report_path,
)

# ---------------------------------------------------------------------------
# Cross-platform TrueType font registration (bundled with ReportLab)
# ---------------------------------------------------------------------------

_FONTS_REGISTERED = False
_FONT_REGULAR = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"
_FONT_ITALIC = "Helvetica-Oblique"


def _ensure_fonts_registered() -> tuple[str, str, str]:
    global _FONTS_REGISTERED, _FONT_REGULAR, _FONT_BOLD, _FONT_ITALIC
    if _FONTS_REGISTERED:
        return _FONT_REGULAR, _FONT_BOLD, _FONT_ITALIC

    fonts_dir = Path(reportlab.__file__).resolve().parent / "fonts"
    vera_reg = fonts_dir / "Vera.ttf"
    vera_bd = fonts_dir / "VeraBd.ttf"
    vera_it = fonts_dir / "VeraIt.ttf"
    vera_bi = fonts_dir / "VeraBI.ttf"
    if vera_reg.is_file() and vera_bd.is_file() and vera_it.is_file():
        pdfmetrics.registerFont(TTFont("Vera", str(vera_reg)))
        pdfmetrics.registerFont(TTFont("VeraBd", str(vera_bd)))
        pdfmetrics.registerFont(TTFont("VeraIt", str(vera_it)))
        if vera_bi.is_file():
            pdfmetrics.registerFont(TTFont("VeraBI", str(vera_bi)))
        pdfmetrics.registerFontFamily(
            "Vera",
            normal="Vera",
            bold="VeraBd",
            italic="VeraIt",
            boldItalic="VeraBI" if vera_bi.is_file() else "VeraBd",
        )
        _FONT_REGULAR = "Vera"
        _FONT_BOLD = "VeraBd"
        _FONT_ITALIC = "VeraIt"

    _FONTS_REGISTERED = True
    return _FONT_REGULAR, _FONT_BOLD, _FONT_ITALIC


# ---------------------------------------------------------------------------
# Two-pass numbered canvas ("Page X of Y")
# ---------------------------------------------------------------------------


def _make_numbered_canvas(report_title: str, generated_label: str):
    font_reg, _, _ = _ensure_fonts_registered()

    class _NumberedCanvas(canvas.Canvas):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self._saved_page_states: list[dict[str, Any]] = []

        def showPage(self) -> None:  # noqa: N802 (ReportLab API)
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self) -> None:
            total_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self._draw_footer(total_pages)
                super().showPage()
            super().save()

        def _draw_footer(self, total_pages: int) -> None:
            width, _ = self._pagesize
            margin_x = 14 * mm
            footer_y = 9 * mm

            self.saveState()
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(margin_x, footer_y + 4 * mm, width - margin_x, footer_y + 4 * mm)

            self.setFont(font_reg, 7.5)
            self.setFillColor(colors.HexColor("#64748B"))
            short_title = (
                report_title[:65] + "..." if len(report_title) > 68 else report_title
            )
            self.drawString(
                margin_x,
                footer_y,
                f"Local Report SQL Agent  |  {short_title}  |  Generated {generated_label}",
            )
            self.drawRightString(
                width - margin_x,
                footer_y,
                f"Page {self._pageNumber} of {total_pages}",
            )
            self.restoreState()

    return _NumberedCanvas


# ---------------------------------------------------------------------------
# Formatting & layout helpers
# ---------------------------------------------------------------------------


def _safe_paragraph_markup(text: str) -> str:
    escaped = xml_escape(text or "")
    return escaped.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br/>")


def _format_display_value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        # Clean formatting for currency/decimal quantities while avoiding -0.0
        if value == 0.0:
            return "0.00"
        return f"{value:,.2f}" if abs(value) >= 1000 or round(value, 2) == round(value, 6) else f"{value:,.4f}"
    if isinstance(value, int):
        return str(value)
    return str(value)


def _is_numeric_column(rows: list[list[Any]], col_idx: int, sample_limit: int = 200) -> bool:
    saw_value = False
    for row in rows[:sample_limit]:
        val = row[col_idx]
        if val is None:
            continue
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            return False
        saw_value = True
    return saw_value


def _compute_column_widths(
    columns: list[str],
    rows: list[list[Any]],
    available_width: float,
) -> list[float]:
    ncols = len(columns)
    weights: list[float] = []
    sample = rows[:200]
    for idx, col in enumerate(columns):
        max_chars = max(len(col) + 2, 6)
        for row in sample:
            rendered = _format_display_value(row[idx])
            first_line = rendered.split("\n", 1)[0]
            max_chars = max(max_chars, min(len(first_line), 46))
        weights.append(float(min(max(max_chars, 6), 46)))

    total_weight = sum(weights) or float(ncols)
    min_col_w = min(26.0, available_width / max(ncols * 1.6, 1.0))
    raw_widths = [max(min_col_w, (w / total_weight) * available_width) for w in weights]
    scale = available_width / sum(raw_widths)
    return [w * scale for w in raw_widths]


# ---------------------------------------------------------------------------
# Public PDF generator
# ---------------------------------------------------------------------------


def generate_pdf_file(
    *,
    title: str,
    description: str = "",
    sql_query: str = "",
    columns: Sequence[str] | None = None,
    rows: Sequence[Sequence[Any] | Mapping[str, Any]] | None = None,
    output_dir: str | Path,
    summary: str | None = None,
    user_request: str = "",
    page_size_name: str = "A4",
    max_pdf_rows: int = 5_000,
    include_sql: bool = False,
    record_history: bool = True,
    report_spec: Any | None = None,
    charts: Sequence[Mapping[str, Any]] | None = None,
    sections: Sequence[Mapping[str, Any]] | None = None,
    datasets: Mapping[str, Any] | None = None,
    kpis: Sequence[Mapping[str, Any]] | None = None,
    findings: Sequence[str] | None = None,
) -> ReportMetadata:
    """Generate a professionally styled, paginated PDF report inside ``output_dir``."""
    clean_title = (title or "").strip()
    if not clean_title:
        raise ReportValidationError("Report title must not be empty")

    # 1. Dynamic Report Specification branch
    if report_spec is not None:
        from .dynamic_pdf_composer import compose_dynamic_pdf
        from .report_spec import ReportSpecification
        spec_obj = report_spec if isinstance(report_spec, ReportSpecification) else ReportSpecification.from_dict(report_spec)
        return compose_dynamic_pdf(spec_obj, output_dir=output_dir, record_history=record_history)

    if (charts and len(charts) > 0) or (sections and len(sections) > 0) or (datasets and len(datasets) > 1):
        from .dynamic_pdf_composer import compose_dynamic_pdf
        from .report_spec import (
            ChartConfiguration,
            ReportComponent,
            ReportSection,
            ReportSpecification,
            TableConfiguration,
        )

        all_datasets = dict(datasets or {})
        if "primary" not in all_datasets and (columns or rows):
            all_datasets["primary"] = {
                "columns": list(columns or []),
                "rows": list(rows or []),
            }

        sec_components: list[ReportComponent] = []
        if charts:
            for ch in charts:
                ch_cfg = ChartConfiguration.from_dict(ch)
                ds_id = ch_cfg.dataset_id
                if not ds_id or ds_id not in all_datasets:
                    # Match dataset by x_axis column
                    for candidate_id, cand_ds in all_datasets.items():
                        if ch_cfg.x_axis in cand_ds.get("columns", []):
                            ds_id = candidate_id
                            break
                if not ds_id:
                    ds_id = "primary" if "primary" in all_datasets else (next(iter(all_datasets.keys())) if all_datasets else None)
                ch_cfg.dataset_id = ds_id
                sec_components.append(
                    ReportComponent(
                        component_type="chart",
                        title=ch_cfg.title,
                        chart_config=ch_cfg,
                        dataset_id=ds_id,
                    )
                )

        is_matrix_req = any(k in (user_request or "").lower() for k in ["matrix", "crosstab", "totals", "total"])
        if len(all_datasets) > 1:
            for ds_name, ds_info in all_datasets.items():
                if ds_info.get("columns"):
                    sec_components.append(
                        ReportComponent(
                            component_type="table",
                            title=f"Data Summary: {ds_name.replace('_', ' ').title()}",
                            table_config=TableConfiguration(
                                columns=list(ds_info.get("columns", [])),
                                show_totals=is_matrix_req,
                                dataset_id=ds_name,
                            ),
                            dataset_id=ds_name,
                        )
                    )
        elif columns or rows:
            sec_components.append(
                ReportComponent(
                    component_type="table",
                    title="Data Summary Table",
                    table_config=TableConfiguration(columns=list(columns or []), show_totals=is_matrix_req),
                    dataset_id="primary",
                )
            )

        built_sections = [
            ReportSection(
                title="Analytical Overview",
                description=description,
                components=sec_components,
            )
        ]
        if sections:
            for s in sections:
                built_sections.append(ReportSection.from_dict(s))

        dyn_spec = ReportSpecification(
            title=clean_title,
            subtitle=description,
            executive_summary=summary or "",
            kpis=list(kpis or []),
            findings=list(findings or []),
            sections=built_sections,
            datasets=all_datasets,
            include_sql=include_sql,
            sql_queries=[{"query": sql_query, "purpose": "Report source query"}] if (sql_query and include_sql) else [],
            page_size=page_size_name,
        )
        return compose_dynamic_pdf(dyn_spec, output_dir=output_dir, record_history=record_history)

    if max_pdf_rows < 1:
        raise ReportValidationError("max_pdf_rows must be >= 1")

    columns = columns or []
    rows = rows or []
    total_input = len(rows) if isinstance(rows, (list, tuple)) else 0
    clean_cols, norm_rows, truncated = normalize_tabular_data(
        columns, rows, max_rows=max_pdf_rows
    )

    font_reg, font_bold, font_italic = _ensure_fonts_registered()
    base_size = LETTER if (page_size_name or "A4").upper() == "LETTER" else A4

    # Switch to landscape automatically when columns are wide or numerous
    estimated_char_budget = sum(max(len(c), 10) for c in clean_cols)
    use_landscape = len(clean_cols) > 6 or estimated_char_budget > 85
    pagesize = landscape(base_size) if use_landscape else portrait(base_size)

    margin_lr = 14 * mm
    margin_top = 14 * mm
    margin_bottom = 17 * mm
    available_width = pagesize[0] - 2 * margin_lr

    now = datetime.now()
    generated_str = now.strftime("%Y-%m-%d %H:%M:%S")
    output_path = resolve_safe_report_path(output_dir, clean_title, "pdf", now=now)
    tmp_path = output_path.with_suffix(".pdf.tmp")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName=font_bold,
        fontSize=17,
        leading=21,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4,
    )
    desc_style = ParagraphStyle(
        "ReportDescription",
        parent=styles["Normal"],
        fontName=font_reg,
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#334155"),
        spaceAfter=6,
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName=font_bold,
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=8,
        spaceAfter=4,
    )
    summary_body = ParagraphStyle(
        "SummaryBody",
        parent=styles["Normal"],
        fontName=font_reg,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1E293B"),
    )
    sql_style = ParagraphStyle(
        "SQLCode",
        parent=styles["Code"],
        fontName="Courier",
        fontSize=7.8,
        leading=10.5,
        textColor=colors.HexColor("#0F172A"),
        leftIndent=0,
        rightIndent=0,
    )
    header_cell_style = ParagraphStyle(
        "TableHeaderCell",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=8.0 if len(clean_cols) <= 8 else 7.2,
        leading=10,
        textColor=colors.white,
        wordWrap="CJK",
    )
    body_left_style = ParagraphStyle(
        "TableBodyLeft",
        parent=styles["Normal"],
        fontName=font_reg,
        fontSize=7.8 if len(clean_cols) <= 8 else 7.0,
        leading=9.8,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#0F172A"),
        wordWrap="CJK",
    )
    body_right_style = ParagraphStyle(
        "TableBodyRight",
        parent=body_left_style,
        alignment=TA_RIGHT,
    )
    empty_row_style = ParagraphStyle(
        "TableEmptyRow",
        parent=styles["Normal"],
        fontName=font_italic,
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#64748B"),
    )

    story: list[Any] = []

    # 1. Title & Accent Rule
    story.append(Paragraph(_safe_paragraph_markup(clean_title), title_style))
    if (description or "").strip():
        story.append(Paragraph(_safe_paragraph_markup(description.strip()), desc_style))
    story.append(
        HRFlowable(
            width="100%",
            thickness=1.5,
            color=colors.HexColor("#2563EB"),
            spaceBefore=2,
            spaceAfter=6,
        )
    )

    # 2. Metadata KPI strip
    meta_cells = [
        [
            Paragraph(
                f"<b>Generated:</b> {xml_escape(generated_str)}", summary_body
            ),
            Paragraph(
                f"<b>Records:</b> {len(norm_rows):,}"
                + (f" (of {total_input:,})" if truncated else ""),
                summary_body,
            ),
            Paragraph(f"<b>Columns:</b> {len(clean_cols)}", summary_body),
            Paragraph(
                f"<b>Layout:</b> {'Landscape' if use_landscape else 'Portrait'} {page_size_name.upper()}",
                summary_body,
            ),
        ]
    ]
    kpi_table = Table(
        meta_cells,
        colWidths=[
            available_width * 0.34,
            available_width * 0.24,
            available_width * 0.18,
            available_width * 0.24,
        ],
    )
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFDBFE")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(kpi_table)
    story.append(Spacer(1, 5))

    # 3. Summary section
    story.append(Paragraph("Report Summary", section_heading))
    effective_summary = (summary or "").strip()
    if not effective_summary:
        effective_summary = (
            f"This report contains {len(norm_rows):,} record(s) across "
            f"{len(clean_cols)} column(s): {', '.join(clean_cols)}."
        )
    if truncated:
        effective_summary += (
            f"\nNote: Output table was capped at {max_pdf_rows:,} rows "
            f"(from {total_input:,} supplied rows) for PDF readability."
        )
    story.append(Paragraph(_safe_paragraph_markup(effective_summary), summary_body))

    # 4. SQL Query block
    clean_sql = (sql_query or "").strip()
    if include_sql and clean_sql:
        story.append(Paragraph("Appendix: SQL Queries", section_heading))
        sql_box = Table(
            [[Paragraph(_safe_paragraph_markup(clean_sql), sql_style)]],
            colWidths=[available_width],
        )
        sql_box.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(sql_box)

    # 5. Results Data Table
    story.append(Paragraph("Query Results", section_heading))
    col_widths = _compute_column_widths(clean_cols, norm_rows, available_width)
    numeric_flags = [_is_numeric_column(norm_rows, i) for i in range(len(clean_cols))]

    header_row = [
        Paragraph(_safe_paragraph_markup(col_name), header_cell_style)
        for col_name in clean_cols
    ]
    table_data: list[list[Any]] = [header_row]

    if norm_rows:
        for row in norm_rows:
            rendered_cells: list[Paragraph] = []
            for idx, val in enumerate(row):
                cell_style = body_right_style if numeric_flags[idx] else body_left_style
                rendered_cells.append(
                    Paragraph(
                        _safe_paragraph_markup(_format_display_value(val)),
                        cell_style,
                    )
                )
            table_data.append(rendered_cells)
    else:
        empty_cells: list[Any] = [
            Paragraph("No matching records returned (0 rows).", empty_row_style)
        ] + ["" for _ in range(len(clean_cols) - 1)]
        table_data.append(empty_cells)

    data_table = LongTable(
        table_data,
        colWidths=col_widths,
        repeatRows=1,
        splitByRow=1,
    )
    table_cmds: list[tuple[Any, ...]] = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
        ("TOPPADDING", (0, 1), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E2E8F0")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#94A3B8")),
    ]
    if norm_rows:
        table_cmds.append(
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.white, colors.HexColor("#F8FAFC")],
            )
        )
    elif len(clean_cols) > 1:
        table_cmds.append(("SPAN", (0, 1), (-1, 1)))
        table_cmds.append(("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F8FAFC")))

    data_table.setStyle(TableStyle(table_cmds))
    story.append(data_table)

    try:
        doc = SimpleDocTemplate(
            str(tmp_path),
            pagesize=pagesize,
            leftMargin=margin_lr,
            rightMargin=margin_lr,
            topMargin=margin_top,
            bottomMargin=margin_bottom,
            title=clean_title,
            author="Local Report SQL Agent",
        )
        doc.build(
            story,
            canvasmaker=_make_numbered_canvas(clean_title, generated_str),
        )
        tmp_path.replace(output_path)
    except BaseException:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise

    size_bytes = output_path.stat().st_size
    metadata = ReportMetadata(
        report_id=uuid.uuid4().hex,
        title=clean_title,
        description=(description or "").strip(),
        user_request=(user_request or description or clean_title).strip(),
        sql_query=clean_sql,
        output_format="PDF",
        file_name=output_path.name,
        output_path=str(output_path),
        record_count=len(norm_rows),
        total_input_records=total_input,
        truncated=truncated,
        column_names=clean_cols,
        file_size_bytes=size_bytes,
        created_at=now.isoformat(timespec="seconds"),
        status="completed",
    )

    if record_history:
        ReportHistoryManager(output_dir).record(metadata)

    return metadata

