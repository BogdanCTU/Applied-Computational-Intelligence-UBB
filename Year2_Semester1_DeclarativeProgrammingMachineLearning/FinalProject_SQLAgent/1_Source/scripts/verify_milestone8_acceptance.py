"""Milestone 8 Acceptance Verification Script.

Executes all 6 acceptance scenarios against the live local Ollama model (qwen3.5:4b)
and MCP server to verify end-to-end functionality, SQL approval gates, activity events,
and dynamic report generation.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from agent import ActivityCategory, AgentEvent, AgentOrchestrator
from config.settings import AppSettings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("acceptance_verifier")


async def run_acceptance_tests() -> None:
    settings = AppSettings()
    settings.agent.require_sql_approval = True
    log.info("Starting Milestone 8 Acceptance Verification with model: %s", settings.ollama.model)

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
    # Acceptance Test 1: "Show me the top 10 products by revenue." (Approve SQL)
    # -------------------------------------------------------------------------
    log.info("\n=== TEST 1: Top 10 products by revenue (Approved) ===")
    orchestrator.reset_conversation()
    t1_approved_queries = []
    t1_events = []

    def t1_approval(sql_text: str, exp: str) -> bool:
        log.info("Test 1 Approval Requested for SQL:\n%s", sql_text)
        t1_approved_queries.append(sql_text)
        assert bool(sql_text.strip()), "SQL query must not be empty!"
        return True

    res1 = await orchestrator.process_message(
        "Show me the top 10 products by revenue.",
        approval_callback=t1_approval,
        progress_callback=make_progress_logger("Test 1", t1_events),
    )
    log.info("Test 1 Result Status: %s", res1.status)
    log.info("Test 1 Final Message: %s", res1.final_message[:100])
    assert res1.is_success, f"Test 1 failed with status {res1.status}: {res1.error}"
    assert len(t1_approved_queries) >= 1, "Expected at least 1 SQL approval request"
    assert any(e.category == ActivityCategory.SQL_VALIDATION.value for e in t1_events)
    assert any(e.category == ActivityCategory.APPROVAL_RESULT.value and e.status == "success" for e in t1_events)
    log.info(">>> TEST 1 PASSED <<<")

    # -------------------------------------------------------------------------
    # Acceptance Test 2: "Show me a summary of orders by status." (Reject SQL)
    # -------------------------------------------------------------------------
    log.info("\n=== TEST 2: Summary of orders by status (Rejected) ===")
    orchestrator.reset_conversation()
    t2_rejections = []
    t2_events = []

    def t2_approval(sql_text: str, exp: str) -> bool:
        log.info("Test 2 Approval Requested for SQL (Simulating User Rejection):\n%s", sql_text)
        t2_rejections.append(sql_text)
        return False

    res2 = await orchestrator.process_message(
        "Show me a summary of orders by status.",
        approval_callback=t2_approval,
        progress_callback=make_progress_logger("Test 2", t2_events),
    )
    log.info("Test 2 Result Status: %s", res2.status)
    assert res2.status == "approval_denied" or "denied" in res2.final_message.lower(), "Execution must be blocked on rejection"
    assert len(t2_rejections) >= 1, "Expected approval request before rejection"
    assert any(e.category == ActivityCategory.APPROVAL_RESULT.value and e.status == "rejected" for e in t2_events)
    log.info(">>> TEST 2 PASSED <<<")

    # -------------------------------------------------------------------------
    # Acceptance Test 3: PDF with historical chart, pie chart, tables
    # -------------------------------------------------------------------------
    log.info("\n=== TEST 3: PDF with historical chart and pie chart ===")
    orchestrator.reset_conversation()
    t3_events = []

    res3 = await orchestrator.process_message(
        "Produce me a PDF report containing a historical chart of orders, a pie chart of order distribution, and some tables regarding order data.",
        approval_callback=lambda q, e: True,
        progress_callback=make_progress_logger("Test 3", t3_events),
    )
    log.info("Test 3 Status: %s", res3.status)
    assert res3.is_success, f"Test 3 failed: {res3.error}"
    assert len(res3.generated_reports) >= 1, "Expected generated PDF report"
    rep3 = res3.generated_reports[0]
    log.info("Test 3 Report Path: %s (Size: %d bytes)", rep3.get("output_path"), rep3.get("file_size_bytes", 0))
    assert Path(rep3["output_path"]).is_file()
    assert rep3.get("output_format") == "PDF"
    log.info(">>> TEST 3 PASSED <<<")

    # -------------------------------------------------------------------------
    # Acceptance Test 4: Multi-series line chart PDF report
    # -------------------------------------------------------------------------
    log.info("\n=== TEST 4: Multi-series line chart PDF report ===")
    orchestrator.reset_conversation()
    t4_events = []

    res4 = await orchestrator.process_message(
        "Generate a PDF comparing monthly revenue across different product categories using a multi-series line chart and a summary table.",
        approval_callback=lambda q, e: True,
        progress_callback=make_progress_logger("Test 4", t4_events),
    )
    log.info("Test 4 Status: %s", res4.status)
    assert res4.is_success, f"Test 4 failed: {res4.error}"
    assert len(res4.generated_reports) >= 1
    rep4 = res4.generated_reports[0]
    log.info("Test 4 Report Path: %s (Size: %d bytes)", rep4.get("output_path"), rep4.get("file_size_bytes", 0))
    assert Path(rep4["output_path"]).is_file()
    log.info(">>> TEST 4 PASSED <<<")

    # -------------------------------------------------------------------------
    # Acceptance Test 5: Explicit SQL inclusion in appendix
    # -------------------------------------------------------------------------
    log.info("\n=== TEST 5: Top 10 products with SQL in Appendix ===")
    orchestrator.reset_conversation()
    t5_events = []

    res5 = await orchestrator.process_message(
        "Generate a PDF with the top 10 products by revenue, including the SQL queries used in a final appendix.",
        approval_callback=lambda q, e: True,
        progress_callback=make_progress_logger("Test 5", t5_events),
    )
    log.info("Test 5 Status: %s", res5.status)
    assert res5.is_success, f"Test 5 failed: {res5.error}"
    assert len(res5.generated_reports) >= 1
    rep5 = res5.generated_reports[0]
    log.info("Test 5 Report Path: %s (Size: %d bytes)", rep5.get("output_path"), rep5.get("file_size_bytes", 0))
    assert Path(rep5["output_path"]).is_file()
    log.info(">>> TEST 5 PASSED <<<")

    # -------------------------------------------------------------------------
    # Acceptance Test 6: CSV Export
    # -------------------------------------------------------------------------
    log.info("\n=== TEST 6: CSV Export monthly orders and revenue ===")
    orchestrator.reset_conversation()
    t6_events = []

    res6 = await orchestrator.process_message(
        "Export a CSV containing monthly order counts and revenue.",
        approval_callback=lambda q, e: True,
        progress_callback=make_progress_logger("Test 6", t6_events),
    )
    log.info("Test 6 Status: %s", res6.status)
    assert res6.is_success, f"Test 6 failed: {res6.error}"
    assert len(res6.generated_reports) >= 1
    rep6 = res6.generated_reports[0]
    log.info("Test 6 Report Path: %s (Format: %s, Records: %d)", rep6.get("output_path"), rep6.get("output_format"), rep6.get("record_count", 0))
    assert Path(rep6["output_path"]).is_file()
    assert rep6.get("output_format") == "CSV"
    log.info(">>> TEST 6 PASSED <<<")

    await orchestrator.close()
    log.info("\n🎉 ALL 6 ACCEPTANCE TESTS COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(run_acceptance_tests())
