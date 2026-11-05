"""Automated Pytest suite for PDF generation, CSV generation, path security, and report history."""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pytest

from reporting import (
    ReportHistoryManager,
    ReportSecurityError,
    ReportValidationError,
    generate_csv_file,
    generate_pdf_file,
    resolve_safe_report_path,
    sanitize_filename_stem,
)


def test_filename_sanitization_and_traversal_protection(tmp_path: Path) -> None:
    out_dir = tmp_path / "reports"

    assert sanitize_filename_stem("../../etc/passwd") == "etc_passwd"
    assert sanitize_filename_stem(r"..\..\Windows\System32\CON") == "windows_system32_con"
    assert sanitize_filename_stem("CON").startswith("report_")
    assert sanitize_filename_stem("   ///...   ") == "report"

    safe_pdf = resolve_safe_report_path(out_dir, "../../../secret_escape", "pdf")
    assert safe_pdf.parent == out_dir.resolve()
    assert safe_pdf.suffix == ".pdf"

    with pytest.raises(ReportSecurityError):
        sanitize_filename_stem("bad\x00title")

    with pytest.raises(ReportValidationError):
        resolve_safe_report_path(out_dir, "report", "exe")


def test_csv_generation_utf8_nulls_and_escaping(tmp_path: Path) -> None:
    out_dir = tmp_path / "reports"
    columns = ["customer_name", "note", "amount", "optional_phone"]
    rows = [
        ["Alice, Jr.", 'Said "Hello"\nNext line', 1234.56, None],
        ["Élodie Müller", "Price in € & £ <ok>", 0, "+33-1-99"],
    ]

    meta = generate_csv_file(
        title="Special Chars & UTF-8 CSV!",
        columns=columns,
        rows=rows,
        output_dir=out_dir,
        description="Checks escaping and NULLs",
        sql_query="SELECT * FROM sample",
    )

    path = Path(meta.output_path)
    assert path.is_file()
    assert path.parent == out_dir.resolve()
    assert meta.output_format == "CSV"
    assert meta.record_count == 2
    assert meta.truncated is False

    with path.open("r", encoding="utf-8", newline="") as fh:
        parsed = list(csv.reader(fh))

    assert parsed[0] == columns
    assert parsed[1] == ["Alice, Jr.", 'Said "Hello"\nNext line', "1234.56", ""]
    assert parsed[2] == ["Élodie Müller", "Price in € & £ <ok>", "0", "+33-1-99"]


def test_csv_empty_and_large_results(tmp_path: Path) -> None:
    out_dir = tmp_path / "reports"

    empty_meta = generate_csv_file(
        title="Empty Result Report",
        columns=["month", "revenue"],
        rows=[],
        output_dir=out_dir,
    )
    assert empty_meta.record_count == 0
    lines = Path(empty_meta.output_path).read_text(encoding="utf-8").splitlines()
    assert lines == ["month,revenue"]

    large_rows = [[i, f"Item #{i}", round(i * 1.25, 2)] for i in range(2_500)]
    large_meta = generate_csv_file(
        title="Large Dataset Export",
        columns=["id", "label", "total"],
        rows=large_rows,
        output_dir=out_dir,
    )
    assert large_meta.record_count == 2_500
    assert Path(large_meta.output_path).stat().st_size > 30_000


