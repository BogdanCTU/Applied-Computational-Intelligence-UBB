"""Execution benchmark runner for Text-to-SQL on SQLite test engines."""

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from app.core.config import get_project_root
from app.core.logging import get_logger
from app.database.sqlite_executor import QueryResult, SQLiteExecutor
from app.datasets.preprocessor import SQLTrainingExample
from app.evaluation.metrics import (
    EvaluationMetrics,
    compare_execution_results,
    compute_exact_match,
)
from app.inference.engine import InferenceEngine
from app.utils.sql_sanitizer import is_valid_sql_syntax

logger = get_logger(__name__)


@dataclass
class EvaluationSampleResult:
    db_id: str
    question: str
    golden_sql: str
    predicted_sql: str
    is_valid_sql: bool
    is_exact_match: bool
    is_execution_match: bool
    gold_row_count: int
    pred_row_count: int
    latency_ms: float
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

    def evaluate(
        self,
        examples: List[SQLTrainingExample],
        run_name: str = "baseline",
    ) -> Tuple[EvaluationMetrics, List[EvaluationSampleResult]]:
        """Executes full evaluation on dataset and writes structured report."""
        logger.info(f"Starting evaluation run '{run_name}' on {len(examples)} examples...")
        metrics = EvaluationMetrics(total_samples=len(examples))
        sample_results: List[EvaluationSampleResult] = []

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

            # 2. Generate Predicted SQL
            start_t = time.perf_counter()
            pred_sql, raw_resp = self.engine.generate_sql(
                schema_text=ex.schema_text,
                question=ex.question,
            )
            latency_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
            metrics.total_latency_ms += latency_ms

            # 3. Check Syntax Validity
            is_valid = is_valid_sql_syntax(pred_sql)
            if is_valid:
                metrics.valid_sql_count += 1

            # 4. Check Exact Match
            is_em = compute_exact_match(pred_sql, ex.query)
            if is_em:
                metrics.exact_match_count += 1

            # 5. Check Execution Match
            is_ex = False
            pred_error = None
            pred_row_count = 0
            if is_valid:
                pred_res = executor.execute(pred_sql)
                if pred_res.success:
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

            sample_result = EvaluationSampleResult(
                db_id=ex.db_id,
                question=ex.question,
                golden_sql=ex.query,
                predicted_sql=pred_sql,
                is_valid_sql=is_valid,
                is_exact_match=is_em,
                is_execution_match=is_ex,
                gold_row_count=gold_res.row_count,
                pred_row_count=pred_row_count,
                latency_ms=latency_ms,
                error=pred_error,
            )
            sample_results.append(sample_result)

            logger.info(
                f"[{idx}/{len(examples)}] DB: {ex.db_id} | EX: {is_ex} | EM: {is_em} | Latency: {latency_ms}ms"
            )

        # Save Report
        self._save_report(run_name, metrics, sample_results)
        return metrics, sample_results

    def _save_report(
        self,
        run_name: str,
        metrics: EvaluationMetrics,
        results: List[EvaluationSampleResult],
    ) -> None:
        """Saves evaluation summary JSON and detailed sample CSV."""
        dest_dir = self.output_dir / run_name
        dest_dir.mkdir(parents=True, exist_ok=True)

        summary_file = dest_dir / "summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(metrics.to_dict(), f, indent=2)

        details_file = dest_dir / "detailed_samples.json"
        with open(details_file, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in results], f, indent=2)

        logger.info(f"Report saved: {summary_file}")
