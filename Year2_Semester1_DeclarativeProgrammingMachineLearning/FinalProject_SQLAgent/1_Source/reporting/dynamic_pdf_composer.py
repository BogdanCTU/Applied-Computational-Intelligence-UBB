"""Dynamic multi-component PDF report composer supporting charts, tables, KPIs, and findings."""

from __future__ import annotations

import logging
import re
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
    story.append(Spacer(1, 6))

    # 1b. Reporting Period & Data Availability Banner (when period metadata is specified)
    if spec.requested_period or spec.historical_comparison_period or spec.available_data_range:
        req_lbl = _safe_markup(spec.requested_period or "All Available Data")
        bounds_str = ""
        if spec.period_boundaries.get("interval"):
            bounds_str = f" {_safe_markup(spec.period_boundaries['interval'])}"
        status_badge = (
            "<font color='#DC2626'><b>No Records (0 rows)</b></font>"
            if (spec.requested_period and not spec.requested_period_has_data)
            else "<font color='#15803D'><b>Verified Data</b></font>"
        )
        comp_lbl = _safe_markup(spec.historical_comparison_period or "None")
        avail_min = _safe_markup(str(spec.available_data_range.get("min_date", "") or "N/A"))
        avail_max = _safe_markup(str(spec.available_data_range.get("max_date", "") or "N/A"))
        avail_str = f"{avail_min} to {avail_max}" if (avail_min != "N/A" or avail_max != "N/A") else "Full Ledger"

        period_bar = Table(
            [
                [
                    Paragraph(f"<b>Requested Period:</b> {req_lbl}{bounds_str} ({status_badge})", body_style),
                    Paragraph(f"<b>Comparison Period:</b> {comp_lbl}", body_style),
                    Paragraph(f"<b>DB Date Range:</b> {avail_str}", body_style),
                ]
            ],
            colWidths=[available_width * 0.42, available_width * 0.28, available_width * 0.30],
        )
        period_bar.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        colors.HexColor("#FEF2F2")
                        if (spec.requested_period and not spec.requested_period_has_data)
                        else colors.HexColor("#F1F5F9"),
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor("#FECACA")
                        if (spec.requested_period and not spec.requested_period_has_data)
                        else colors.HexColor("#CBD5E1"),
                    ),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(period_bar)
        story.append(Spacer(1, 8))

    # 2. Executive Summary
    if spec.executive_summary:
        story.append(Paragraph("Executive Summary", section_title_style))
        story.append(Paragraph(_safe_markup(spec.executive_summary), body_style))
        story.append(Spacer(1, 6))

    # Helper to build a KPI card grid table
    def _build_kpi_grid(
        kpi_list: list[dict[str, Any]],
        bg_hex: str = "#EFF6FF",
        border_hex: str = "#BFDBFE",
        grid_hex: str = "#DBEAFE",
        val_hex: str = "#1E3A8A",
    ) -> Table:
        kpi_cells: list[list[Any]] = []
        card_row: list[Any] = []
        num_kpis = len(kpi_list)
        cols_per_row = min(4, max(1, num_kpis))
        card_w = available_width / cols_per_row

        for raw_k in kpi_list:
            if isinstance(raw_k, str):
                if ":" in raw_k:
                    parts = raw_k.split(":", 1)
                    k = {"label": parts[0].strip(), "value": parts[1].strip()}
                else:
                    k = {"label": "Metric", "value": raw_k}
            elif isinstance(raw_k, Mapping):
                k = dict(raw_k)
            else:
                k = {"label": "Metric", "value": str(raw_k)}

            lbl = _safe_markup(str(k.get("label", "Metric")))
            val = _safe_markup(str(k.get("value", "—")))
            sub = _safe_markup(str(k.get("note", k.get("change", k.get("delta", "")))))
            card_content = (
                f"<font size='8' color='#475569'>{lbl}</font><br/>"
                f"<font size='12.5' color='{val_hex}'><b>{val}</b></font>"
            )
            if sub:
                card_content += f"<br/><font size='7.2' color='#047857'>{sub}</font>"

            card_row.append(Paragraph(card_content, body_style))
            if len(card_row) == cols_per_row:
                kpi_cells.append(card_row)
                card_row = []

        if card_row:
            while len(card_row) < cols_per_row:
                card_row.append("")
            kpi_cells.append(card_row)

        kpi_tbl = Table(kpi_cells, colWidths=[card_w] * cols_per_row)
        kpi_tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg_hex)),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(border_hex)),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor(grid_hex)),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return kpi_tbl

    # 3. Key Performance Indicators (Requested Period + Optional Labeled Comparison Period)
    if spec.kpis:
        if spec.requested_period and not spec.requested_period_has_data:
            story.append(
                Paragraph(
                    f"<b>Requested Period KPIs — {_safe_markup(spec.requested_period)} (Verified 0 Records):</b>",
                    component_title_style,
                )
            )
            story.append(
                _build_kpi_grid(
                    spec.kpis,
                    bg_hex="#FEF2F2",
                    border_hex="#FECACA",
                    grid_hex="#FEE2E2",
                    val_hex="#991B1B",
                )
            )
        else:
            story.append(_build_kpi_grid(spec.kpis))
        story.append(Spacer(1, 6))

    if spec.comparison_kpis:
        comp_hdr = _safe_markup(spec.historical_comparison_period or "Historical Comparison Period")
        story.append(
            Paragraph(
                f"<b>Historical Comparison KPIs — {comp_hdr} (Reference Only, Not Requested Period):</b>",
                component_title_style,
            )
        )
        story.append(
            _build_kpi_grid(
                spec.comparison_kpis,
                bg_hex="#FFFBEB",
                border_hex="#FDE68A",
                grid_hex="#FEF3C7",
                val_hex="#92400E",
            )
        )
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

    # 5. Dynamic Sections & Components (filtering out empty sections & avoiding duplicate chart titles)
    charts_requested = 0
    charts_rendered = 0
    tables_requested = 0
    tables_rendered = 0
    failed_components: list[dict[str, Any]] = []
    warnings: list[str] = list(spec.validation_warnings or [])

    datasets_count = len(spec.datasets)
    dataset_details: dict[str, int] = {
        ds_id: (len(ds.get("rows", [])) if isinstance(ds, dict) else len(ds) if isinstance(ds, (list, tuple)) else 0)
        for ds_id, ds in spec.datasets.items()
    }

    rendered_section_num = 0
    for raw_sec in spec.sections:
        section = raw_sec if isinstance(raw_sec, ReportSection) else ReportSection.from_dict(raw_sec)
        sec_comp_groups: list[list[Any]] = []

        for raw_comp in section.components:
            comp = raw_comp if isinstance(raw_comp, ReportComponent) else ReportComponent.from_dict(raw_comp)
            comp_flowables: list[Any] = []

            # Suppress external Paragraph title for charts when ChartRegistry already renders the same title inside the Drawing
            show_external_title = bool(comp.title)
            if comp.component_type == "chart" and comp.chart_config and comp.chart_config.title:
                if comp.title.strip().lower() == comp.chart_config.title.strip().lower():
                    show_external_title = False

            if show_external_title:
                comp_flowables.append(Paragraph(_safe_markup(comp.title), component_title_style))
            if comp.description:
                comp_flowables.append(Paragraph(_safe_markup(comp.description), body_style))
                comp_flowables.append(Spacer(1, 3))

            # Resolve dataset for component
            ds_data: dict[str, Any] = {}
            if comp.dataset_id and comp.dataset_id in spec.datasets:
                raw_ds = spec.datasets[comp.dataset_id]
                ds_data = raw_ds if isinstance(raw_ds, dict) else {"columns": [], "rows": list(raw_ds) if isinstance(raw_ds, (list, tuple)) else []}
            elif spec.datasets:
                raw_ds = next(iter(spec.datasets.values()))
                ds_data = raw_ds if isinstance(raw_ds, dict) else {"columns": [], "rows": list(raw_ds) if isinstance(raw_ds, (list, tuple)) else []}

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
                        comp_flowables.append(chart_drawing)
                        comp_flowables.append(Spacer(1, 8))
                        sec_comp_groups.append(comp_flowables)
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
                    comp_flowables.append(tbl_flowable)
                    comp_flowables.append(Spacer(1, 8))
                    sec_comp_groups.append(comp_flowables)
                    tables_rendered += 1
                except Exception as e:
                    failed_components.append({"type": "table", "title": comp.title, "error": str(e)})
                    warnings.append(f"Failed to render table '{comp.title}': {e}")

            elif comp.component_type == "text" and comp.content:
                comp_flowables.append(Paragraph(_safe_markup(str(comp.content)), body_style))
                comp_flowables.append(Spacer(1, 6))
                sec_comp_groups.append(comp_flowables)

        # Never render bare/empty section headings with 0 components
        if not sec_comp_groups:
            continue

        rendered_section_num += 1
        clean_sec_title = re.sub(r"^\d+\.\s*", "", section.title.strip())
        sec_header_flowables: list[Any] = [
            Paragraph(f"{rendered_section_num}. {_safe_markup(clean_sec_title)}", section_title_style)
        ]
        if section.description:
            sec_header_flowables.append(Paragraph(_safe_markup(section.description), body_style))
            sec_header_flowables.append(Spacer(1, 4))

        # Keep section title together with first component to prevent orphan headings at bottom of page
        story.append(KeepTogether(sec_header_flowables + sec_comp_groups[0]))
        for extra_group in sec_comp_groups[1:]:
            story.extend(extra_group)

    sections_count = rendered_section_num

    # 5b. Data Availability & Methodology Notes Section (if notes or omitted analyses exist)
    methodology_notes = list(spec.data_availability_notes or []) + [
        f"Omitted Visualization/Breakdown: {om}" for om in (spec.omitted_analyses or [])
    ]
    if methodology_notes:
        rendered_section_num += 1
        sections_count = rendered_section_num
        note_flowables: list[Any] = [
            Paragraph(f"{rendered_section_num}. Data Availability & Methodology Notes", section_title_style)
        ]
        note_rows = [[Paragraph(f"• {_safe_markup(n)}", body_style)] for n in methodology_notes]
        notes_tbl = Table(note_rows, colWidths=[available_width])
        notes_tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        note_flowables.append(notes_tbl)
        note_flowables.append(Spacer(1, 8))
        story.append(KeepTogether(note_flowables))

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
            sql_lines = [line for line in q_text.strip().splitlines() if line.strip()] or [q_text.strip()]
            table_data = [[Paragraph(_safe_markup(line), sql_code_style)] for line in sql_lines]
            sql_box = Table(
                table_data,
                colWidths=[available_width],
                repeatRows=0,
                splitByRow=1,
            )
            sql_box.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
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
        requested_period=spec.requested_period,
        actual_data_period=spec.actual_data_period,
        historical_comparison_period=spec.historical_comparison_period,
        requested_period_has_data=spec.requested_period_has_data,
        available_data_range=dict(spec.available_data_range or {}),
        kpis=list(spec.kpis or []),
        comparison_kpis=list(spec.comparison_kpis or []),
        omitted_analyses=list(spec.omitted_analyses or []),
        executive_summary=spec.executive_summary,
    )

    if record_history:
        from .report_manager import ReportHistoryManager

        ReportHistoryManager(output_dir).record(metadata)

    return metadata


