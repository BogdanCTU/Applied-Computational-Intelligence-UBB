"""Unit tests for stage-specific context relevance, schema filtering, and selective skill loading."""

from __future__ import annotations

import pytest

from agent.context_builder import ContextBuilder
from agent.context_models import ExecutionStage
from agent.skill_manager import SkillManager
from database.schema_inspector import ColumnInfo, DatabaseSchema, ForeignKeyInfo, TableSchema


def _make_sample_database_schema() -> DatabaseSchema:
    """Create multi-table mock schema for testing filtering."""
    orders_table = TableSchema(
        name="orders",
        columns=[
            ColumnInfo("order_id", "INTEGER", "INTEGER", True, None, True, 1),
            ColumnInfo("customer_id", "INTEGER", "INTEGER", True, None, False, 0),
            ColumnInfo("order_date", "TEXT", "TEXT", True, None, False, 0),
            ColumnInfo("total_amount", "REAL", "REAL", True, None, False, 0),
        ],
        primary_keys=["order_id"],
        foreign_keys=[ForeignKeyInfo(1, 0, "customer_id", "customers", "customer_id", "NO ACTION", "NO ACTION")],
        indexes=[],
        row_count=1000,
    )
    customers_table = TableSchema(
        name="customers",
        columns=[
            ColumnInfo("customer_id", "INTEGER", "INTEGER", True, None, True, 1),
            ColumnInfo("customer_name", "TEXT", "TEXT", True, None, False, 0),
            ColumnInfo("city", "TEXT", "TEXT", False, None, False, 0),
        ],
        primary_keys=["customer_id"],
        foreign_keys=[],
        indexes=[],
        row_count=500,
    )
    products_table = TableSchema(
        name="products",
        columns=[
            ColumnInfo("product_id", "INTEGER", "INTEGER", True, None, True, 1),
            ColumnInfo("product_name", "TEXT", "TEXT", True, None, False, 0),
            ColumnInfo("unit_price", "REAL", "REAL", True, None, False, 0),
        ],
        primary_keys=["product_id"],
        foreign_keys=[],
        indexes=[],
        row_count=200,
    )
    return DatabaseSchema(
        database_path="/dummy/ecommerce.db",
        table_count=3,
        total_rows=1700,
        tables=[orders_table, customers_table, products_table],
        relationships=[],
    )


def test_schema_filtering_by_relevant_tables() -> None:
    builder = ContextBuilder()
    full_schema = _make_sample_database_schema()

    # Request only orders and customers
    ctx = builder.build(
        ExecutionStage.SQL_GENERATION,
        user_request="Find customer orders",
        schema=full_schema,
        relevant_tables=["orders", "customers"],
    )

    assert "Table: orders" in ctx.system_prompt
    assert "Table: customers" in ctx.system_prompt
    # products should not appear in the filtered schema
    assert "Table: products" not in ctx.system_prompt


def test_schema_unfiltered_when_no_relevant_tables_specified() -> None:
    builder = ContextBuilder()
    full_schema = _make_sample_database_schema()

    ctx = builder.build(
        ExecutionStage.SCHEMA_DISCOVERY,
        user_request="Inspect all tables",
        schema=full_schema,
    )

    assert "Table: orders" in ctx.system_prompt
    assert "Table: customers" in ctx.system_prompt
    assert "Table: products" in ctx.system_prompt


def test_skill_relevance_per_stage() -> None:
    skill_mgr = SkillManager()
    builder = ContextBuilder(skill_manager=skill_mgr)

    # 1. SQL_GENERATION should include sql_generation, NOT report_design
    sql_ctx = builder.build(ExecutionStage.SQL_GENERATION, user_request="Generate SQL query")
    assert "skill_sql_generation" in sql_ctx.report.included_sections
    assert "skill_report_design" not in sql_ctx.report.included_sections

    # 2. DATA_ANALYSIS should include ecommerce_analysis, NOT report_design
    analysis_ctx = builder.build(ExecutionStage.DATA_ANALYSIS, user_request="Analyze data")
    assert "skill_ecommerce_analysis" in analysis_ctx.report.included_sections
    assert "skill_report_design" not in analysis_ctx.report.included_sections

    # 3. CHART_PLANNING should include report_design
    chart_ctx = builder.build(ExecutionStage.CHART_PLANNING, user_request="Choose charts")
    assert "skill_report_design" in chart_ctx.report.included_sections

    # 4. REQUEST_PLANNING should not load heavy report design or SQL skills by default
    plan_ctx = builder.build(ExecutionStage.REQUEST_PLANNING, user_request="Plan execution")
    assert "skill_report_design" not in plan_ctx.report.included_sections


def test_semantic_facts_relevance_and_formatting() -> None:
    builder = ContextBuilder()
    facts = [
        {"key": "AOV", "value": "Average Order Value = Total Net Sales / Order Count"},
        {"key": "Return_Window", "value": "Returns permitted within 30 days of delivery"},
    ]
    ctx = builder.build(
        ExecutionStage.SQL_GENERATION,
        user_request="Calculate AOV",
        semantic_facts=facts,
    )
    assert "DOMAIN KNOWLEDGE & BUSINESS DEFINITIONS:" in ctx.system_prompt
    assert "AOV: Average Order Value" in ctx.system_prompt
    assert "Return_Window: Returns permitted within 30 days" in ctx.system_prompt
    assert "semantic_facts" in ctx.report.included_sections


def test_custom_explicit_skills_override() -> None:
    skill_mgr = SkillManager()
    builder = ContextBuilder(skill_manager=skill_mgr)

    # Explicitly load data_validation in SQL_GENERATION even though not default
    ctx = builder.build(
        ExecutionStage.SQL_GENERATION,
        user_request="Generate and validate SQL",
        skills=["data_validation"],
    )
    assert "skill_data_validation" in ctx.report.included_sections
