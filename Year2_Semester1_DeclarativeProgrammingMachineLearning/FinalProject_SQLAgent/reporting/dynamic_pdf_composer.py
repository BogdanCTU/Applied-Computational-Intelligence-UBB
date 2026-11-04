"""Dynamic multi-component PDF report composer supporting charts, tables, KPIs, and findings."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, LETTER, landscape, portrait
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .chart_builder import _format_val, _safe_float, build_chart
from .pdf_generator import _compute_column_widths, _ensure_fonts_registered, _format_display_value, _is_numeric_column, _make_numbered_canvas
from .report_manager import ReportMetadata, resolve_safe_report_path
from .report_spec import ChartConfiguration, ReportComponent, ReportSection, ReportSpecification, TableConfiguration

log = logging.getLogger(__name__)


def _safe_markup(text: str) -> str:
    """Escape text for ReportLab Platypus Paragraphs while keeping safe inline formatting."""
    if not text:
        return ""
    # Basic protection
    s = xml_escape(str(text))
    # Allow simple safe tags if originally present
    s = s.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
    s = s.replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
    s = s.replace("&lt;code&gt;", "<font face='Courier'>").replace("&lt;/code&gt;", "</font>")
    return s.replace("\n", "<br/>")


def compose_dynamic_pdf(
    spec: ReportSpecification,
    output_dir: str | Path,
    *,
    record_history: bool = True,
) -> ReportMetadata:
    """Render a dynamic, publication-grade multi-page PDF from a ReportSpecification."""
    font_reg, font_bold, font_italic = _ensure_fonts_registered()
    base_size = LETTER if (spec.page_size or "A4").upper() == "LETTER" else A4

    # Default to portrait, use landscape if any table has > 6 columns
    max_cols = 0
    for s in spec.sections:
        for c in s.components:
            if c.component_type == "table":
                t_cols = c.table_config.columns if c.table_config else []
                max_cols = max(max_cols, len(t_cols))
    for ds in spec.datasets.values():
        max_cols = max(max_cols, len(ds.get("columns", [])))

    use_landscape = max_cols > 6
    pagesize = landscape(base_size) if use_landscape else portrait(base_size)

    margin_lr = 14 * mm
    margin_top = 14 * mm
    margin_bottom = 17 * mm
    available_width = pagesize[0] - 2 * margin_lr

    now = datetime.now()
    generated_str = now.strftime("%Y-%m-%d %H:%M:%S")
    output_path = resolve_safe_report_path(output_dir, spec.title, "pdf", now=now)
    tmp_path = output_path.with_suffix(".pdf.tmp")

    # Typography styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName=font_bold,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=3,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName=font_reg,
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#475569"),
        spaceAfter=8,
    )
    section_title_style = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontName=font_bold,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=12,
        spaceAfter=4,
    )
    component_title_style = ParagraphStyle(
        "ComponentTitle",
        parent=styles["Heading3"],
        fontName=font_bold,
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#334155"),
        spaceBefore=6,
        spaceAfter=3,
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName=font_reg,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1E293B"),
    )
    finding_item_style = ParagraphStyle(
        "FindingItem",
        parent=styles["Normal"],
        fontName=font_reg,
        fontSize=8.8,
        leading=12.5,
        textColor=colors.HexColor("#0F172A"),
    )
    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=7.8,
        leading=10,
        textColor=colors.HexColor("#FFFFFF"),
    )
    table_cell_left = ParagraphStyle(
        "TableCellL",
        parent=styles["Normal"],
        fontName=font_reg,
        fontSize=7.6,
        leading=10,
        textColor=colors.HexColor("#1E293B"),
    )
    table_cell_right = ParagraphStyle(
        "TableCellR",
        parent=table_cell_left,
        alignment=TA_RIGHT,
    )
    sql_code_style = ParagraphStyle(
        "SQLAppendixCode",
        parent=styles["Code"],
        fontName="Courier",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#0F172A"),
    )

    story: list[Any] = []

    # 1. Document Title & Subtitle
    story.append(Paragraph(_safe_markup(spec.title), title_style))
    if spec.subtitle:
        story.append(Paragraph(_safe_markup(spec.subtitle), subtitle_style))

    # Meta Banner (Timestamp, Mode)
    meta_bar = Table(
        [
            [
                Paragraph(f"<b>Generated:</b> {generated_str}", body_style),
                Paragraph(f"<b>Database:</b> ecommerce.db (Local)", body_style),
                Paragraph(f"<b>Layout:</b> {'Landscape' if use_landscape else 'Portrait'} {spec.page_size.upper()}", body_style),
            ]
        ],
        colWidths=[available_width * 0.35, available_width * 0.35, available_width * 0.30],
    )
    meta_bar.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(meta_bar)
    story.append(Spacer(1, 8))

    # 2. Executive Summary
    if spec.executive_summary:
        story.append(Paragraph("Executive Summary", section_title_style))
        story.append(Paragraph(_safe_markup(spec.executive_summary), body_style))
        story.append(Spacer(1, 6))

    # 3. Key Performance Indicators (KPI Cards Grid)
    if spec.kpis:
        kpi_cells: list[list[Any]] = []
        card_row: list[Any] = []
        num_kpis = len(spec.kpis)
        cols_per_row = min(4, num_kpis)
        card_w = available_width / cols_per_row

        for k in spec.kpis:
            lbl = _safe_markup(str(k.get("label", "Metric")))
            val = _safe_markup(str(k.get("value", "—")))
            sub = _safe_markup(str(k.get("note", k.get("change", ""))))
            card_content = (
                f"<font size='8' color='#64748B'>{lbl}</font><br/>"
                f"<font size='13' color='#1E3A8A'><b>{val}</b></font>"
            )
            if sub:
                card_content += f"<br/><font size='7.5' color='#10B981'>{sub}</font>"

            card_row.append(Paragraph(card_content, body_style))
            if len(card_row) == cols_per_row:
                kpi_cells.append(card_row)
                card_row = []

        if card_row:
            while len(card_row) < cols_per_row:
                card_row.append("")
            kpi_cells.append(card_row)

        kpi_table = Table(kpi_cells, colWidths=[card_w] * cols_per_row)
        kpi_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFDBFE")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DBEAFE")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(kpi_table)
        story.append(Spacer(1, 8))

    # 4. Highlighted Findings Callout Box
    if spec.findings:
        findings_paragraphs = [Paragraph(f"• {_safe_markup(f)}", finding_item_style) for f in spec.findings]
        findings_box = Table(
            [[Paragraph("<b>Key Analytical Findings:</b>", component_title_style)]] + [[p] for p in findings_paragraphs],
            colWidths=[available_width],
        )
        findings_box.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#86EFAC")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(findings_box)
        story.append(Spacer(1, 8))

    # 5. Dynamic Sections & Components
    sections_count = len(spec.sections)
    charts_requested = 0
    charts_rendered = 0
    tables_requested = 0
    tables_rendered = 0
    failed_components: list[dict[str, Any]] = []
    warnings: list[str] = []

    datasets_count = len(spec.datasets)
    dataset_details: dict[str, int] = {
        ds_id: len(ds.get("rows", [])) for ds_id, ds in spec.datasets.items()
    }

    for sec_idx, section in enumerate(spec.sections, start=1):
        story.append(Paragraph(f"{sec_idx}. {_safe_markup(section.title)}", section_title_style))
        if section.description:
            story.append(Paragraph(_safe_markup(section.description), body_style))
            story.append(Spacer(1, 4))

        for comp in section.components:
            if comp.title:
                story.append(Paragraph(_safe_markup(comp.title), component_title_style))
            if comp.description:
                story.append(Paragraph(_safe_markup(comp.description), body_style))
                story.append(Spacer(1, 3))

            # Resolve dataset for component
            ds_data: dict[str, Any] = {}
            if comp.dataset_id and comp.dataset_id in spec.datasets:
                ds_data = spec.datasets[comp.dataset_id]
            elif spec.datasets:
                # Default to first available dataset
                ds_data = next(iter(spec.datasets.values()))

            cols = ds_data.get("columns", [])
            rows = ds_data.get("rows", [])

            # Render Component by Type
            if comp.component_type == "chart":
                charts_requested += 1
                try:
                    if comp.chart_config:
                        cfg = comp.chart_config
                        cfg.width = available_width
                        chart_drawing = build_chart(cfg, cols, rows)
                        story.append(chart_drawing)
                        story.append(Spacer(1, 8))
                        charts_rendered += 1
                    else:
                        failed_components.append({"type": "chart", "title": comp.title, "error": "Missing chart configuration"})
                        warnings.append(f"Chart '{comp.title}' missing configuration.")
                except Exception as e:
                    failed_components.append({"type": "chart", "title": comp.title, "error": str(e)})
                    warnings.append(f"Failed to render chart '{comp.title}': {e}")

            elif comp.component_type == "table":
                tables_requested += 1
                try:
                    t_cfg = comp.table_config or TableConfiguration()
                    tbl_flowable = _build_table_flowable(
                        t_cfg,
                        cols,
                        rows,
                        available_width,
                        table_header_style,
                        table_cell_left,
                        table_cell_right,
                    )
                    story.append(tbl_flowable)
                    story.append(Spacer(1, 8))
                    tables_rendered += 1
                except Exception as e:
                    failed_components.append({"type": "table", "title": comp.title, "error": str(e)})
                    warnings.append(f"Failed to render table '{comp.title}': {e}")

            elif comp.component_type == "text" and comp.content:
                story.append(Paragraph(_safe_markup(str(comp.content)), body_style))
                story.append(Spacer(1, 6))

    # 6. APPENDIX: SQL QUERIES (PHASE 4: INCLUDED ONLY WHEN EXPLICITLY REQUESTED)
    if spec.include_sql and spec.sql_queries:
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceAfter=8))
        story.append(Paragraph("Appendix: Executed SQL Queries", section_title_style))
        story.append(
            Paragraph(
                "<i>This appendix was included per explicit user request. The following read-only SQL queries were executed to generate the report data:</i>",
                body_style,
            )
        )
        story.append(Spacer(1, 4))

        for idx, sq in enumerate(spec.sql_queries, start=1):
            q_text = sq.get("query", sq.get("sql", ""))
            q_purpose = sq.get("purpose", sq.get("explanation", f"Query {idx}"))
            story.append(Paragraph(f"<b>Query {idx}:</b> {_safe_markup(q_purpose)}", component_title_style))
            sql_box = Table(
                [[Paragraph(_safe_markup(q_text), sql_code_style)]],
                colWidths=[available_width],
            )
            sql_box.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("LEFTPADDING", (0, 0), (-1, -1), 7),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ]
                )
            )
            story.append(sql_box)
            story.append(Spacer(1, 6))

    # Build Document Template
    doc = SimpleDocTemplate(
        str(tmp_path),
        pagesize=pagesize,
        leftMargin=margin_lr,
        rightMargin=margin_lr,
        topMargin=margin_top,
        bottomMargin=margin_bottom,
    )

    NumberedCanvas = _make_numbered_canvas(spec.title, generated_str)
    page_counter = {"count": 1}

    class CountingCanvas(NumberedCanvas):  # type: ignore[valid-type, misc]
        def save(self) -> None:
            page_counter["count"] = max(1, len(self._saved_page_states))
            super().save()

    doc.build(story, canvasmaker=CountingCanvas)
    page_count = page_counter["count"]

    # Atomic move
    tmp_path.replace(output_path)
    file_size = output_path.stat().st_size

    total_records = sum(len(d.get("rows", [])) for d in spec.datasets.values())
    primary_cols = next(iter(spec.datasets.values())).get("columns", []) if spec.datasets else []

    completion_status = "complete" if not failed_components else ("partial" if (charts_rendered > 0 or tables_rendered > 0) else "failed")

    metadata = ReportMetadata(
        report_id=str(uuid.uuid4())[:8],
        title=spec.title,
        description=spec.subtitle or spec.executive_summary or spec.title,
        user_request=spec.title,
        sql_query=spec.sql_queries[0].get("query", "") if spec.sql_queries else "",
        output_format="PDF",
        file_name=output_path.name,
        output_path=str(output_path),
        record_count=total_records,
        total_input_records=total_records,
        truncated=False,
        column_names=primary_cols,
        file_size_bytes=file_size,
        created_at=generated_str,
        status="completed",
        page_count=page_count,
        sections_count=sections_count,
        charts_requested=charts_requested,
        charts_rendered=charts_rendered,
        tables_requested=tables_requested,
        tables_rendered=tables_rendered,
        datasets_count=datasets_count,
        dataset_details=dataset_details,
        failed_components=failed_components,
        completion_status=completion_status,
        warnings=warnings,
    )

    if record_history:
        from .report_manager import ReportHistoryManager

        ReportHistoryManager(output_dir).record(metadata)

    return metadata


def _build_table_flowable(
    config: TableConfiguration,
    columns: Sequence[str],
    rows: Sequence[Sequence[Any] | Mapping[str, Any]],
    available_width: float,
    header_style: ParagraphStyle,
    cell_left_style: ParagraphStyle,
    cell_right_style: ParagraphStyle,
) -> Any:
    """Build a paginated LongTable with repeated headers across page breaks."""
    display_cols = config.columns if config.columns else list(columns)
    if not display_cols:
        return Paragraph("<i>(Empty table configuration)</i>", cell_left_style)

    # Normalize rows
    dict_rows: list[dict[str, Any]] = []
    if rows:
        if isinstance(rows[0], dict):
            dict_rows = [dict(r) for r in rows]  # type: ignore[arg-type]
        else:
            dict_rows = [dict(zip(columns, r)) for r in rows]  # type: ignore[arg-type]

    if config.limit and len(dict_rows) > config.limit:
        dict_rows = dict_rows[:config.limit]

    # Optional sorting
    if config.sort_by and dict_rows and config.sort_by in dict_rows[0]:
        dict_rows.sort(
            key=lambda r: (r.get(config.sort_by) is None, r.get(config.sort_by) or 0)
        )

    # Numeric alignment
    numeric_flags = []
    for c in display_cols:
        sample_vals = [r.get(c) for r in dict_rows[:10]]
        is_num = all(isinstance(v, (int, float)) or (v is None) for v in sample_vals) if sample_vals else False
        numeric_flags.append(is_num)

    # Row totals for matrix/crosstab or when show_totals is True with >=2 numeric columns
    add_row_total = config.show_totals and sum(numeric_flags) >= 2 and "Total" not in [c.title() for c in display_cols]
    if add_row_total:
        orig_cols = list(display_cols)
        orig_num = list(numeric_flags)
        display_cols = orig_cols + ["Total"]
        numeric_flags = orig_num + [True]
        for r in dict_rows:
            r["Total"] = sum(_safe_float(r.get(c), 0.0) for idx, c in enumerate(orig_cols) if orig_num[idx])

    # Summary row for column totals
    total_row_idx = -1
    if config.show_totals and dict_rows:
        total_row: dict[str, Any] = {}
        for idx, c in enumerate(display_cols):
            if idx == 0:
                total_row[c] = "Total"
            elif numeric_flags[idx]:
                total_row[c] = sum(_safe_float(r.get(c), 0.0) for r in dict_rows)
            else:
                total_row[c] = ""
        dict_rows.append(total_row)
        total_row_idx = len(dict_rows)

    col_widths = _compute_column_widths(display_cols, [[r.get(c) for c in display_cols] for r in dict_rows], available_width)

    header_cells = [Paragraph(_safe_markup(c.replace("_", " ").title()), header_style) for c in display_cols]
    table_data: list[list[Any]] = [header_cells]

    if dict_rows:
        for r_idx, r in enumerate(dict_rows, start=1):
            row_cells: list[Paragraph] = []
            is_tot_row = (config.show_totals and r_idx == len(dict_rows))
            for idx, c in enumerate(display_cols):
                style = cell_right_style if numeric_flags[idx] else cell_left_style
                val = r.get(c)
                fmt = config.formatting.get(c, "")
                if fmt:
                    val_str = _format_val(val, fmt)
                else:
                    val_str = _format_display_value(val)
                if is_tot_row or (add_row_total and idx == len(display_cols) - 1):
                    val_str = f"<b>{val_str}</b>"
                row_cells.append(Paragraph(_safe_markup(val_str), style))
            table_data.append(row_cells)
    else:
        table_data.append([Paragraph("No records found.", cell_left_style)] + ["" for _ in range(len(display_cols) - 1)])

    table_cmds: list[tuple[Any, ...]] = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
        ("TOPPADDING", (0, 0), (-1, 0), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
    ]

    if config.show_totals and total_row_idx > 0:
        table_cmds.append(("BACKGROUND", (0, total_row_idx), (-1, total_row_idx), colors.HexColor("#E2E8F0")))
        table_cmds.append(("FONTNAME", (0, total_row_idx), (-1, total_row_idx), "Helvetica-Bold"))
        table_cmds.append(("LINEABOVE", (0, total_row_idx), (-1, total_row_idx), 1.0, colors.HexColor("#64748B")))

    if add_row_total:
        table_cmds.append(("FONTNAME", (-1, 1), (-1, -1), "Helvetica-Bold"))
        table_cmds.append(("BACKGROUND", (-1, 1), (-1, -1), colors.HexColor("#F1F5F9")))

    # LongTable supports clean multi-page pagination with repeatRows=1
    tbl = LongTable(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle(table_cmds))
    return tbl
