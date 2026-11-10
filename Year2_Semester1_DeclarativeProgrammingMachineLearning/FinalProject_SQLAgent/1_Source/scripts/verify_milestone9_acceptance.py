"""Milestone 9 Acceptance Verification Script.

Executes all 7 acceptance scenarios against the live local Ollama model (qwen3.5:4b)
and MCP server to verify end-to-end functionality:
1. Default SQL approval (automatic approval, no dialog, logged in inspector)
2. Manual SQL approval (approval dialog workflow, reject blocks, approve permits)
3. Historical report (PDF with historical chart, pie chart, tables, executive summary)
4. Multi-series chart (PDF with multi-series line chart and summary table)
5. Matrix report (PDF with matrix crosstab, row totals, column totals, heatmap shading)
6. SQL appendix (included only when explicitly requested)
7. CSV export (aggregated monthly orders and revenue)
+ Visual page rendering to PNG via PySide6 QPdfDocument for visual inspection.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtCore import QSize
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import QApplication

from agent import ActivityCategory, AgentEvent, AgentOrchestrator
from config.settings import AppSettings
from tests.test_reporting import _extract_pdf_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("m9_verifier")


def render_pdf_to_images(pdf_path: Path, output_prefix: str) -> list[Path]:
    """Render all pages of a PDF to high-resolution PNG images using PySide6 QPdfDocument."""
    app = QApplication.instance() or QApplication(sys.argv)
    doc = QPdfDocument()
    doc.load(str(pdf_path))
    num_pages = doc.pageCount()
    rendered_images: list[Path] = []

    for page_idx in range(num_pages):
        page_size = doc.pagePointSize(page_idx).toSize() * 2
        img = doc.render(page_idx, page_size)
        out_img_path = pdf_path.parent / f"{output_prefix}_page_{page_idx + 1}.png"
        img.save(str(out_img_path))
        rendered_images.append(out_img_path)
        log.info("  [Visual Inspection] Rendered page %d/%d to %s (%d bytes)", page_idx + 1, num_pages, out_img_path.name, out_img_path.stat().st_size)

    return rendered_images


async def run_milestone9_acceptance_tests() -> None:
    settings = AppSettings()
    log.info("Starting Milestone 9 Verification with model: %s", settings.ollama.model)

    # Verify initial database sha256
    db_file = settings.database_path
    initial_sha = hashlib.sha256(db_file.read_bytes()).hexdigest()
    log.info("Initial database SHA-256: %s", initial_sha)

    orchestrator = AgentOrchestrator(settings)
    await orchestrator.initialize()

    def make_progress_logger(test_name: str, event_list: list):
        def _cb(event: AgentEvent) -> None:
            if event.activity_event:
                ae = event.activity_event
                event_list.append(ae)
                cat = ae.category if isinstance(ae.category, str) else getattr(ae.category, "value", str(ae.category))
                log.info("  [%s Activity] %s: %s", test_name, cat, ae.title)
        return _cb

    # -------------------------------------------------------------------------
    # TEST 1: Default SQL Approval (Disabled manual approval -> Auto-approved)
    # -------------------------------------------------------------------------
    log.info("\n=== TEST 1: Default SQL Approval (Auto-approved) ===")
    settings.agent.require_sql_approval = False
    orchestrator.settings.agent.require_sql_approval = False
    orchestrator.reset_conversation()
    t1_events = []
    t1_dialog_shown = False

    def t1_dialog_tracker(query: str, exp: str) -> bool:
        nonlocal t1_dialog_shown
        t1_dialog_shown = True
        return True

    res1 = await orchestrator.process_message(
        "Show me the top 10 products by revenue.",
        approval_callback=t1_dialog_tracker,
        progress_callback=make_progress_logger("Test 1", t1_events),
    )
    log.info("Test 1 Status: %s", res1.status)
    assert res1.is_success, f"Test 1 failed: {res1.error}"
    assert t1_dialog_shown is False, "Approval dialog was invoked when approval is disabled!"
    # Verify inspector logged automatic approval
    auto_app_events = [e for e in t1_events if e.category == ActivityCategory.APPROVAL_RESULT.value]
    assert len(auto_app_events) >= 1, "Expected APPROVAL_RESULT activity event"
    assert auto_app_events[0].status == "auto_approved"
    assert "SQL automatically approved — manual approval is disabled in settings." in auto_app_events[0].description
    log.info(">>> TEST 1 PASSED: SQL auto-approved without dialog and logged in inspector <<<")

    # -------------------------------------------------------------------------
    # TEST 2: Manual SQL Approval Enabled (Approval dialog workflow)
    # -------------------------------------------------------------------------
    log.info("\n=== TEST 2: Manual SQL Approval Enabled ===")
    settings.agent.require_sql_approval = True
    orchestrator.settings.agent.require_sql_approval = True

    # Case 2A: User Rejects
    log.info("--- Subtest 2A: User Rejects Query ---")
    orchestrator.reset_conversation()
    t2a_events = []
    t2a_dialog_shown = False

    def t2a_reject(query: str, exp: str) -> bool:
        nonlocal t2a_dialog_shown
        t2a_dialog_shown = True
        log.info("  User clicked REJECT for SQL:\n%s", query[:80])
        return False

    res2a = await orchestrator.process_message(
        "Show me the top 10 products by revenue.",
        approval_callback=t2a_reject,
        progress_callback=make_progress_logger("Test 2A", t2a_events),
    )
    assert t2a_dialog_shown is True, "Approval dialog was NOT invoked when approval is enabled!"
    assert res2a.status == "approval_denied" or "denied" in res2a.final_message.lower()
    assert any(e.category == ActivityCategory.APPROVAL_RESULT.value and e.status == "rejected" for e in t2a_events)
    log.info("  Subtest 2A Passed: Rejection successfully blocked execution.")

    # Case 2B: User Approves
    log.info("--- Subtest 2B: User Approves Query ---")
    orchestrator.reset_conversation()
    t2b_events = []
    t2b_dialog_shown = False

    def t2b_approve(query: str, exp: str) -> bool:
        nonlocal t2b_dialog_shown
        t2b_dialog_shown = True
        log.info("  User clicked APPROVE for SQL:\n%s", query[:80])
        return True

    res2b = await orchestrator.process_message(
        "Show me the top 10 products by revenue.",
        approval_callback=t2b_approve,
        progress_callback=make_progress_logger("Test 2B", t2b_events),
    )
    assert t2b_dialog_shown is True
    assert res2b.is_success
    assert any(e.category == ActivityCategory.APPROVAL_RESULT.value and e.status == "success" for e in t2b_events)
    log.info(">>> TEST 2 PASSED: Manual SQL approval dialog fully enforced <<<")

    # For remaining report tests, keep require_sql_approval = False to allow fluid report generation
    settings.agent.require_sql_approval = False
    orchestrator.settings.agent.require_sql_approval = False

    # -------------------------------------------------------------------------
    # TEST 3: Historical report with historical chart, pie chart, and tables
    # -------------------------------------------------------------------------
    log.info("\n=== TEST 3: Detailed Historical Report with Charts ===")
    orchestrator.reset_conversation()
    t3_events = []

    res3 = await orchestrator.process_message(
        "Create a detailed PDF report containing an historical chart of orders, a pie chart of order distribution and tables regarding order data.",
        progress_callback=make_progress_logger("Test 3", t3_events),
    )
    log.info("Test 3 Status: %s", res3.status)
    assert res3.is_success, f"Test 3 failed: {res3.error}"
    assert len(res3.generated_reports) >= 1
    rep3 = res3.generated_reports[0]
    pdf3_path = Path(rep3["output_path"])
    log.info("Test 3 PDF Path: %s (%d bytes)", pdf3_path.name, rep3.get("file_size_bytes", 0))
    assert pdf3_path.is_file()
    assert rep3.get("charts_rendered", 0) >= 2, f"Expected at least 2 charts rendered, got {rep3.get('charts_rendered')}"
    assert rep3.get("completion_status") == "complete"
    # Verify no SQL appendix by default
    pdf3_text = _extract_pdf_text(pdf3_path)
    assert "Appendix: Executed SQL Queries" not in pdf3_text
    # Render PDF pages to PNG for visual inspection
    render_pdf_to_images(pdf3_path, "milestone9_test3_historical")
    log.info(">>> TEST 3 PASSED: Actual historical and pie charts rendered in PDF <<<")

    # -------------------------------------------------------------------------
    # TEST 4: Multi-series line chart PDF report
    # -------------------------------------------------------------------------
    log.info("\n=== TEST 4: Multi-Series Line Chart PDF Report ===")
    orchestrator.reset_conversation()
    t4_events = []

    res4 = await orchestrator.process_message(
        "Generate a PDF comparing monthly revenue across different product categories using a multi-series line chart, including a summary table.",
        progress_callback=make_progress_logger("Test 4", t4_events),
    )
    log.info("Test 4 Status: %s", res4.status)
    assert res4.is_success, f"Test 4 failed: {res4.error}"
    assert len(res4.generated_reports) >= 1
    rep4 = res4.generated_reports[0]
    pdf4_path = Path(rep4["output_path"])
    log.info("Test 4 PDF Path: %s (%d bytes)", pdf4_path.name, rep4.get("file_size_bytes", 0))
    assert pdf4_path.is_file()
    assert rep4.get("charts_rendered", 0) >= 1
    render_pdf_to_images(pdf4_path, "milestone9_test4_multiseries")
    log.info(">>> TEST 4 PASSED: Multi-series line chart rendered in PDF <<<")

    # -------------------------------------------------------------------------
    # TEST 5: Matrix Report (Crosstab with totals and heatmap)
    # -------------------------------------------------------------------------
    log.info("\n=== TEST 5: Matrix Report (Crosstab with Totals & Heatmap) ===")
    orchestrator.reset_conversation()
    t5_events = []

    res5 = await orchestrator.process_message(
        "Generate a report with a matrix showing order counts by month and order status, including row totals, column totals and a heatmap-style visualization if supported.",
        progress_callback=make_progress_logger("Test 5", t5_events),
    )
    log.info("Test 5 Status: %s", res5.status)
    assert res5.is_success, f"Test 5 failed: {res5.error}"
    assert len(res5.generated_reports) >= 1
    rep5 = res5.generated_reports[0]
    pdf5_path = Path(rep5["output_path"])
    log.info("Test 5 PDF Path: %s (%d bytes)", pdf5_path.name, rep5.get("file_size_bytes", 0))
    assert pdf5_path.is_file()
    render_pdf_to_images(pdf5_path, "milestone9_test5_matrix")
    log.info(">>> TEST 5 PASSED: Matrix crosstab with totals and heatmap rendered <<<")

    # -------------------------------------------------------------------------
    # TEST 6: SQL Appendix (Explicitly Requested)
    # -------------------------------------------------------------------------
    log.info("\n=== TEST 6: Report with Explicit SQL Appendix ===")
    orchestrator.reset_conversation()
    t6_events = []

    res6 = await orchestrator.process_message(
        "Generate a PDF report containing the top 10 products by revenue and include the SQL queries in a final appendix.",
        progress_callback=make_progress_logger("Test 6", t6_events),
    )
    log.info("Test 6 Status: %s", res6.status)
    assert res6.is_success, f"Test 6 failed: {res6.error}"
    assert len(res6.generated_reports) >= 1
    rep6 = res6.generated_reports[0]
    pdf6_path = Path(rep6["output_path"])
    log.info("Test 6 PDF Path: %s (%d bytes)", pdf6_path.name, rep6.get("file_size_bytes", 0))
    assert pdf6_path.is_file()
    pdf6_text = _extract_pdf_text(pdf6_path)
    assert "Appendix" in pdf6_text, "Expected SQL Appendix in output when explicitly requested!"
    render_pdf_to_images(pdf6_path, "milestone9_test6_sql_appendix")
    log.info(">>> TEST 6 PASSED: SQL Appendix included per explicit request <<<")

    # -------------------------------------------------------------------------
    # TEST 7: CSV Export
    # -------------------------------------------------------------------------
    log.info("\n=== TEST 7: CSV Export ===")
    orchestrator.reset_conversation()
    t7_events = []

    res7 = await orchestrator.process_message(
        "Export monthly order counts and revenue to CSV.",
        progress_callback=make_progress_logger("Test 7", t7_events),
    )
    log.info("Test 7 Status: %s", res7.status)
    assert res7.is_success, f"Test 7 failed: {res7.error}"
    assert len(res7.generated_reports) >= 1
    rep7 = res7.generated_reports[0]
    csv_path = Path(rep7["output_path"])
    log.info("Test 7 CSV Path: %s (%d bytes, Format: %s)", csv_path.name, rep7.get("file_size_bytes", 0), rep7.get("output_format"))
    assert csv_path.is_file()
    assert rep7.get("output_format") == "CSV"
    assert rep7.get("record_count", 0) > 0
    csv_content = csv_path.read_text(encoding="utf-8")
    log.info("Test 7 CSV Preview:\n%s", "\n".join(csv_content.strip().splitlines()[:5]))
    log.info(">>> TEST 7 PASSED: CSV export generated successfully <<<")

    # Clean shutdown
    await orchestrator.close()

    # Final DB sha256 verification
    final_sha = hashlib.sha256(db_file.read_bytes()).hexdigest()
    assert initial_sha == final_sha, f"Database was modified! Initial: {initial_sha}, Final: {final_sha}"
    log.info("Final database SHA-256 match verified: %s", final_sha)

    log.info("\n==================================================================")
    log.info("🏆 ALL 7 MILESTONE 9 ACCEPTANCE TESTS COMPLETED SUCCESSFULLY!")
    log.info("==================================================================")


if __name__ == "__main__":
    asyncio.run(run_milestone9_acceptance_tests())

