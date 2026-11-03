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