def test_pdf_generation_single_and_multipage_with_special_chars(tmp_path: Path) -> None:
    out_dir = tmp_path / "reports"

    # 8 columns + 220 rows triggers automatic Landscape layout and multi-page pagination
    columns = [
        "order_id",
        "customer_name",
        "country",
        "channel",
        "payment_method",
        "notes_xml_check",
        "discount",
        "total_amount",
    ]
    rows = [
        [
            1000 + i,
            f"Customer {i} (Élodie & Co.)",
            "Germany" if i % 2 == 0 else "United States",
            "web",
            "card",
            f"Tag <check id='{i}'> & quote \"ok\"" if i % 5 else None,
            0.0,
            round(145.75 + i * 3.1, 2),
        ]
        for i in range(220)
    ]

    meta = generate_pdf_file(
        title="Monthly Revenue & Channel Breakdown",
        description="Multi-page analytical report with XML-sensitive characters.",
        sql_query="SELECT order_id, customer_name, total_amount FROM orders ORDER BY order_id",
        columns=columns,
        rows=rows,
        output_dir=out_dir,
        summary="Total of 220 orders analysed across web and app channels.",
    )

    pdf_path = Path(meta.output_path)
    assert pdf_path.is_file()
    assert pdf_path.parent == out_dir.resolve()
    assert meta.output_format == "PDF"
    assert meta.record_count == 220

    raw_bytes = pdf_path.read_bytes()
    assert raw_bytes.startswith(b"%PDF-")
    assert raw_bytes.rstrip().endswith(b"%%EOF")
    # Count PDF '/Type /Page' leaf objects (excluding '/Type /Pages') to prove multi-page pagination
    page_count = len(re.findall(rb"/Type\s*/Page\b", raw_bytes))
    assert page_count >= 4


def test_pdf_empty_results_and_dict_rows_and_truncation(tmp_path: Path) -> None:
    out_dir = tmp_path / "reports"

    empty_pdf = generate_pdf_file(
        title="Zero Rows PDF",
        description="Query returned no matching records",
        sql_query="SELECT id, total FROM orders WHERE 1 = 0",
        columns=["id", "total"],
        rows=[],
        output_dir=out_dir,
    )
    assert empty_pdf.record_count == 0
    assert Path(empty_pdf.output_path).read_bytes().startswith(b"%PDF-")

    # Dict rows + max_pdf_rows truncation
    dict_rows = [{"id": i, "total": i * 10.0} for i in range(25)]
    trunc_pdf = generate_pdf_file(
        title="Truncated PDF",
        columns=["id", "total"],
        rows=dict_rows,
        output_dir=out_dir,
        max_pdf_rows=10,
    )
    assert trunc_pdf.record_count == 10
    assert trunc_pdf.total_input_records == 25
    assert trunc_pdf.truncated is True


def test_report_history_persistence_and_lookup(tmp_path: Path) -> None:
    out_dir = tmp_path / "reports"

    pdf_meta = generate_pdf_file(
        title="First Report",
        columns=["a", "b"],
        rows=[[1, "x"]],
        output_dir=out_dir,
    )
    csv_meta = generate_csv_file(
        title="Second Report",
        columns=["a", "b"],
        rows=[[2, "y"]],
        output_dir=out_dir,
    )

    mgr = ReportHistoryManager(out_dir)
    history = mgr.list_reports()
    assert len(history) == 2
    # Newest first
    assert history[0].report_id == csv_meta.report_id
    assert history[1].report_id == pdf_meta.report_id
    assert history[0].to_dict()["file_exists"] is True

    looked_up = mgr.get_report(pdf_meta.report_id)
    assert looked_up is not None
    assert looked_up.title == "First Report"

    # Validation error cases
    with pytest.raises(ReportValidationError):
        generate_csv_file(title="", columns=["a"], rows=[[1]], output_dir=out_dir)

    with pytest.raises(ReportValidationError):
        generate_pdf_file(title="Bad Width", columns=["a", "b"], rows=[[1]], output_dir=out_dir)


# ---------------------------------------------------------------------------
# Milestone 8: Advanced Dynamic Reporting & Chart Engine Tests
# ---------------------------------------------------------------------------


