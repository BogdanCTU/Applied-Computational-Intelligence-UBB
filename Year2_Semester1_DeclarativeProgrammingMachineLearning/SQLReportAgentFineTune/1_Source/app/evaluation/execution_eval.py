"""Execution benchmark runner for Text-to-SQL on SQLite test engines with Schema Grounding metrics."""

import json
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from app.core.config import get_project_root
from app.core.logging import get_logger
from app.database.schema_manager import DatabaseSchema, SchemaManager
from app.database.sqlite_executor import QueryResult, SQLiteExecutor
from app.datasets.ast_annotator import ASTSchemaAnnotator
from app.datasets.preprocessor import SQLTrainingExample
from app.evaluation.metrics import (
    ErrorCategory,
    EvaluationMetrics,
    classify_sql_error,
    compare_execution_results,
    compute_exact_match,
)
from app.evaluation.sampler import classify_sql_complexity
from app.inference.engine import InferenceEngine
from app.utils.sql_sanitizer import is_valid_sql_syntax

logger = get_logger(__name__)


@dataclass
class EvaluationSampleResult:
    example_id: str
    db_id: str
    question: str
    golden_sql: str
    predicted_sql: str
    is_valid_sql: bool
    is_exact_match: bool
    is_execution_match: bool
    error_category: str
    gold_row_count: int
    pred_row_count: int
    latency_ms: float
    source: str = "spider"
    complexity: str = "medium"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    pred_tables: List[str] = field(default_factory=list)
    pred_cols: List[str] = field(default_factory=list)
    gold_tables: List[str] = field(default_factory=list)
    gold_cols: List[str] = field(default_factory=list)
    is_table_selection_correct: bool = False
    is_col_selection_correct: bool = False
    error: Optional[str] = None