def _infer_auto_column_format(col_name: str) -> str:
    """Infer display format ('currency', 'percent', 'int', or '') from column name."""
    cl = col_name.lower().strip()
    if any(k in cl for k in ("pct", "percent", "share_pct", "margin_pct", "rate_pct")):
        return "percent"
    if any(
        k in cl
        for k in (
            "sales",
            "revenue",
            "subtotal",
            "total_amount",
            "avg_order_value",
            "aov",
            "amount",
            "price",
            "cost",
            "fee",
            "tax",
            "discount",
            "profit",
        )
    ):
        return "currency"
    if any(
        k in cl
        for k in (
            "order_count",
            "total_orders",
            "orders_count",
            "orders",
            "transaction_count",
            "total_transactions",
            "transactions",
            "count",
            "units",
            "quantity",
        )
    ):
        return "int"
    return ""


def _is_non_additive_column(col_name: str) -> bool:
    """Return True if column is a ratio, average, or rate that must not be summed directly."""
    cl = col_name.lower().strip()
    return any(
        k in cl
        for k in ("avg", "average", "aov", "margin", "rate", "unit_price", "price", "ratio")
    )


def _is_homogeneous_crosstab(numeric_cols: Sequence[str]) -> bool:
    """Return True only when numeric columns are homogeneous pivot categories (e.g. status/channel slices).

    Returns False when columns represent distinct incompatible measures (such as Order Count + Sales + Revenue),
    preventing invalid horizontal row summation.
    """
    if len(numeric_cols) < 2:
        return False
    heterogeneous_measure_tokens = (
        "order",
        "transaction",
        "sales",
        "subtotal",
        "revenue",
        "total_amount",
        "amount",
        "aov",
        "avg",
        "average",
        "margin",
        "profit",
        "pct",
        "percent",
        "share",
        "price",
        "cost",
        "tax",
        "discount",
        "shipping",
        "count",
    )
    matched_tokens: set[str] = set()
    for c in numeric_cols:
        cl = c.lower().strip()
        for tok in heterogeneous_measure_tokens:
            if tok in cl:
                matched_tokens.add(tok)
    # If any heterogeneous metric keywords appear in the numeric column headers, they are distinct metrics, NOT a crosstab
    return len(matched_tokens) == 0


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
    from .canonical_data import validate_tabular_rows_structure

    display_cols = list(config.columns) if config.columns else list(columns)
    if not display_cols:
        return Paragraph("<i>(Empty table configuration)</i>", cell_left_style)

    # Validate and normalize rows, blocking scalar strings from character-by-character zipping
    _, sanitized_rows, _ = validate_tabular_rows_structure(columns, rows)
    dict_rows: list[dict[str, Any]] = []
    for r in sanitized_rows:
        if isinstance(r, Mapping):
            dict_rows.append(dict(r))
        elif isinstance(r, (list, tuple)):
            dict_rows.append(dict(zip(columns, r)))

    if config.limit and len(dict_rows) > config.limit:
        dict_rows = dict_rows[:config.limit]

    # Optional sorting
    if config.sort_by and dict_rows and config.sort_by in dict_rows[0]:
        dict_rows.sort(
            key=lambda r: (r.get(config.sort_by) is None, r.get(config.sort_by) or 0)
        )

    # Numeric alignment
    numeric_flags: list[bool] = []
    for c in display_cols:
        sample_vals = [r.get(c) for r in dict_rows[:10] if r.get(c) is not None]
        is_num = (
            all(isinstance(v, (int, float)) or _safe_float(v, None) is not None for v in sample_vals)
            if sample_vals
            else False
        )
        # Never treat temporal/month columns as numeric sums
        if any(k in c.lower() for k in ("month", "date", "period", "year", "id", "sku")):
            is_num = False
        numeric_flags.append(is_num)

    numeric_col_names = [c for c, is_num in zip(display_cols, numeric_flags) if is_num]

    # Row totals ONLY for homogeneous crosstab pivots (e.g., cancelled + delivered + shipped),
    # NEVER summing Order Count + Sales + Revenue!
    add_row_total = (
        config.show_totals
        and _is_homogeneous_crosstab(numeric_col_names)
        and "Total" not in [c.title() for c in display_cols]
    )
    if add_row_total:
        orig_cols = list(display_cols)
        orig_num = list(numeric_flags)
        display_cols = orig_cols + ["Total"]
        numeric_flags = orig_num + [True]
        for r in dict_rows:
            r["Total"] = sum(_safe_float(r.get(c), 0.0) for idx, c in enumerate(orig_cols) if orig_num[idx])

    # Summary row for vertical column totals (only when >= 2 rows exist)
    total_row_idx = -1
    if config.show_totals and len(dict_rows) >= 2:
        total_row: dict[str, Any] = {}
        # First pass: compute additive column totals
        for idx, c in enumerate(display_cols):
            if idx == 0:
                total_row[c] = "Total"
            elif numeric_flags[idx]:
                if _is_non_additive_column(c):
                    total_row[c] = None  # Computed in second pass
                else:
                    total_row[c] = sum(_safe_float(r.get(c), 0.0) for r in dict_rows)
            else:
                total_row[c] = ""

        # Second pass: compute derived ratios (such as AOV = Total Revenue / Total Orders)
        ord_col = next((c for c in display_cols if "order" in c.lower() and not _is_non_additive_column(c)), None)
        rev_col = next((c for c in display_cols if any(k in c.lower() for k in ("revenue", "total_amount", "sales"))), None)
        for idx, c in enumerate(display_cols):
            if idx > 0 and numeric_flags[idx] and total_row.get(c) is None:
                cl = c.lower()
                if any(k in cl for k in ("aov", "avg_order_value", "average_order_value")) and ord_col and rev_col:
                    tot_o = _safe_float(total_row.get(ord_col), 0.0)
                    tot_r = _safe_float(total_row.get(rev_col), 0.0)
                    total_row[c] = (tot_r / tot_o) if tot_o > 0 else "—"
                else:
                    # Average across rows for other rate/margin columns
                    vals = [_safe_float(r.get(c), 0.0) for r in dict_rows if r.get(c) is not None]
                    total_row[c] = (sum(vals) / len(vals)) if vals else "—"

        dict_rows.append(total_row)
        total_row_idx = len(dict_rows)

    col_widths = _compute_column_widths(display_cols, [[r.get(c) for c in display_cols] for r in dict_rows], available_width)

    header_cells = [Paragraph(_safe_markup(c.replace("_", " ").title()), header_style) for c in display_cols]
    table_data: list[list[Any]] = [header_cells]

    if dict_rows:
        for r_idx, r in enumerate(dict_rows, start=1):
            row_cells: list[Paragraph] = []
            is_tot_row = (total_row_idx > 0 and r_idx == total_row_idx)
            for idx, c in enumerate(display_cols):
                style = cell_right_style if numeric_flags[idx] else cell_left_style
                val = r.get(c)
                fmt = config.formatting.get(c, "") or (_infer_auto_column_format(c) if numeric_flags[idx] else "")
                if isinstance(val, str) and val in {"Total", "—", ""}:
                    val_str = val
                elif fmt:
                    val_str = _format_val(val, fmt)
                else:
                    val_str = _format_display_value(val)
                if is_tot_row or (add_row_total and idx == len(display_cols) - 1):
                    val_str = f"<b>{_safe_markup(val_str)}</b>"
                    row_cells.append(Paragraph(val_str, style))
                else:
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

    if total_row_idx > 0:
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