def test_m8_all_11_vector_chart_types_build() -> None:
    """Milestone 8: Build and verify all 11 ReportLab vector chart types."""
    from reporting.chart_builder import build_chart
    from reporting.report_spec import ChartConfiguration, ChartType

    sample_rows = [
        {"month": "2023-01", "sales": 100, "profit": 30, "cat": "Books"},
        {"month": "2023-02", "sales": 150, "profit": 45, "cat": "Electronics"},
        {"month": "2023-03", "sales": 120, "profit": 35, "cat": "Apparel"},
        {"month": "2023-04", "sales": 200, "profit": 60, "cat": "Home"},
    ]

    all_chart_types = [
        ChartType.LINE,
        ChartType.MULTI_LINE,
        ChartType.HISTORICAL_LINE,
        ChartType.VERTICAL_BAR,
        ChartType.GROUPED_BAR,
        ChartType.STACKED_BAR,
        ChartType.HORIZONTAL_BAR,
        ChartType.PIE,
        ChartType.DONUT,
        ChartType.AREA,
        ChartType.SCATTER,
    ]

    for ct in all_chart_types:
        y_cols = ["sales", "profit"] if ct in {ChartType.MULTI_LINE, ChartType.GROUPED_BAR, ChartType.STACKED_BAR} else ["sales"]
        config = ChartConfiguration(
            chart_type=ct,
            title=f"Test {ct.value}",
            x_column="month",
            y_columns=y_cols,
        )
        drawing = build_chart(config, sample_rows, width=450, height=200)
        assert drawing is not None, f"Chart type {ct.value} failed to build"
        assert drawing.width == 450
        assert drawing.height == 200


def test_m8_dynamic_pdf_composer_multi_dataset(tmp_path: Path) -> None:
    """Milestone 8: Test compose_dynamic_pdf with multiple datasets, KPI cards, charts, and tables."""
    from reporting.dynamic_pdf_composer import compose_dynamic_pdf
    from reporting.report_spec import (
        ChartConfiguration,
        ChartType,
        ReportComponent,
        ReportSection,
        ReportSpecification,
        TableConfiguration,
    )

    out_dir = tmp_path / "reports"
    spec = ReportSpecification(
        title="Quarterly Performance Report",
        subtitle="Multi-Dataset Analysis Q1-Q2",
        executive_summary="Executive summary highlighting solid growth across major product sectors.",
        kpis=[
            {"label": "Total Revenue", "value": "$145,200", "delta": "+12.4%"},
            {"label": "Total Orders", "value": "1,240", "delta": "+8.1%"},
            {"label": "Avg Order Value", "value": "$117.10", "delta": "+4.0%"},
        ],
        key_findings=[
            "Electronics category generated 48% of total gross sales.",
            "Repeat customer order rate grew to 34% in Q2.",
        ],
        datasets={
            "monthly_orders": {
                "name": "monthly_orders",
                "columns": ["month", "orders_count", "revenue"],
                "rows": [
                    ["2023-01", 310, 36270.0],
                    ["2023-02", 290, 33930.0],
                    ["2023-03", 350, 40950.0],
                    ["2023-04", 290, 34050.0],
                ],
            },
            "status_distribution": {
                "name": "status_distribution",
                "columns": ["status", "count"],
                "rows": [
                    ["delivered", 1120],
                    ["shipped", 80],
                    ["canceled", 40],
                ],
            },
        },
        sections=[
            ReportSection(
                title="1. Order Volume Trends",
                description="Monthly order progression over the first two quarters.",
                components=[
                    ReportComponent(
                        component_type="chart",
                        dataset_name="monthly_orders",
                        chart_config=ChartConfiguration(
                            chart_type=ChartType.HISTORICAL_LINE,
                            title="Monthly Orders",
                            x_column="month",
                            y_columns=["orders_count"],
                        ),
                    ),
                    ReportComponent(
                        component_type="table",
                        dataset_name="monthly_orders",
                        table_config=TableConfiguration(
                            columns=["month", "orders_count", "revenue"],
                            formatting={"revenue": "currency"},
                        ),
                    ),
                ],
            ),
            ReportSection(
                title="2. Fulfillment Status Distribution",
                components=[
                    ReportComponent(
                        component_type="chart",
                        dataset_name="status_distribution",
                        chart_config=ChartConfiguration(
                            chart_type=ChartType.DONUT,
                            title="Orders by Status",
                            x_column="status",
                            y_columns=["count"],
                        ),
                    ),
                ],
            ),
        ],
        include_sql=False,
    )

    meta = compose_dynamic_pdf(spec, out_dir)
    assert meta is not None
    assert meta.file_size_bytes > 5_000
    pdf_path = Path(meta.output_path)
    assert pdf_path.is_file()
    assert pdf_path.read_bytes().startswith(b"%PDF-")