class ExecutionEvaluator:
    """Evaluates an inference model against a suite of database-grounded questions."""

    def __init__(
        self,
        engine: InferenceEngine,
        db_map: Dict[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        timeout_seconds: float = 5.0,
        strict_order: bool = False,
    ):
        self.engine = engine
        self.db_map = db_map
        if output_dir is None:
            self.output_dir = get_project_root() / "7_Results"
        else:
            self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout_seconds = timeout_seconds
        self.strict_order = strict_order
        self.annotator = ASTSchemaAnnotator()
        self._schema_cache: Dict[str, DatabaseSchema] = {}

    def _get_schema(self, db_id: str, db_path: Path) -> DatabaseSchema:
        if db_id not in self._schema_cache:
            self._schema_cache[db_id] = SchemaManager.extract_schema_from_sqlite(db_path, db_id=db_id)
        return self._schema_cache[db_id]

    def evaluate(
        self,
        examples: List[SQLTrainingExample],
        run_name: str = "baseline",
    ) -> Tuple[EvaluationMetrics, List[EvaluationSampleResult]]:
        """Executes full evaluation on dataset and writes structured report."""
        logger.info(f"Starting evaluation run '{run_name}' on {len(examples)} examples...")
        metrics = EvaluationMetrics(total_samples=len(examples))
        sample_results: List[EvaluationSampleResult] = []
        error_counts: Dict[str, int] = {}

        # Tracking for breakdowns
        db_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "correct": 0})
        comp_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "correct": 0})
        source_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "correct": 0})

        # Schema Grounding Tracking
        table_precisions: List[float] = []
        table_recalls: List[float] = []
        col_precisions: List[float] = []
        col_recalls: List[float] = []
        contingency = {
            "schema_correct_sql_correct": 0,
            "schema_correct_sql_wrong": 0,
            "schema_wrong_sql_correct": 0,
            "schema_wrong_sql_wrong": 0,
        }
        has_schema_predictions = False

        for idx, ex in enumerate(examples, 1):
            db_path = self.db_map.get(ex.db_id)
            if not db_path or not db_path.exists():
                logger.error(f"Missing database for {ex.db_id}")
                continue

            executor = SQLiteExecutor(db_path, timeout_seconds=self.timeout_seconds)

            # 1. Execute Golden SQL
            gold_res = executor.execute(ex.query)
            if not gold_res.success:
                logger.warning(f"Golden query failed for {ex.question}: {gold_res.error}")

            # 2. Extract Golden Schema Elements
            schema = self._get_schema(ex.db_id, db_path)
            gold_anno = self.annotator.annotate(ex.query, schema, example_id=ex.example_id)
            gold_tables = gold_anno.tables
            gold_cols = gold_anno.columns

            # 3. Generate Predicted SQL with tokens
            start_t = time.perf_counter()
            pred_tables: List[str] = []
            pred_cols: List[str] = []
            pred_rels: List[str] = []

            if hasattr(self.engine, "generate_sql_detailed"):
                detailed_out = self.engine.generate_sql_detailed(
                    schema_text=ex.schema_text,
                    question=ex.question,
                )
                if len(detailed_out) == 7:
                    pred_sql, raw_resp, p_tokens, c_tokens, pred_tables, pred_cols, pred_rels = detailed_out
                else:
                    pred_sql, raw_resp, p_tokens, c_tokens = detailed_out[:4]
            else:
                pred_sql, raw_resp = self.engine.generate_sql(
                    schema_text=ex.schema_text,
                    question=ex.question,
                )
                p_tokens, c_tokens = 0, 0

            latency_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
            metrics.total_latency_ms += latency_ms
            metrics.latencies_ms.append(latency_ms)
            metrics.prompt_tokens_list.append(p_tokens)
            metrics.completion_tokens_list.append(c_tokens)

            # 4. Check Syntax Validity
            is_valid = is_valid_sql_syntax(pred_sql)
            if is_valid:
                metrics.valid_sql_count += 1

            # 5. Check Exact Match
            is_em = compute_exact_match(pred_sql, ex.query)
            if is_em:
                metrics.exact_match_count += 1

            # 6. Check Execution Match
            is_ex = False
            pred_error = None
            pred_row_count = 0
            if is_valid:
                pred_res = executor.execute(pred_sql)
                if pred_res.success:
                    metrics.executable_sql_count += 1
                    pred_row_count = pred_res.row_count
                    is_ex = compare_execution_results(
                        pred_rows=pred_res.rows,
                        gold_rows=gold_res.rows,
                        strict_order=self.strict_order,
                    )
                else:
                    pred_error = pred_res.error
            else:
                pred_error = "SyntaxError: Invalid SQL output"

            if is_ex:
                metrics.execution_match_count += 1
                metrics.binary_ex_outcomes.append(1)
            else:
                metrics.binary_ex_outcomes.append(0)

            # 7. Schema Grounding Evaluation (if predicted schema elements are present)
            is_tab_correct = False
            is_col_correct = False

            if pred_tables or pred_cols:
                has_schema_predictions = True
                pred_tab_set = {t.lower() for t in pred_tables}
                gold_tab_set = {t.lower() for t in gold_tables}

                pred_col_set = {c.lower() for c in pred_cols}
                gold_col_set = {c.lower() for c in gold_cols}

                tab_inter = len(pred_tab_set.intersection(gold_tab_set))
                tab_p = (tab_inter / len(pred_tab_set)) if pred_tab_set else 0.0
                tab_r = (tab_inter / len(gold_tab_set)) if gold_tab_set else 0.0
                table_precisions.append(tab_p)
                table_recalls.append(tab_r)
                is_tab_correct = (pred_tab_set == gold_tab_set)

                col_inter = len(pred_col_set.intersection(gold_col_set))
                col_p = (col_inter / len(pred_col_set)) if pred_col_set else 0.0
                col_r = (col_inter / len(gold_col_set)) if gold_col_set else 0.0
                col_precisions.append(col_p)
                col_recalls.append(col_r)
                is_col_correct = (pred_col_set == gold_col_set)

                # Schema overall correctness is defined by table selection accuracy
                is_schema_correct = is_tab_correct

                if is_schema_correct and is_ex:
                    contingency["schema_correct_sql_correct"] += 1
                elif is_schema_correct and not is_ex:
                    contingency["schema_correct_sql_wrong"] += 1
                elif not is_schema_correct and is_ex:
                    contingency["schema_wrong_sql_correct"] += 1
                else:
                    contingency["schema_wrong_sql_wrong"] += 1

            # 8. Categorize Failure (12 categories)
            err_cat = classify_sql_error(
                pred_error=pred_error,
                is_exec_match=is_ex,
                gold_sql=ex.query,
                pred_sql=pred_sql,
            )
            error_counts[err_cat] = error_counts.get(err_cat, 0) + 1

            # Complexity & Source tracking
            complexity = classify_sql_complexity(ex.query)
            source = getattr(ex, "source", "spider")

            db_stats[ex.db_id]["total"] += 1
            if is_ex:
                db_stats[ex.db_id]["correct"] += 1

            comp_stats[complexity]["total"] += 1
            if is_ex:
                comp_stats[complexity]["correct"] += 1

            source_stats[source]["total"] += 1
            if is_ex:
                source_stats[source]["correct"] += 1

            ex_id = getattr(ex, "example_id", f"sample_{idx}")
            sample_result = EvaluationSampleResult(
                example_id=ex_id,
                db_id=ex.db_id,
                question=ex.question,
                golden_sql=ex.query,
                predicted_sql=pred_sql,
                is_valid_sql=is_valid,
                is_exact_match=is_em,
                is_execution_match=is_ex,
                error_category=err_cat,
                gold_row_count=gold_res.row_count,
                pred_row_count=pred_row_count,
                latency_ms=latency_ms,
                source=source,
                complexity=complexity,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                pred_tables=pred_tables,
                pred_cols=pred_cols,
                gold_tables=gold_tables,
                gold_cols=gold_cols,
                is_table_selection_correct=is_tab_correct,
                is_col_selection_correct=is_col_correct,
                error=pred_error,
            )
            sample_results.append(sample_result)

            logger.info(
                f"[{idx}/{len(examples)}] DB: {ex.db_id} ({complexity}) | EX: {is_ex} | EM: {is_em} | Err: {err_cat} | Latency: {latency_ms}ms"
            )

        metrics.error_distribution = error_counts

        # Calculate Breakdown Accuracies
        metrics.accuracy_by_db = {
            db: round(stat["correct"] / stat["total"] * 100.0, 2)
            for db, stat in sorted(db_stats.items())
        }
        metrics.accuracy_by_complexity = {
            comp: round(stat["correct"] / stat["total"] * 100.0, 2)
            for comp, stat in sorted(comp_stats.items())
        }
        metrics.accuracy_by_source = {
            src: round(stat["correct"] / stat["total"] * 100.0, 2)
            for src, stat in sorted(source_stats.items())
        }

        # Calculate Schema Grounding Aggregates if present
        if has_schema_predictions and table_precisions:
            p_tab = round(sum(table_precisions) / len(table_precisions) * 100.0, 2)
            r_tab = round(sum(table_recalls) / len(table_recalls) * 100.0, 2)
            f1_tab = round(2.0 * p_tab * r_tab / max(0.001, p_tab + r_tab), 2)

            p_col = round(sum(col_precisions) / len(col_precisions) * 100.0, 2)
            r_col = round(sum(col_recalls) / len(col_recalls) * 100.0, 2)
            f1_col = round(2.0 * p_col * r_col / max(0.001, p_col + r_col), 2)

            metrics.schema_table_precision = p_tab
            metrics.schema_table_recall = r_tab
            metrics.schema_table_f1 = f1_tab
            metrics.schema_col_precision = p_col
            metrics.schema_col_recall = r_col
            metrics.schema_col_f1 = f1_col
            metrics.schema_sql_contingency = contingency

        # Save Report
        self._save_report(run_name, metrics, sample_results)
        return metrics, sample_results

    def _save_report(
        self,
        run_name: str,
        metrics: EvaluationMetrics,
        results: List[EvaluationSampleResult],
    ) -> None:
        """Saves evaluation summary JSON and detailed sample records."""
        dest_dir = self.output_dir / run_name
        dest_dir.mkdir(parents=True, exist_ok=True)

        summary_file = dest_dir / "summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(metrics.to_dict(), f, indent=2)

        details_file = dest_dir / "detailed_samples.json"
        with open(details_file, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in results], f, indent=2)

        logger.info(f"Report saved: {summary_file}")
