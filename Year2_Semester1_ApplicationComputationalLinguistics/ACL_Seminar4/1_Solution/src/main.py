"""Main pipeline script for Seminar 4 IR System (Part 1).

Executes the complete workflow:
1. Load and parse CACM collection
2. Tokenize and calculate the 7 most frequent stop words
3. Construct the inverted index and measure build time
4. Persist inverted index to 3_Output/inverted_index.json
5. Execute 3 representative test queries ('database', 'compiler', 'algorithm')
6. Compute Precision@3 and Precision@7 against ground truth
7. Measure high-resolution retrieval performance (mean & median)
8. Generate outputs: results.json, test_results.csv, performance.json
9. Generate documentation: results.md, README.md, implementation.md, seminar_report.pdf
"""

import json
import os
from pathlib import Path
import shutil
import sys
import time
from typing import Dict, List

# Ensure config and modules can be imported
current_dir = Path(__file__).resolve().parent
solution_dir = current_dir.parent
project_root = solution_dir.parent
for p in [str(solution_dir), str(current_dir), str(project_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    import config
    from preprocessing import (
        load_cacm_collection,
        compute_corpus_stop_words,
        save_processed_documents,
        save_stop_words,
        Preprocessor,
        extract_alphabetic_tokens,
    )
    from indexer import InvertedIndex
    from retrieval import RetrievalSystem
    from evaluation import (
        create_default_relevance_judgments,
        save_relevance_judgments,
        evaluate_queries,
        export_results_to_json,
        export_results_to_csv,
        QueryEvaluationResult,
    )
    from report_generator import (
        generate_results_markdown,
        generate_pdf_report,
        generate_readme,
        generate_implementation_docs,
    )
except ImportError:
    from .. import config
    from .preprocessing import (
        load_cacm_collection,
        compute_corpus_stop_words,
        save_processed_documents,
        save_stop_words,
        Preprocessor,
        extract_alphabetic_tokens,
    )
    from .indexer import InvertedIndex
    from .retrieval import RetrievalSystem
    from .evaluation import (
        create_default_relevance_judgments,
        save_relevance_judgments,
        evaluate_queries,
        export_results_to_json,
        export_results_to_csv,
        QueryEvaluationResult,
    )
    from .report_generator import (
        generate_results_markdown,
        generate_pdf_report,
        generate_readme,
        generate_implementation_docs,
    )


def ensure_dataset_available() -> Path:
    """Ensure raw CACM dataset exists in 1_Solution/data/raw/."""
    target_path = config.RAW_CACM_FILE
    if target_path.is_file() and target_path.stat().st_size > 0:
        return target_path

    # Check fallback location
    if config.FALLBACK_CACM_FILE.is_file():
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(config.FALLBACK_CACM_FILE, target_path)
        if config.FALLBACK_QRELS_FILE.is_file():
            shutil.copy(config.FALLBACK_QRELS_FILE, config.RAW_QRELS_FILE)
        if config.FALLBACK_QUERY_FILE.is_file():
            shutil.copy(config.FALLBACK_QUERY_FILE, config.RAW_QUERY_FILE)
        return target_path

    raise FileNotFoundError(
        f"CACM dataset could not be found at {target_path} or {config.FALLBACK_CACM_FILE}."
    )


def run_pipeline() -> Dict:
    """Execute the full IR pipeline and return summary metrics."""
    print("=" * 70)
    print("Seminar 4: Information Retrieval System (Part 1) Pipeline")
    print("=" * 70)

    # 1. Dataset Loading
    raw_cacm_path = ensure_dataset_available()
    print(f"[1/8] Loading CACM documents from: {raw_cacm_path}")
    documents = load_cacm_collection(raw_cacm_path)
    print(f"      Successfully parsed {len(documents):,} documents.")

    # Save processed documents for reproducibility
    save_processed_documents(documents, config.PROCESSED_DOCS_FILE)
    print(f"      Saved processed documents to: {config.PROCESSED_DOCS_FILE}")

    # 2. Preprocessing & Stop-Word Identification
    print(f"[2/8] Calculating corpus token frequencies and top {config.NUM_STOP_WORDS} stop words...")
    stop_words, stop_word_freqs, total_tokens_before = compute_corpus_stop_words(
        documents, num_stop_words=config.NUM_STOP_WORDS
    )
    save_stop_words(stop_words, stop_word_freqs, config.STOP_WORDS_FILE)

    # Compute vocabulary before stop words
    all_raw_tokens = []
    for doc in documents:
        all_raw_tokens.extend(extract_alphabetic_tokens(doc.searchable_text))
    vocab_size_before = len(set(all_raw_tokens))

    print(f"      Top {config.NUM_STOP_WORDS} stop words: {stop_words}")
    for rank, (w, count) in enumerate(stop_word_freqs.items(), 1):
        print(f"        {rank}. {w:<12}: {count:,} occurrences")
    print(f"      Total tokens before stop-word removal: {total_tokens_before:,}")
    print(f"      Vocabulary size before stop-word removal: {vocab_size_before:,}")

    # Initialize Preprocessor with discovered stop words
    preprocessor = Preprocessor(stop_words=stop_words)

    # 3. Inverted Index Construction
    print("[3/8] Building Inverted Index...")
    index = InvertedIndex()

    t_start_build = time.perf_counter_ns()
    index.build(documents, preprocessor)
    t_end_build = time.perf_counter_ns()
    build_time_ms = (t_end_build - t_start_build) / 1_000_000.0

    print(f"      Index built in {build_time_ms:.2f} ms.")
    print(f"      Vocabulary size after stop-word removal: {index.vocabulary_size:,}")
    print(f"      Total indexed tokens after stop-word removal: {index.total_tokens_after:,}")
    print(f"      Total postings: {index.total_postings:,}")

    # 4. Inverted Index Persistence
    print(f"[4/8] Saving Inverted Index to: {config.INVERTED_INDEX_FILE}")
    index.save(config.INVERTED_INDEX_FILE, save_metadata=True)

    index_size_bytes = os.path.getsize(config.INVERTED_INDEX_FILE)
    corpus_size_bytes = os.path.getsize(raw_cacm_path)
    index_ratio_pct = (index_size_bytes / corpus_size_bytes) * 100.0
    print(f"      Index size: {index_size_bytes:,} bytes ({index_size_bytes / (1024*1024):.2f} MB)")
    print(f"      Corpus size: {corpus_size_bytes:,} bytes ({corpus_size_bytes / (1024*1024):.2f} MB)")
    print(f"      Index-to-corpus ratio: {index_ratio_pct:.2f}%")

    # 5. Ground Truth & Relevance Judgments
    print("[5/8] Setting up relevance judgments...")
    relevance_judgments = create_default_relevance_judgments()
    save_relevance_judgments(relevance_judgments, config.RELEVANCE_JUDGMENTS_FILE)

    # 6. Query Retrieval & Evaluation
    print(f"[6/8] Executing test queries: {config.DEFAULT_TEST_QUERIES}")
    retrieval_system = RetrievalSystem(index, preprocessor)
    eval_results = evaluate_queries(
        retrieval_system=retrieval_system,
        queries=config.DEFAULT_TEST_QUERIES,
        relevance_judgments=relevance_judgments,
        timing_repeats=500,
    )

    avg_answer_time_ms = sum(r.retrieval_time_ms for r in eval_results) / len(eval_results)
    median_answer_time_ms = sum(r.median_retrieval_time_ms for r in eval_results) / len(eval_results)

    print(f"      Average system answer time: {avg_answer_time_ms:.4f} ms")
    print(f"      Median system answer time: {median_answer_time_ms:.4f} ms")

    for r in eval_results:
        print(f"      Query '{r.query_word}': {r.matching_documents} matches | "
              f"P@3={r.precision_at_3:.2f} | P@7={r.precision_at_7:.2f} | "
              f"Latency={r.retrieval_time_ms:.4f} ms")

    # Export results
    export_results_to_json(eval_results, config.RESULTS_JSON_FILE)
    export_results_to_csv(eval_results, config.TEST_RESULTS_CSV_FILE)
    print(f"      Exported results to {config.RESULTS_JSON_FILE} and {config.TEST_RESULTS_CSV_FILE}")

    # 7. Performance & Statistical Metrics Recording
    print(f"[7/8] Recording performance statistics to: {config.PERFORMANCE_JSON_FILE}")
    perf_metrics = {
        "student_name": config.STUDENT_NAME,
        "dataset_name": "CACM",
        "documents_count": len(documents),
        "index_build_time_ms": round(build_time_ms, 2),
        "avg_retrieval_time_ms": round(avg_answer_time_ms, 4),
        "median_retrieval_time_ms": round(median_answer_time_ms, 4),
        "num_stop_words": config.NUM_STOP_WORDS,
        "stop_words": stop_words,
        "stop_word_frequencies": stop_word_freqs,
        "index_size_bytes": index_size_bytes,
        "index_size_mb": round(index_size_bytes / (1024 * 1024), 2),
        "corpus_size_bytes": corpus_size_bytes,
        "corpus_size_mb": round(corpus_size_bytes / (1024 * 1024), 2),
        "index_to_corpus_ratio_pct": round(index_ratio_pct, 2),
        "vocabulary_size_before": vocab_size_before,
        "vocabulary_size_after": index.vocabulary_size,
        "total_tokens_before": total_tokens_before,
        "total_tokens_after": index.total_tokens_after,
        "timing_repetitions": 500,
        "benchmark_timer": "time.perf_counter_ns",
    }

    with open(config.PERFORMANCE_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(perf_metrics, f, indent=2)

    # 8. Documentation & Seminar Deliverables Generation
    print("[8/8] Generating documentation and seminar report...")
    generate_results_markdown(
        student_name=config.STUDENT_NAME,
        perf=perf_metrics,
        eval_results=eval_results,
        file_path=config.RESULTS_MD_FILE,
    )
    generate_readme(config.README_MD_FILE)
    generate_implementation_docs(config.IMPLEMENTATION_MD_FILE)
    generate_pdf_report(
        student_name=config.STUDENT_NAME,
        perf=perf_metrics,
        eval_results=eval_results,
        file_path=config.SEMINAR_REPORT_PDF,
    )

    print("=" * 70)
    print("Pipeline Execution Completed Successfully!")
    print(f"PDF Report generated at: {config.SEMINAR_REPORT_PDF}")
    print(f"Results Markdown generated at: {config.RESULTS_MD_FILE}")
    print("=" * 70)

    return perf_metrics


if __name__ == "__main__":
    run_pipeline()