def _extract_pdf_text(pdf_path: Path) -> str:
    """Helper to extract text from ReportLab PDF by decompressing streams."""
    import base64
    import zlib

    data = pdf_path.read_bytes()
    text_parts: list[str] = [data.decode("latin1", errors="ignore")]
    idx = 0
    while True:
        s_idx = data.find(b"stream\n", idx)
        if s_idx == -1:
            s_idx = data.find(b"stream\r\n", idx)
            if s_idx == -1:
                break
            s_idx += 8
        else:
            s_idx += 7
        e_idx = data.find(b"endstream", s_idx)
        if e_idx == -1:
            break
        raw_stream = data[s_idx:e_idx].strip()
        try:
            a85 = base64.a85decode(raw_stream, adobe=True)
            text_parts.append(zlib.decompress(a85).decode("latin1", errors="ignore"))
        except Exception:
            try:
                text_parts.append(zlib.decompress(raw_stream).decode("latin1", errors="ignore"))
            except Exception:
                text_parts.append(raw_stream.decode("latin1", errors="ignore"))
        idx = e_idx + 9
    return "\n".join(text_parts)


def test_m8_sql_visibility_policy_in_pdf(tmp_path: Path) -> None:
    """Milestone 8: SQL query is excluded by default and included in appendix only when requested."""
    out_dir = tmp_path / "reports"
    secret_sql = "SELECT order_id, secret_code FROM confidential_orders"

    # 1. Default: include_sql=False -> SQL query must NOT appear in output
    meta_no_sql = generate_pdf_file(
        title="No SQL PDF Report",
        columns=["order_id"],
        rows=[[101]],
        sql_query=secret_sql,
        output_dir=out_dir,
        include_sql=False,
    )
    pdf_text_no_sql = _extract_pdf_text(Path(meta_no_sql.output_path))
    assert "confidential_orders" not in pdf_text_no_sql
    assert "Appendix: SQL Queries" not in pdf_text_no_sql

    # 2. Explicit: include_sql=True -> SQL query must appear in dedicated Appendix
    meta_with_sql = generate_pdf_file(
        title="With SQL PDF Report",
        columns=["order_id"],
        rows=[[101]],
        sql_query=secret_sql,
        output_dir=out_dir,
        include_sql=True,
    )
    pdf_text_with_sql = _extract_pdf_text(Path(meta_with_sql.output_path))
    assert "Appendix: SQL Queries" in pdf_text_with_sql
    assert "confidential_orders" in pdf_text_with_sql


def test_m8_multi_dataset_csv_generation(tmp_path: Path) -> None:
    """Milestone 8: Multi-dataset CSV exports separate datasets with boundary headers."""
    out_dir = tmp_path / "reports"
    datasets = {
        "monthly_revenue": {
            "columns": ["month", "revenue"],
            "rows": [["2023-01", 1000], ["2023-02", 1500]],
        },
        "order_statuses": {
            "columns": ["status", "count"],
            "rows": [["delivered", 50], ["pending", 5]],
        },
    }

    meta = generate_csv_file(
        title="Multi Dataset Export",
        columns=["month", "revenue"],
        rows=[["2023-01", 1000]],
        datasets=datasets,
        output_dir=out_dir,
    )

    csv_content = Path(meta.output_path).read_text(encoding="utf-8")
    assert "# Dataset: monthly_revenue" in csv_content
    assert "month,revenue" in csv_content
    assert "# Dataset: order_statuses" in csv_content
    assert "status,count" in csv_content
    assert "delivered,50" in csv_content


