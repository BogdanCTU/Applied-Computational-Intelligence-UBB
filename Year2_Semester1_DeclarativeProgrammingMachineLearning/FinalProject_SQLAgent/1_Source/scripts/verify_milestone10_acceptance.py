"""Milestone 10 Acceptance Verification Script.

Executes comprehensive acceptance scenarios covering:
1. SQL Approval toggle verification (Auto-approved when False, dialog-enforced when True with rejection and approval).
2. Advanced Chart Generation & Multi-Component Reporting across categories:
   - Comparison & Ranking: horizontal_bar
   - Trend & Time-Series: historical_line, multi_line
   - Distribution: pie, donut, histogram, box_plot
   - Hierarchical: treemap
   - Matrix & Tabular: matrix crosstab with row/column totals and heatmap shading
3. SQL Appendix verification (included only when explicitly requested).
4. CSV Export.
5. High-resolution PDF page rendering to PNG using PySide6 QPdfDocument for visual inspection.
6. Absolute database immutability verification via SHA-256 checksums.
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
log = logging.getLogger("m10_verifier")


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
        log.info(
            "  [Visual Inspection] Rendered page %d/%d to %s (%d bytes)",
            page_idx + 1,
            num_pages,
            out_img_path.name,
            out_img_path.stat().st_size,
        )

    return rendered_images


async def run_milestone10_acceptance_tests() -> None:
    settings = AppSettings()
    log.info("Starting Milestone 10 Verification with model: %s", settings.ollama.model)

    # 1. Verify database integrity upfront
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
    # TEST 1: Configurable SQL Approval Toggle
    # -------------------------------------------------------------------------
    log.info("\n=== TEST 1: Configurable SQL Approval Toggle ===")
    
    # 1A: require_sql_approval = False (Default: Auto-approved without dialog)
    log.info("--- Subtest 1A: require_sql_approval = False (Auto-approved) ---")
    settings.agent.require_sql_approval = False
    orchestrator.settings.agent.require_sql_approval = False
    orchestrator.reset_conversation()
    t1a_events = []
    t1a_dialog_shown = False

    def t1a_dialog(query: str, exp: str) -> bool:
        nonlocal t1a_dialog_shown
        t1a_dialog_shown = True
        return True

    res1a = await orchestrator.process_message(
        "Show me total sales revenue by product category.",
        approval_callback=t1a_dialog,
        progress_callback=make_progress_logger("Test 1A", t1a_events),
    )
    assert res1a.is_success, f"Test 1A failed: {res1a.error}"
    assert t1a_dialog_shown is False, "Approval dialog was shown when require_sql_approval is False!"
    auto_app_events = [e for e in t1a_events if e.category == ActivityCategory.APPROVAL_RESULT.value]
    assert len(auto_app_events) >= 1, "Expected APPROVAL_RESULT event in activity log"
    assert auto_app_events[0].status == "auto_approved"
    log.info("  Subtest 1A Passed: Auto-approved without modal, logged in inspector.")

    # 1B: require_sql_approval = True (Rejection test)
    log.info("--- Subtest 1B: require_sql_approval = True (Rejection) ---")
    settings.agent.require_sql_approval = True
    orchestrator.settings.agent.require_sql_approval = True
    orchestrator.reset_conversation()
    t1b_events = []
    t1b_dialog_shown = False

    def t1b_reject(query: str, exp: str) -> bool:
        nonlocal t1b_dialog_shown
        t1b_dialog_shown = True
        return False

    res1b = await orchestrator.process_message(
        "Show me the top 5 customers by spending.",
        approval_callback=t1b_reject,
        progress_callback=make_progress_logger("Test 1B", t1b_events),
    )
    assert t1b_dialog_shown is True, "Approval dialog was NOT shown when require_sql_approval is True!"
    assert res1b.status == "approval_denied" or "denied" in res1b.final_message.lower()
    assert any(e.category == ActivityCategory.APPROVAL_RESULT.value and e.status == "rejected" for e in t1b_events)
    log.info("  Subtest 1B Passed: Rejection successfully blocked execution.")

    # 1C: require_sql_approval = True (Approval test)
    log.info("--- Subtest 1C: require_sql_approval = True (Approval) ---")
    orchestrator.reset_conversation()
    t1c_events = []
    t1c_dialog_shown = False

    def t1c_approve(query: str, exp: str) -> bool:
        nonlocal t1c_dialog_shown
        t1c_dialog_shown = True
        return True

    res1c = await orchestrator.process_message(
        "Show me the top 5 customers by spending.",
        approval_callback=t1c_approve,
        progress_callback=make_progress_logger("Test 1C", t1c_events),
    )
    assert t1c_dialog_shown is True, "Approval dialog was NOT shown when require_sql_approval is True!"
    assert res1c.is_success, f"Test 1C failed: {res1c.error}"
    assert any(e.category == ActivityCategory.APPROVAL_RESULT.value and e.status == "success" for e in t1c_events)
    log.info("  Subtest 1C Passed: Approval permitted execution.")
    log.info(">>> TEST 1 PASSED: Configurable SQL approval fully verified <<<")

    # Set require_sql_approval = False for automated reporting tests
    settings.agent.require_sql_approval = False
    orchestrator.settings.agent.require_sql_approval = False

    # -------------------------------------------------------------------------
    # TEST 2: Historical orders & Distribution (historical_line + pie/donut)
    # -------------------------------------------------------------------------
    log.info("\n=== TEST 2: Historical Trend & Distribution PDF Report ===")
    orchestrator.reset_conversation()
    t2_events = []

    res2 = await orchestrator.process_message(
        "Create a detailed PDF report containing an historical line chart of orders over time, a pie chart of order status distribution, and a summary table.",
        progress_callback=make_progress_logger("Test 2", t2_events),
    )
    log.info("Test 2 Status: %s", res2.status)
    assert res2.is_success, f"Test 2 failed: {res2.error}"
    assert len(res2.generated_reports) >= 1
    rep2 = res2.generated_reports[0]
    pdf2_path = Path(rep2["output_path"])
    log.info("Test 2 PDF Path: %s (%d bytes)", pdf2_path.name, rep2.get("file_size_bytes", 0))
    assert pdf2_path.is_file()
    assert rep2.get("charts_rendered", 0) >= 2, f"Expected >= 2 charts, got {rep2.get('charts_rendered')}"
    assert rep2.get("completion_status") == "complete"
    # Visual rendering
    imgs2 = render_pdf_to_images(pdf2_path, "milestone10_test2_historical_pie")
    assert len(imgs2) >= 1
    log.info(">>> TEST 2 PASSED: Historical line and pie chart report rendered successfully <<<")

    # -------------------------------------------------------------------------
    # TEST 3: Product Revenue Ranking (horizontal_bar)
    # -------------------------------------------------------------------------
    log.info("\n=== TEST 3: Product Ranking Horizontal Bar PDF Report ===")
    orchestrator.reset_conversation()
    t3_events = []

    res3 = await orchestrator.process_message(
        "Generate a PDF report ranking the top 10 products by total revenue using a horizontal bar chart.",
        progress_callback=make_progress_logger("Test 3", t3_events),
    )
    log.info("Test 3 Status: %s", res3.status)
    assert res3.is_success, f"Test 3 failed: {res3.error}"
    assert len(res3.generated_reports) >= 1
    rep3 = res3.generated_reports[0]
    pdf3_path = Path(rep3["output_path"])
    log.info("Test 3 PDF Path: %s (%d bytes)", pdf3_path.name, rep3.get("file_size_bytes", 0))
    assert pdf3_path.is_file()
    assert rep3.get("charts_rendered", 0) >= 1
    imgs3 = render_pdf_to_images(pdf3_path, "milestone10_test3_ranking_hbar")
    assert len(imgs3) >= 1
    log.info(">>> TEST 3 PASSED: Horizontal bar ranking report rendered successfully <<<")

    # -------------------------------------------------------------------------
    # TEST 4: Numerical Distribution (histogram and box plot)
    # -------------------------------------------------------------------------
    log.info("\n=== TEST 4: Numerical Distribution Histogram & Box Plot PDF Report ===")
    orchestrator.reset_conversation()
    t4_events = []

    res4 = await orchestrator.process_message(
        "Generate a PDF report analyzing the distribution of order totals with a histogram and a box plot.",
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
    imgs4 = render_pdf_to_images(pdf4_path, "milestone10_test4_distribution")
    assert len(imgs4) >= 1
    log.info(">>> TEST 4 PASSED: Distribution report rendered successfully <<<")

    # -------------------------------------------------------------------------
    # TEST 5: Hierarchical Category Breakdown (treemap)
    # -------------------------------------------------------------------------
    log.info("\n=== TEST 5: Hierarchical Category Breakdown Treemap PDF Report ===")
    orchestrator.reset_conversation()
    t5_events = []

    res5 = await orchestrator.process_message(
        "Generate a PDF report displaying product category revenue breakdown using a treemap.",
        progress_callback=make_progress_logger("Test 5", t5_events),
    )
    log.info("Test 5 Status: %s", res5.status)
    assert res5.is_success, f"Test 5 failed: {res5.error}"
    assert len(res5.generated_reports) >= 1
    rep5 = res5.generated_reports[0]
    pdf5_path = Path(rep5["output_path"])
    log.info("Test 5 PDF Path: %s (%d bytes)", pdf5_path.name, rep5.get("file_size_bytes", 0))
    assert pdf5_path.is_file()
    assert rep5.get("charts_rendered", 0) >= 1
    imgs5 = render_pdf_to_images(pdf5_path, "milestone10_test5_treemap")
    assert len(imgs5) >= 1
    log.info(">>> TEST 5 PASSED: Treemap hierarchical report rendered successfully <<<")

    # -------------------------------------------------------------------------
    # TEST 6: Matrix Crosstab with Totals & Heatmap Cell Shading
    # -------------------------------------------------------------------------
    log.info("\n=== TEST 6: Matrix Crosstab with Totals & Heatmap PDF Report ===")
    orchestrator.reset_conversation()
    t6_events = []

    res6 = await orchestrator.process_message(
        "Generate a PDF report with a matrix showing order counts by month and order status, including row totals, column totals and a heatmap.",
        progress_callback=make_progress_logger("Test 6", t6_events),
    )
    log.info("Test 6 Status: %s", res6.status)
    assert res6.is_success, f"Test 6 failed: {res6.error}"
    assert len(res6.generated_reports) >= 1
    rep6 = res6.generated_reports[0]
    pdf6_path = Path(rep6["output_path"])
    log.info("Test 6 PDF Path: %s (%d bytes)", pdf6_path.name, rep6.get("file_size_bytes", 0))
    assert pdf6_path.is_file()
    imgs6 = render_pdf_to_images(pdf6_path, "milestone10_test6_matrix")
    assert len(imgs6) >= 1
    log.info(">>> TEST 6 PASSED: Matrix crosstab with totals & heatmap rendered successfully <<<")

    # -------------------------------------------------------------------------
    # TEST 7: Multi-Series Category Comparison Line Chart
    # -------------------------------------------------------------------------
    log.info("\n=== TEST 7: Multi-Series Line Chart PDF Report ===")
    orchestrator.reset_conversation()
    t7_events = []

    res7 = await orchestrator.process_message(
        "Generate a PDF comparing monthly revenue across different product categories using a multi-series line chart.",
        progress_callback=make_progress_logger("Test 7", t7_events),
    )
    log.info("Test 7 Status: %s", res7.status)
    assert res7.is_success, f"Test 7 failed: {res7.error}"
    assert len(res7.generated_reports) >= 1
    rep7 = res7.generated_reports[0]
    pdf7_path = Path(rep7["output_path"])
    log.info("Test 7 PDF Path: %s (%d bytes)", pdf7_path.name, rep7.get("file_size_bytes", 0))
    assert pdf7_path.is_file()
    assert rep7.get("charts_rendered", 0) >= 1
    imgs7 = render_pdf_to_images(pdf7_path, "milestone10_test7_multiseries")
    assert len(imgs7) >= 1
    log.info(">>> TEST 7 PASSED: Multi-series line chart rendered successfully <<<")

    # -------------------------------------------------------------------------
    # TEST 8: SQL Appendix Included on Explicit Request
    # -------------------------------------------------------------------------
    log.info("\n=== TEST 8: SQL Appendix Included on Explicit Request ===")
    orchestrator.reset_conversation()
    t8_events = []

    res8 = await orchestrator.process_message(
        "Generate a PDF report of total revenue by month and include the executed SQL queries in a final appendix.",
        progress_callback=make_progress_logger("Test 8", t8_events),
    )
    log.info("Test 8 Status: %s", res8.status)
    assert res8.is_success, f"Test 8 failed: {res8.error}"
    assert len(res8.generated_reports) >= 1
    rep8 = res8.generated_reports[0]
    pdf8_path = Path(rep8["output_path"])
    log.info("Test 8 PDF Path: %s (%d bytes)", pdf8_path.name, rep8.get("file_size_bytes", 0))
    assert pdf8_path.is_file()
    pdf8_text = _extract_pdf_text(pdf8_path)
    assert "Appendix" in pdf8_text, "Expected SQL Appendix in output when explicitly requested!"
    imgs8 = render_pdf_to_images(pdf8_path, "milestone10_test8_sql_appendix")
    assert len(imgs8) >= 1
    log.info(">>> TEST 8 PASSED: SQL Appendix rendered when explicitly requested <<<")

    # -------------------------------------------------------------------------
    # TEST 9: CSV Export
    # -------------------------------------------------------------------------
    log.info("\n=== TEST 9: CSV Export ===")
    orchestrator.reset_conversation()
    t9_events = []

    res9 = await orchestrator.process_message(
        "Export monthly order counts and revenue to CSV.",
        progress_callback=make_progress_logger("Test 9", t9_events),
    )
    log.info("Test 9 Status: %s", res9.status)
    assert res9.is_success, f"Test 9 failed: {res9.error}"
    assert len(res9.generated_reports) >= 1
    rep9 = res9.generated_reports[0]
    csv_path = Path(rep9["output_path"])
    log.info("Test 9 CSV Path: %s (%d bytes, Format: %s)", csv_path.name, rep9.get("file_size_bytes", 0), rep9.get("output_format"))
    assert csv_path.is_file()
    assert rep9.get("output_format") == "CSV"
    assert rep9.get("record_count", 0) > 0
    log.info(">>> TEST 9 PASSED: CSV export generated successfully <<<")

    # Clean shutdown
    await orchestrator.close()

    # Final DB sha256 verification
    final_sha = hashlib.sha256(db_file.read_bytes()).hexdigest()
    assert initial_sha == final_sha, f"Database was modified! Initial: {initial_sha}, Final: {final_sha}"
    log.info("Final database SHA-256 match verified: %s", final_sha)

    log.info("\n==================================================================")
    log.info("🏆 ALL 9 MILESTONE 10 ACCEPTANCE TESTS COMPLETED SUCCESSFULLY!")
    log.info("==================================================================")


if __name__ == "__main__":
    asyncio.run(run_milestone10_acceptance_tests())

