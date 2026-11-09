"""Context Builder with internal token budgeting and stage-specific context assembly.

Assembles minimal, stage-specific context profiles for local LLMs (e.g. qwen3.5:4b)
under a strict token budget. Prioritizes mandatory sections, handles untrusted inputs safely,
integrates skills and memory, and produces structured build audit reports.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Sequence

from agent.checkpoint_models import TaskCheckpoint
from agent.context_models import (
    AssembledContext,
    ContextBuildReport,
    ContextBudgetExceededError,
    ContextComponentBreakdown,
    ContextError,
    ContextSection,
    ExcludedSection,
    ExecutionStage,
    InvalidStageError,
    SectionPriority,
)
from agent.skill_models import LoadedSkill, estimate_tokens
from agent.system_prompt import _format_discovered_tools_section, build_system_prompt
from agent.task_models import AgentTask, TaskStep
from config.settings import DEFAULT_CONTEXT_WINDOW, AppSettings, load_settings
from database.schema_inspector import DatabaseSchema

log = logging.getLogger(__name__)

# Default stage-to-skills mapping
STAGE_SKILL_MAP: dict[ExecutionStage, list[str]] = {
    ExecutionStage.REQUEST_PLANNING: [],
    ExecutionStage.SCHEMA_DISCOVERY: ["sql_generation"],
    ExecutionStage.SQL_GENERATION: ["sql_generation"],
    ExecutionStage.SQL_VALIDATION: ["data_validation"],
    ExecutionStage.DATA_ANALYSIS: ["ecommerce_analysis"],
    ExecutionStage.CHART_PLANNING: ["report_design"],
    ExecutionStage.REPORT_GENERATION: ["data_validation", "report_design"],
    ExecutionStage.FINAL_RESPONSE: [],
}

# Standard stage instructions
STAGE_INSTRUCTIONS: dict[ExecutionStage, str] = {
    ExecutionStage.REQUEST_PLANNING: (
        "TASK PLANNING STAGE:\n"
        "Analyze the user request and database schema. Generate a clear, structured sequence of execution steps "
        "with dependencies and required MCP tools (`inspect_database_schema`, `prepare_sql_query`, "
        "`execute_readonly_sql`, `generate_pdf_report`, `generate_csv_report`)."
    ),
    ExecutionStage.SCHEMA_DISCOVERY: (
        "SCHEMA DISCOVERY STAGE:\n"
        "Call `inspect_database_schema` with `table_name='ALL'` (or `get_table_sample` if needed) to inspect "
        "table structures, primary keys, date ranges, and relationships. Identify the tables and columns "
        "needed to satisfy the user request."
    ),
    ExecutionStage.SQL_GENERATION: (
        "SQL GENERATION STAGE:\n"
        "Generate a single, syntactically correct, strictly read-only SQLite query and validate it by calling "
        "`prepare_sql_query`. Adhere to SQLite idioms: use explicit column projections (no SELECT *), "
        "qualified table names, and `strftime` for date operations. Once validated, call `execute_readonly_sql`."
    ),
    ExecutionStage.SQL_VALIDATION: (
        "SQL VALIDATION STAGE:\n"
        "Verify with `prepare_sql_query` that the proposed SQL query is strictly read-only, references existing "
        "tables/columns, has no dangerous side-effects, and safely answers the original question, then call "
        "`execute_readonly_sql`."
    ),
    ExecutionStage.DATA_ANALYSIS: (
        "DATA ANALYSIS STAGE:\n"
        "Analyze the validated SQL query results. Verify metric definitions, compute key performance "
        "indicators, identify trends, and proceed to call `generate_pdf_report` (or `generate_csv_report` if CSV was explicitly requested)."
    ),
    ExecutionStage.CHART_PLANNING: (
        "CHART PLANNING STAGE:\n"
        "Select the most appropriate visual chart type(s) representing the data and invoke `generate_pdf_report` "
        "to render the executive PDF report with charts, KPIs, and data tables."
    ),
    ExecutionStage.REPORT_GENERATION: (
        "REPORT GENERATION STAGE:\n"
        "Call `generate_pdf_report` (default) or `generate_csv_report` (only if CSV was explicitly requested) "
        "with a clear `title` and `description`. Ensure numerical reconciliation with CanonicalSQLDataset."
    ),
    ExecutionStage.FINAL_RESPONSE: (
        "FINAL SYNTHESIS STAGE:\n"
        "Provide a clear, executive-level natural language summary answering the user's initial request. "
        "Reference the generated report file path and highlight key quantitative findings from the SQL results."
    ),
}


class ContextBuilder:
    """Assembles stage-specific context profiles with internal token budget enforcement."""

    def __init__(
        self,
        settings: AppSettings | None = None,
        *,
        skill_manager: Any | None = None,
        memory_repo: Any | None = None,
        schema_provider: Callable[[], str | DatabaseSchema] | str | DatabaseSchema | None = None,
        tool_registry: Any | None = None,
        tool_mode: str = "native",
        num_ctx: int | None = None,
        reserved_output_tokens: int = 1024,
        safety_margin_tokens: int = 256,
    ) -> None:
        self.settings = settings or load_settings()
        self.skill_manager = skill_manager
        self.memory_repo = memory_repo
        self.schema_provider = schema_provider
        self.tool_registry = tool_registry
        self.tool_mode = tool_mode

        # Centralized token configuration
        configured_limit = (
            getattr(self.settings.agent, "agent_context_window", None)
            or getattr(self.settings.ollama, "num_ctx", None)
            or DEFAULT_CONTEXT_WINDOW
        )
        self.num_ctx = int(num_ctx or configured_limit)
        self.reserved_output_tokens = max(128, int(reserved_output_tokens))
        self.safety_margin_tokens = max(64, int(safety_margin_tokens))

    # -----------------------------------------------------------------------
    # Primary Assembly Methods
    # -----------------------------------------------------------------------

    def build(
        self,
        stage: ExecutionStage | str,
        *,
        user_request: str | None = None,
        task: AgentTask | None = None,
        active_step: TaskStep | None = None,
        checkpoint: TaskCheckpoint | None = None,
        skills: list[LoadedSkill] | list[str] | None = None,
        schema: DatabaseSchema | str | dict[str, Any] | None = None,
        relevant_tables: list[str] | None = None,
        semantic_facts: list[Any] | None = None,
        working_memory: dict[str, Any] | None = None,
        tool_results: list[dict[str, Any]] | list[str] | None = None,
        conversation_history: Sequence[Any] | None = None,
        proposed_sql: str | None = None,
        dataset_summary: dict[str, Any] | str | None = None,
        custom_sections: list[ContextSection] | None = None,
        tool_mode: str | None = None,
        discovered_tools: Any | None = None,
        reporting_period: dict[str, str] | None = None,
        reserved_output_tokens: int | None = None,
        safety_margin_tokens: int | None = None,
        num_ctx_override: int | None = None,
        effective_context_window: int | None = None,
        configured_context_window: int | None = None,
        model_validation_status: str | None = None,
    ) -> AssembledContext:
        """Construct a stage-specific context profile governed by token budgets."""
        exec_stage = self._normalize_stage(stage)

        # 1. Calculate budget limits
        total_num_ctx = effective_context_window or num_ctx_override or self.num_ctx
        conf_window = (
            configured_context_window
            or getattr(self.settings.agent, "agent_context_window", None)
            or total_num_ctx
        )
        val_status = model_validation_status or "compatible"

        res_output = (
            reserved_output_tokens
            if reserved_output_tokens is not None
            else self.reserved_output_tokens
        )
        safe_margin = (
            safety_margin_tokens
            if safety_margin_tokens is not None
            else self.safety_margin_tokens
        )
        avail_input = self._compute_available_budget(total_num_ctx, res_output, safe_margin)

        # 2. Gather candidate sections for the stage
        candidate_sections = self._collect_stage_sections(
            stage=exec_stage,
            user_request=user_request,
            task=task,
            active_step=active_step,
            checkpoint=checkpoint,
            skills=skills,
            schema=schema,
            relevant_tables=relevant_tables,
            semantic_facts=semantic_facts,
            working_memory=working_memory,
            tool_results=tool_results,
            conversation_history=conversation_history,
            proposed_sql=proposed_sql,
            dataset_summary=dataset_summary,
            custom_sections=custom_sections,
            tool_mode=tool_mode,
            discovered_tools=discovered_tools,
            reporting_period=reporting_period,
        )

        # 3. Filter sections through internal token budget allocator
        admitted, excluded, warnings = self._allocate_budget(candidate_sections, avail_input)

        # 4. Partition admitted sections into system prompt and user prompt
        system_content, user_content = self._assemble_prompts(admitted)

        # 5. Build component breakdown and audit report
        breakdown = self._calculate_component_breakdown(admitted)
        estimated_input = sum(s.estimated_tokens for s in admitted)
        remaining = max(0, avail_input - estimated_input)

        report = ContextBuildReport(
            stage=exec_stage,
            num_ctx=total_num_ctx,
            configured_context_window=conf_window,
            effective_context_window=total_num_ctx,
            reserved_output_tokens=res_output,
            safety_margin_tokens=safe_margin,
            available_input_tokens=avail_input,
            estimated_input_tokens=estimated_input,
            remaining_tokens=remaining,
            component_breakdown=breakdown.to_dict(),
            included_sections=[s.name for s in admitted],
            included_categories=sorted(list({s.category for s in admitted})),
            excluded_sections=excluded,
            excluded_categories=sorted(list({s.category for s in excluded})),
            exclusion_reasons=[e.reason for e in excluded],
            model_validation_status=val_status,
            warnings=warnings,
        )

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

        return AssembledContext(
            stage=exec_stage,
            system_prompt=system_content,
            user_prompt=user_content,
            messages=messages,
            report=report,
        )

    def build_messages(
        self,
        stage: ExecutionStage | str,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Convenience helper returning Ollama-compatible message dicts."""
        assembled = self.build(stage, **kwargs)
        return assembled.messages

    def build_prompt(
        self,
        stage: ExecutionStage | str,
        **kwargs: Any,
    ) -> str:
        """Convenience helper returning concatenated system and user prompts."""
        assembled = self.build(stage, **kwargs)
        return f"{assembled.system_prompt}\n\n---\n\n{assembled.user_prompt}"

    # -----------------------------------------------------------------------
    # Budget Management & Token Allocation (Internal)
    # -----------------------------------------------------------------------

    def _compute_available_budget(
        self,
        total_num_ctx: int,
        reserved_output: int,
        safety_margin: int,
    ) -> int:
        """Compute maximum token space available for input context."""
        avail = total_num_ctx - reserved_output - safety_margin
        if avail <= 0:
            raise ContextBudgetExceededError(
                f"Configured context ({total_num_ctx}) is too small to satisfy "
                f"reserved output ({reserved_output}) and safety margin ({safety_margin})."
            )
        return avail

    def _allocate_budget(
        self,
        sections: list[ContextSection],
        available_budget: int,
    ) -> tuple[list[ContextSection], list[ExcludedSection], list[str]]:
        """Admit or exclude sections based on priority without partial truncation.

        Mandatory sections MUST fit. If they exceed available_budget, ContextBudgetExceededError is raised.
        Optional sections are admitted strictly in order of priority (MANDATORY > HIGH > MEDIUM > LOW).
        """
        warnings: list[str] = []

        # Check mandatory sections
        mandatory_sections = [s for s in sections if s.is_mandatory]
        mandatory_tokens = sum(s.estimated_tokens for s in mandatory_sections)

        if mandatory_tokens > available_budget:
            raise ContextBudgetExceededError(
                f"Mandatory context sections require {mandatory_tokens} tokens, "
                f"which exceeds the available input budget of {available_budget} tokens."
            )

        admitted: list[ContextSection] = []
        excluded: list[ExcludedSection] = []
        current_tokens = 0

        # Mandatory sections are admitted first
        for s in mandatory_sections:
            admitted.append(s)
            current_tokens += s.estimated_tokens

        # Sort optional sections by priority descending, then name for deterministic tie-breaking
        optional_sections = [s for s in sections if not s.is_mandatory]
        optional_sections.sort(key=lambda s: (-s.priority.value, s.name))

        for s in optional_sections:
            if current_tokens + s.estimated_tokens <= available_budget:
                admitted.append(s)
                current_tokens += s.estimated_tokens
            else:
                reason = (
                    f"Token budget exceeded (section requires {s.estimated_tokens} tokens, "
                    f"remaining budget is {available_budget - current_tokens})."
                )
                excluded.append(
                    ExcludedSection(
                        name=s.name,
                        category=s.category,
                        priority=s.priority,
                        estimated_tokens=s.estimated_tokens,
                        reason=reason,
                    )
                )
                warnings.append(
                    f"Optional section '{s.name}' ({s.estimated_tokens} tokens) excluded due to token budget constraint."
                )
                log.debug("Excluding optional section '%s' (%d tokens): %s", s.name, s.estimated_tokens, reason)

        if (available_budget - current_tokens) < max(100, int(0.1 * available_budget)):
            warnings.append(
                f"Available input token budget nearly exhausted ({available_budget - current_tokens} tokens remaining)."
            )

        return admitted, excluded, warnings

    def _calculate_component_breakdown(
        self,
        admitted: list[ContextSection],
    ) -> ContextComponentBreakdown:
        """Sum tokens per category bucket."""
        breakdown = ContextComponentBreakdown()
        for s in admitted:
            cat = s.category
            tokens = s.estimated_tokens
            if hasattr(breakdown, cat):
                setattr(breakdown, cat, getattr(breakdown, cat) + tokens)
            else:
                breakdown.other += tokens
        return breakdown

    # -----------------------------------------------------------------------
    # Stage Section Collectors (Internal)
    # -----------------------------------------------------------------------

    def _collect_stage_sections(
        self,
        stage: ExecutionStage,
        *,
        user_request: str | None,
        task: AgentTask | None,
        active_step: TaskStep | None,
        checkpoint: TaskCheckpoint | None,
        skills: list[LoadedSkill] | list[str] | None,
        schema: DatabaseSchema | str | dict[str, Any] | None,
        relevant_tables: list[str] | None,
        semantic_facts: list[Any] | None,
        working_memory: dict[str, Any] | None,
        tool_results: list[dict[str, Any]] | list[str] | None,
        conversation_history: Sequence[Any] | None = None,
        proposed_sql: str | None,
        dataset_summary: dict[str, Any] | str | None,
        custom_sections: list[ContextSection] | None,
        tool_mode: str | None = None,
        discovered_tools: Any | None = None,
        reporting_period: dict[str, str] | None = None,
    ) -> list[ContextSection]:
        """Gather candidate context sections for the given execution stage."""
        sections: list[ContextSection] = []

        # 1. Base System Instructions (Mandatory)
        sys_text = self._build_base_system_instructions(
            tool_mode=tool_mode,
            reporting_period=reporting_period,
        )
        sections.append(
            ContextSection(
                name="system_instructions",
                content=sys_text,
                priority=SectionPriority.MANDATORY,
                is_mandatory=True,
                category="system_instructions",
                estimated_tokens=estimate_tokens(sys_text),
            )
        )

        # 1b. Discovered MCP Tools Registry Summary (High Priority)
        active_registry = discovered_tools if discovered_tools is not None else self.tool_registry
        tools_summary = _format_discovered_tools_section(active_registry)
        if tools_summary:
            sections.append(
                ContextSection(
                    name="discovered_mcp_tools",
                    content=tools_summary,
                    priority=SectionPriority.HIGH,
                    is_mandatory=False,
                    category="system_instructions",
                    estimated_tokens=estimate_tokens(tools_summary),
                )
            )

        # 2. Stage Instructions (Mandatory)
        stage_text = STAGE_INSTRUCTIONS.get(stage, f"STAGE: {stage.value}")
        sections.append(
            ContextSection(
                name="stage_instructions",
                content=stage_text,
                priority=SectionPriority.MANDATORY,
                is_mandatory=True,
                category="system_instructions",
                estimated_tokens=estimate_tokens(stage_text),
            )
        )

        # 3. Stage Skills (High priority)
        skill_sections = self._resolve_skills_for_stage(stage, skills)
        sections.extend(skill_sections)

        # 4. Database Schema (High priority for SQL/Schema/Planning)
        schema_text = self._resolve_schema_text(stage, schema, relevant_tables)
        if schema_text:
            prio = (
                SectionPriority.HIGH
                if stage in (ExecutionStage.SQL_GENERATION, ExecutionStage.SCHEMA_DISCOVERY, ExecutionStage.REQUEST_PLANNING)
                else SectionPriority.MEDIUM
            )
            sections.append(
                ContextSection(
                    name="database_schema",
                    content=schema_text,
                    priority=prio,
                    is_mandatory=False,
                    category="database_schema",
                    estimated_tokens=estimate_tokens(schema_text),
                )
            )

        # 5. Proposed SQL (Mandatory for SQL Validation)
        if proposed_sql:
            sql_text = f"PROPOSED SQL QUERY:\n```sql\n{proposed_sql.strip()}\n```"
            is_mand = (stage == ExecutionStage.SQL_VALIDATION)
            prio = SectionPriority.MANDATORY if is_mand else SectionPriority.HIGH
            sections.append(
                ContextSection(
                    name="proposed_sql",
                    content=sql_text,
                    priority=prio,
                    is_mandatory=is_mand,
                    category="task_and_checkpoint",
                    estimated_tokens=estimate_tokens(sql_text),
                )
            )

        # 6. Dataset Summary (High for Analysis and Chart Planning)
        if dataset_summary:
            ds_text = self._format_dataset_summary(dataset_summary)
            is_mand = stage in (ExecutionStage.DATA_ANALYSIS, ExecutionStage.CHART_PLANNING)
            sections.append(
                ContextSection(
                    name="dataset_summary",
                    content=ds_text,
                    priority=SectionPriority.HIGH if not is_mand else SectionPriority.MANDATORY,
                    is_mandatory=is_mand,
                    category="tool_results",
                    estimated_tokens=estimate_tokens(ds_text),
                )
            )

        # 7. Task and Active Step Context (Medium to High)
        if task or active_step:
            task_text = self._format_task_state(task, active_step)
            sections.append(
                ContextSection(
                    name="task_state",
                    content=task_text,
                    priority=SectionPriority.HIGH if active_step else SectionPriority.MEDIUM,
                    is_mandatory=False,
                    category="task_and_checkpoint",
                    estimated_tokens=estimate_tokens(task_text),
                )
            )

        # 8. Checkpoint State (Medium)
        if checkpoint:
            chk_text = self._format_checkpoint_state(checkpoint)
            sections.append(
                ContextSection(
                    name="checkpoint_state",
                    content=chk_text,
                    priority=SectionPriority.MEDIUM,
                    is_mandatory=False,
                    category="task_and_checkpoint",
                    estimated_tokens=estimate_tokens(chk_text),
                )
            )

        # 9. Working Memory (Medium)
        wm_data = working_memory or self._query_working_memory(task)
        if wm_data:
            wm_text = f"WORKING MEMORY VARIABLES:\n{json.dumps(wm_data, indent=2, sort_keys=True)}"
            sections.append(
                ContextSection(
                    name="working_memory",
                    content=wm_text,
                    priority=SectionPriority.MEDIUM,
                    is_mandatory=False,
                    category="working_memory",
                    estimated_tokens=estimate_tokens(wm_text),
                )
            )

        # 10. Semantic Facts (Low to Medium)
        facts = semantic_facts or self._query_semantic_facts(stage, relevant_tables)
        if facts:
            fact_text = self._format_semantic_facts(facts)
            sections.append(
                ContextSection(
                    name="semantic_facts",
                    content=fact_text,
                    priority=SectionPriority.LOW,
                    is_mandatory=False,
                    category="semantic_memory",
                    estimated_tokens=estimate_tokens(fact_text),
                )
            )

        # 11. Tool Results (Medium)
        if tool_results:
            tr_text = self._format_tool_results(tool_results)
            sections.append(
                ContextSection(
                    name="tool_results",
                    content=tr_text,
                    priority=SectionPriority.MEDIUM,
                    is_mandatory=False,
                    category="tool_results",
                    estimated_tokens=estimate_tokens(tr_text),
                )
            )

        # 12. Conversation History (Low to Medium)
        if conversation_history:
            history_sections = self._format_conversation_history(conversation_history)
            sections.extend(history_sections)

        # 13. Custom Sections (Variable)
        if custom_sections:
            for cs in custom_sections:
                if cs.estimated_tokens <= 0:
                    cs.estimated_tokens = estimate_tokens(cs.content)
                sections.append(cs)

        # 14. User Request (Mandatory)
        effective_request = (
            user_request
            or (task.user_request if task else None)
            or (active_step.description if active_step else "Execute requested stage.")
        )
        safe_req_text = self._sanitize_user_input(effective_request)
        sections.append(
            ContextSection(
                name="user_request",
                content=safe_req_text,
                priority=SectionPriority.MANDATORY,
                is_mandatory=True,
                category="user_request",
                estimated_tokens=estimate_tokens(safe_req_text),
            )
        )

        # Duplicate context elimination: ensure unique section names and unique content
        unique_sections: list[ContextSection] = []
        seen_names: set[str] = set()
        seen_contents: set[str] = set()

        for s in sections:
            c_norm = s.content.strip()
            if s.name in seen_names or c_norm in seen_contents:
                log.debug("Eliminating duplicate context section: '%s'", s.name)
                continue
            seen_names.add(s.name)
            seen_contents.add(c_norm)
            unique_sections.append(s)

        return unique_sections

    # -----------------------------------------------------------------------
    # Helpers: Formatting & Resolution (Internal)
    # -----------------------------------------------------------------------

    def _normalize_stage(self, stage: ExecutionStage | str) -> ExecutionStage:
        """Convert input string to ExecutionStage enum."""
        if isinstance(stage, ExecutionStage):
            return stage
        try:
            return ExecutionStage(stage.strip().upper())
        except (ValueError, AttributeError):
            valid_names = [e.value for e in ExecutionStage]
            raise InvalidStageError(
                f"Unknown execution stage '{stage}'. Must be one of: {valid_names}"
            )

    def _build_base_system_instructions(
        self,
        *,
        tool_mode: str | None = None,
        reporting_period: dict[str, str] | None = None,
    ) -> str:
        """Construct capability-aware system instructions via build_system_prompt."""
        active_mode = tool_mode or self.tool_mode or "native"
        return build_system_prompt(
            self.settings,
            tool_mode=active_mode,
            reporting_period=reporting_period,
        )

    def _resolve_skills_for_stage(
        self,
        stage: ExecutionStage,
        explicit_skills: list[LoadedSkill] | list[str] | None,
    ) -> list[ContextSection]:
        """Retrieve and format skills relevant to the current stage."""
        sections: list[ContextSection] = []

        if explicit_skills:
            # Handle list of LoadedSkill or skill IDs
            for sk in explicit_skills:
                if isinstance(sk, LoadedSkill):
                    s_text = f"DOMAIN SKILL GUIDELINES [{sk.name} v{sk.metadata.version}]:\n{sk.content.strip()}"
                    sections.append(
                        ContextSection(
                            name=f"skill_{sk.skill_id}",
                            content=s_text,
                            priority=SectionPriority.HIGH,
                            is_mandatory=False,
                            category="skills",
                            estimated_tokens=estimate_tokens(s_text),
                        )
                    )
                elif isinstance(sk, str) and self.skill_manager:
                    try:
                        loaded = self.skill_manager.load_skill(sk)
                        s_text = f"DOMAIN SKILL GUIDELINES [{loaded.name} v{loaded.metadata.version}]:\n{loaded.content.strip()}"
                        sections.append(
                            ContextSection(
                                name=f"skill_{loaded.skill_id}",
                                content=s_text,
                                priority=SectionPriority.HIGH,
                                is_mandatory=False,
                                category="skills",
                                estimated_tokens=estimate_tokens(s_text),
                            )
                        )
                    except Exception as e:
                        log.warning("Could not load explicit skill '%s': %s", sk, e)
            return sections

        # If no explicit skills provided, check stage mapping and skill manager
        if not self.skill_manager:
            return []

        target_skill_ids = STAGE_SKILL_MAP.get(stage, [])
        if not target_skill_ids:
            return []

        for sid in target_skill_ids:
            try:
                loaded = self.skill_manager.load_skill(sid)
                s_text = f"DOMAIN SKILL GUIDELINES [{loaded.name} v{loaded.metadata.version}]:\n{loaded.content.strip()}"
                sections.append(
                    ContextSection(
                        name=f"skill_{loaded.skill_id}",
                        content=s_text,
                        priority=SectionPriority.HIGH,
                        is_mandatory=False,
                        category="skills",
                        estimated_tokens=estimate_tokens(s_text),
                    )
                )
            except Exception as e:
                log.debug("Skill '%s' not loaded for stage '%s': %s", sid, stage.value, e)

        return sections

    def _resolve_schema_text(
        self,
        stage: ExecutionStage,
        schema: DatabaseSchema | str | dict[str, Any] | None,
        relevant_tables: list[str] | None,
    ) -> str | None:
        """Obtain and format database schema string."""
        if schema:
            if isinstance(schema, DatabaseSchema):
                return self._format_database_schema(schema, relevant_tables)
            if isinstance(schema, dict):
                return self._format_schema_dict(schema, relevant_tables)
            return str(schema).strip()

        # Check provider function
        if self.schema_provider:
            try:
                prov = self.schema_provider() if callable(self.schema_provider) else self.schema_provider
                if isinstance(prov, DatabaseSchema):
                    return self._format_database_schema(prov, relevant_tables)
                if isinstance(prov, dict):
                    return self._format_schema_dict(prov, relevant_tables)
                return str(prov).strip()
            except Exception as e:
                log.warning("Error fetching schema from schema_provider: %s", e)

        return None

    def _format_schema_dict(
        self,
        schema_dict: dict[str, Any],
        relevant_tables: list[str] | None,
    ) -> str:
        """Render a concise, token-efficient summary from an inspect_database_schema dict."""
        tables = schema_dict.get("tables")
        if not isinstance(tables, list):
            return f"DATABASE SCHEMA:\n{json.dumps(schema_dict, indent=2)}"

        if relevant_tables:
            rel_set = {t.lower().strip() for t in relevant_tables if isinstance(t, str)}
            filtered = [
                t for t in tables
                if isinstance(t, dict) and str(t.get("name", "")).lower() in rel_set
            ]
            if filtered:
                tables = filtered

        lines: list[str] = ["DATABASE SCHEMA OVERVIEW:"]
        for t in tables:
            if not isinstance(t, dict):
                continue
            t_name = t.get("name", "unknown")
            row_cnt = t.get("row_count")
            cnt_str = f" ({row_cnt:,} rows)" if isinstance(row_cnt, int) else ""
            lines.append(f"Table: {t_name}{cnt_str}")
            cols = t.get("columns", [])
            if isinstance(cols, list) and cols:
                col_parts: list[str] = []
                for c in cols:
                    if isinstance(c, dict):
                        pk = " [PK]" if c.get("is_primary_key") else ""
                        dtype = c.get("data_type") or c.get("affinity") or "TEXT"
                        col_parts.append(f"{c.get('name')} ({dtype}{pk})")
                if col_parts:
                    lines.append("  Columns: " + ", ".join(col_parts))
            date_cols = t.get("date_columns", [])
            if isinstance(date_cols, list) and date_cols:
                d_parts: list[str] = []
                for dc in date_cols:
                    if isinstance(dc, dict) and dc.get("column"):
                        d_parts.append(
                            f"{dc['column']}: {dc.get('min_value')} to {dc.get('max_value')}"
                        )
                if d_parts:
                    lines.append("  Date Ranges: " + "; ".join(d_parts))
            fks = t.get("foreign_keys", [])
            if isinstance(fks, list) and fks:
                for fk in fks:
                    if isinstance(fk, dict):
                        lines.append(
                            f"  FK: {t_name}.{fk.get('from_column')} -> "
                            f"{fk.get('to_table')}.{fk.get('to_column')}"
                        )
        return "\n".join(lines)

    def _format_database_schema(
        self,
        schema: DatabaseSchema,
        relevant_tables: list[str] | None,
    ) -> str:
        """Render readable schema summary, optionally filtering by relevant tables."""
        tables = schema.tables
        if relevant_tables:
            rel_set = {t.lower().strip() for t in relevant_tables}
            filtered = [t for t in tables if t.name.lower() in rel_set]
            if filtered:
                tables = filtered

        lines: list[str] = ["DATABASE SCHEMA OVERVIEW:"]
        for t in tables:
            cnt_str = f" ({t.row_count:,} rows)" if t.row_count is not None else ""
            lines.append(f"Table: {t.name}{cnt_str}")
            col_parts: list[str] = []
            for c in t.columns:
                pk_marker = " [PK]" if c.is_primary_key else ""
                col_parts.append(f"{c.name} ({c.data_type or c.affinity}{pk_marker})")
            lines.append("  Columns: " + ", ".join(col_parts))

            if t.foreign_keys:
                for fk in t.foreign_keys:
                    lines.append(f"  FK: {t.name}.{fk.from_column} -> {fk.to_table}.{fk.to_column}")

        return "\n".join(lines)

    def _format_task_state(self, task: AgentTask | None, step: TaskStep | None) -> str:
        """Format active task and step state."""
        lines: list[str] = ["TASK EXECUTION STATE:"]
        if task:
            lines.append(f"Task ID: {task.task_id} | Status: {task.status.value}")
            if task.plan:
                plan_summary = getattr(task.plan, "summary", None) or getattr(task.plan, "rationale", "")
                lines.append(f"Plan Summary: {plan_summary}")
                lines.append(f"Total Steps: {len(task.plan.steps)}")
        if step:
            lines.append(f"Active Step ID: {step.step_id}")
            lines.append(f"Step Name: {step.name}")
            lines.append(f"Step Description: {step.description}")
            if step.dependencies:
                lines.append(f"Step Dependencies: {', '.join(step.dependencies)}")
            if step.required_tools:
                lines.append(f"Step Permitted Tools: {', '.join(step.required_tools)}")

        return "\n".join(lines)

    def _format_checkpoint_state(self, checkpoint: TaskCheckpoint) -> str:
        """Format durable checkpoint state."""
        lines = [
            "CHECKPOINT CONTEXT:",
            f"Checkpoint ID: {checkpoint.checkpoint_id} (Seq: {checkpoint.sequence_number})",
            f"Type: {checkpoint.checkpoint_type.value} | Status: {checkpoint.task_status.value}",
        ]
        if checkpoint.completed_step_ids:
            lines.append(f"Completed Steps: {', '.join(checkpoint.completed_step_ids)}")
        if checkpoint.pending_step_ids:
            lines.append(f"Pending Steps: {', '.join(checkpoint.pending_step_ids)}")
        if checkpoint.artifact_ids:
            lines.append(f"Generated Artifacts: {', '.join(checkpoint.artifact_ids)}")
        return "\n".join(lines)

    def _query_working_memory(self, task: AgentTask | None) -> dict[str, Any] | None:
        """Query working memory variables from repository if available."""
        if not self.memory_repo or not task:
            return None
        if hasattr(self.memory_repo, "get_working_memory"):
            try:
                return self.memory_repo.get_working_memory(task.task_id)
            except Exception as e:
                log.debug("Error querying working memory: %s", e)
        return None

    def _query_semantic_facts(
        self,
        stage: ExecutionStage,
        relevant_tables: list[str] | None,
    ) -> list[Any] | None:
        """Query semantic facts from repository if available."""
        if not self.memory_repo or not hasattr(self.memory_repo, "query_facts"):
            return None
        try:
            # Domain mapping based on stage
            domain = "sql" if stage in (ExecutionStage.SQL_GENERATION, ExecutionStage.SQL_VALIDATION) else None
            facts = self.memory_repo.query_facts(domain=domain, limit=5)
            return facts if facts else None
        except Exception as e:
            log.debug("Error querying semantic facts: %s", e)
            return None

    def _format_semantic_facts(self, facts: list[Any]) -> str:
        """Render relevant domain semantic facts."""
        lines = ["DOMAIN KNOWLEDGE & BUSINESS DEFINITIONS:"]
        for f in facts:
            if hasattr(f, "key") and hasattr(f, "value"):
                val = f.value.get("text", str(f.value)) if isinstance(f.value, dict) else str(f.value)
                lines.append(f"- {f.key}: {val}")
            elif isinstance(f, dict):
                k = f.get("key", "fact")
                v = f.get("value", "")
                lines.append(f"- {k}: {v}")
            else:
                lines.append(f"- {str(f)}")
        return "\n".join(lines)

    def _format_dataset_summary(self, summary: dict[str, Any] | str) -> str:
        """Format dataset profile and metadata."""
        if isinstance(summary, str):
            return f"VALIDATED DATASET SUMMARY:\n{summary.strip()}"
        return f"VALIDATED DATASET SUMMARY:\n{json.dumps(summary, indent=2, sort_keys=True)}"

    def _format_tool_results(self, tool_results: list[dict[str, Any]] | list[str]) -> str:
        """Format recent MCP tool execution results with explicit budget bounding notice."""
        lines = ["RECENT TOOL RESULTS:"]
        for tr in tool_results:
            if isinstance(tr, dict):
                t_name = tr.get("tool_name", tr.get("name", "tool"))
                status = tr.get("status", "completed")
                content = tr.get("result", tr.get("content", tr.get("result_summary", "")))
                content_str = str(content)
                if len(content_str) > 3000:
                    content_str = content_str[:3000] + f"\n... [truncated for context budget: {len(content_str) - 3000} characters omitted]"
                safe_content = self._sanitize_delimiters(content_str, "tool_result")
                lines.append(f'<tool_result name="{t_name}" status="{status}">\n{safe_content}\n</tool_result>')
            else:
                tr_str = str(tr)
                if len(tr_str) > 3000:
                    tr_str = tr_str[:3000] + f"\n... [truncated for context budget: {len(tr_str) - 3000} characters omitted]"
                safe_tr = self._sanitize_delimiters(tr_str, "tool_result")
                lines.append(f"<tool_result>\n{safe_tr}\n</tool_result>")
        return "\n".join(lines)

    def _format_conversation_history(
        self, messages: Sequence[Any]
    ) -> list[ContextSection]:
        """Convert prior conversation history into prioritized context sections."""
        sections: list[ContextSection] = []
        if not messages:
            return sections

        total_msgs = len(messages)
        for idx, m in enumerate(messages):
            role = getattr(m, "role", None) or (m.get("role") if isinstance(m, dict) else "unknown")
            content = getattr(m, "content", None) or (m.get("content") if isinstance(m, dict) else str(m))
            if role == "system" or not str(content).strip():
                continue

            # Prioritize newest messages (last 4 get MEDIUM, older get LOW)
            is_recent = idx >= (total_msgs - 4)
            prio = SectionPriority.MEDIUM if is_recent else SectionPriority.LOW

            safe_content = self._sanitize_delimiters(str(content).strip(), "history_msg")
            msg_text = f"CONVERSATION [{role.upper()}]: {safe_content}"
            sections.append(
                ContextSection(
                    name=f"history_{idx:03d}_{role}",
                    content=msg_text,
                    priority=prio,
                    is_mandatory=False,
                    category="conversation_history",
                    estimated_tokens=estimate_tokens(msg_text),
                )
            )
        return sections

    # -----------------------------------------------------------------------
    # Security & Sanitization (Internal)
    # -----------------------------------------------------------------------

    def _sanitize_user_input(self, text: str) -> str:
        """Sanitize and enclose untrusted user input within xml boundaries.

        Neutralizes delimiter escape attempts and role injection headers.
        """
        cleaned = text.strip()
        # Escape closing delimiter to prevent tag breakout
        cleaned = self._sanitize_delimiters(cleaned, "user_request")

        # Neutralize role spoofing headers
        cleaned = re.sub(r"(?im)^(system|assistant|tool)\s*:\s*", "[User quoted header: \\1]: ", cleaned)
        cleaned = re.sub(r"(?im)^###\s*system\b", "### [User quoted system header]", cleaned)

        return f"<user_request>\n{cleaned}\n</user_request>"

    def _sanitize_delimiters(self, text: str, tag: str) -> str:
        """Neutralize closing tag breakouts."""
        close_tag = f"</{tag}>"
        if close_tag in text:
            text = text.replace(close_tag, f"&lt;/{tag}&gt;")
        return text

    # -----------------------------------------------------------------------
    # Prompt Assembly (Internal)
    # -----------------------------------------------------------------------

    def _assemble_prompts(
        self,
        admitted: list[ContextSection],
    ) -> tuple[str, str]:
        """Partition admitted sections into system and user prompts with deterministic order."""
        # System prompt categories: system_instructions, skills, database_schema, semantic_memory
        system_cats = {"system_instructions", "skills", "database_schema", "semantic_memory"}

        sys_blocks: list[str] = []
        user_blocks: list[str] = []

        # Standard ordering for sections in system prompt
        cat_order_sys = ["system_instructions", "skills", "database_schema", "semantic_memory"]
        # Standard ordering for sections in user prompt
        cat_order_user = [
            "task_and_checkpoint",
            "working_memory",
            "tool_results",
            "conversation_history",
            "other",
            "user_request",
        ]

        # Sort admitted sections deterministically by category order
        for cat in cat_order_sys:
            for s in admitted:
                if s.category == cat:
                    sys_blocks.append(s.content.strip())

        for cat in cat_order_user:
            for s in admitted:
                if s.category == cat:
                    user_blocks.append(s.content.strip())

        # Any uncategorized section
        for s in admitted:
            if s.category not in cat_order_sys and s.category not in cat_order_user:
                user_blocks.append(s.content.strip())

        system_prompt = "\n\n".join(sys_blocks)
        user_prompt = "\n\n".join(user_blocks)

        return system_prompt, user_prompt

