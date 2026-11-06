"""Main entry point for ACL Seminar 3 – Zipf's Law Corpus Experiment.

Supports:
    python main.py
    python main.py --download-only
    python main.py --analyze-only
    python main.py --report-only
    python main.py --force-download
    python main.py --verbose
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List

from src.experiment import ExperimentPaths, ZipfExperiment


def setup_logging(verbose: bool = False) -> None:
    """Configure terminal logging format."""
    level = logging.DEBUG if verbose else logging.INFO
    format_str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=level, format=format_str, datefmt="%H:%M:%S")


def check_dependencies() -> None:
    """Verify that all core required libraries are installed."""
    required_modules = [
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("matplotlib", "matplotlib"),
        ("scipy", "scipy"),
        ("nltk", "nltk"),
        ("reportlab", "reportlab"),
        ("requests", "requests"),
    ]

    missing: List[str] = []
    for pkg_name, module_name in required_modules:
        try:
            __import__(module_name)
        except ImportError:
            missing.append(pkg_name)

    if missing:
        print("\n[ERROR] Missing required Python packages:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nPlease install dependencies using:")
        print("  pip install -r requirements.txt\n")
        sys.exit(1)


def print_summary(exp: ZipfExperiment) -> None:
    """Print a clean academic execution summary to stdout."""
    print("\n" + "=" * 80)
    print(" ACL SEMINAR 3: ZIPF'S LAW CORPUS EXPERIMENT – EXECUTION SUMMARY")
    print("=" * 80)

    print("\n1. CORPUS SAMPLING & TYPE-TOKEN RATIO (TTR):")
    print("-" * 80)
    print(f"{'Corpus':<28} {'Language':<16} {'Tokens':<10} {'Unique Words':<14} {'TTR':<8}")
    print("-" * 80)
    for cid in ["frankenstein", "pinocchio", "brown"]:
        if cid in exp.distributions:
            meta = exp.raw_corpora[cid][1]
            dist = exp.distributions[cid]
            print(
                f"{meta.title[:26]:<28} "
                f"{meta.language:<16} "
                f"{dist.total_tokens:<10,}"
                f"{dist.unique_words:<14,}"
                f"{dist.type_token_ratio:<8.4f}"
            )

    print("\n2. ZIPF'S LAW ORDINARY LEAST SQUARES (OLS) REGRESSION:")
    print("-" * 80)
    print(f"{'Corpus':<28} {'Slope':<10} {'Exponent s':<12} {'R² (Full)':<12} {'R² (Top 100)':<12}")
    print("-" * 80)
    for cid in ["frankenstein", "pinocchio", "brown"]:
        if cid in exp.full_zipf_map and cid in exp.top100_zipf_map:
            meta = exp.raw_corpora[cid][1]
            fz = exp.full_zipf_map[cid]
            tz = exp.top100_zipf_map[cid]
            print(
                f"{meta.title[:26]:<28} "
                f"{fz.slope:<10.4f}"
                f"{fz.zipf_exponent:<12.4f}"
                f"{fz.r_squared:<12.4f}"
                f"{tz.r_squared:<12.4f}"
            )

    print("\n3. GENERATED ARTIFACTS & OUTPUT PATHS:")
    print("-" * 80)
    if exp.comparison_csv_path and exp.comparison_csv_path.exists():
        print(f"  [CSV] Comparison Table:       {exp.comparison_csv_path.resolve()}")
    if exp.top20_csv_path and exp.top20_csv_path.exists():
        print(f"  [CSV] Top 20 Comparison:      {exp.top20_csv_path.resolve()}")
    for cid in ["frankenstein", "pinocchio", "brown"]:
        indiv_csv = exp.paths.results_csv_dir / f"{cid}_word_frequencies.csv"
        if indiv_csv.exists():
            print(f"  [CSV] {cid.capitalize()} Frequencies:  {indiv_csv.resolve()}")

    for gid, gpath in exp.graph_paths.items():
        if gpath.exists():
            print(f"  [GRAPH] {gid:<21}: {gpath.resolve()}")

    if exp.metadata_json_path and exp.metadata_json_path.exists():
        print(f"  [METADATA] Reproducibility:  {exp.metadata_json_path.resolve()}")

    if exp.pdf_report_path and exp.pdf_report_path.exists():
        print(f"  [PDF] Academic Report:        {exp.pdf_report_path.resolve()}")

    print("=" * 80)
    print(" Experiment completed successfully. All artifacts are ready.")
    print("=" * 80 + "\n")


def parse_arguments() -> argparse.Namespace:
    """Parse CLI options."""
    parser = argparse.ArgumentParser(
        description="ACL Seminar 3: Zipf's Law Corpus Experiment (Mary Shelley, Carlo Collodi, Brown Corpus)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--download-only",
        action="store_true",
        help="Download and cache all corpora in data/raw/ then exit.",
    )
    group.add_argument(
        "--analyze-only",
        action="store_true",
        help="Run preprocessing, frequency analysis, and Zipf regression; generate CSVs then exit.",
    )
    group.add_argument(
        "--report-only",
        action="store_true",
        help="Run visualization, metadata, and PDF report generation.",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Bypass local cache and re-download all corpora.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable detailed DEBUG logging.",
    )
    return parser.parse_args()


def main() -> None:
    """Main CLI execution flow."""
    args = parse_arguments()
    setup_logging(verbose=args.verbose)

    # 1. Verify dependencies
    check_dependencies()

    # 2. Setup paths
    paths = ExperimentPaths.create()
    exp = ZipfExperiment(paths=paths, force_download=args.force_download)

    if args.download_only:
        exp.step_download()
        print("\n[OK] Corpora downloaded and verified successfully in data/raw/\n")
        return

    if args.analyze_only:
        exp.step_download()
        exp.step_preprocess()
        exp.step_frequency_analysis()
        exp.step_zipf_analysis()
        print("\n[OK] Preprocessing, frequency, and Zipf analyses completed. CSVs saved.\n")
        return

    # Default or report-only: run complete pipeline
    exp.run_all()
    print_summary(exp)


if __name__ == "__main__":
    main()

