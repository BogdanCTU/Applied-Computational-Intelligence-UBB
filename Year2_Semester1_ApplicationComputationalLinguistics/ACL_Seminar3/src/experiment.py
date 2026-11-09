"""Experiment orchestration module for ACL Seminar 3: Zipf's Law Corpus Experiment.

Coordinates:
- Corpus acquisition and verification
- Text preprocessing and sampling
- Frequency distribution analysis
- Zipf's Law linear regression modeling
- Publication-quality visualization generation
- Academic CSV, JSON metadata, and PDF report creation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.corpus_loader import CorpusMetadata, load_all_corpora
from src.frequency_analyzer import FrequencyDistribution, calculate_frequency_distribution
from src.report_generator import (
    generate_comparison_csv,
    generate_metadata_json,
    generate_pdf_report,
    generate_top20_comparison_csv,
)
from src.text_preprocessor import preprocess_corpus
from src.visualizer import (
    COLOR_BROWN,
    COLOR_FRANKENSTEIN,
    COLOR_PINOCCHIO,
    plot_english_comparison,
    plot_english_vs_italian,
    plot_individual_distribution,
    plot_top20_words_comparison,
)
from src.zipf_analyzer import ZipfRegressionResult, compare_zipf_fits

logger = logging.getLogger(__name__)


@dataclass
class ExperimentPaths:
    """Standardized directory and file paths for the project."""

    base_dir: Path
    raw_data_dir: Path
    processed_data_dir: Path
    results_csv_dir: Path
    results_graphs_dir: Path
    results_reports_dir: Path

    @classmethod
    def create(cls, base_dir: Optional[Path] = None) -> ExperimentPaths:
        """Initialize paths relative to base_dir (default: current working directory)."""
        base = base_dir.resolve() if base_dir else Path.cwd().resolve()
        raw = base / "data" / "raw"
        processed = base / "data" / "processed"
        csv_dir = base / "results" / "csv"
        graphs = base / "results" / "graphs"
        reports = base / "results" / "reports"

        for directory in [raw, processed, csv_dir, graphs, reports]:
            directory.mkdir(parents=True, exist_ok=True)

        return cls(
            base_dir=base,
            raw_data_dir=raw,
            processed_data_dir=processed,
            results_csv_dir=csv_dir,
            results_graphs_dir=graphs,
            results_reports_dir=reports,
        )


class ZipfExperiment:
    """End-to-end experiment pipeline manager."""

    def __init__(self, paths: Optional[ExperimentPaths] = None, force_download: bool = False):
        self.paths = paths or ExperimentPaths.create()
        self.force_download = force_download

        self.raw_corpora: Dict[str, Tuple[str, CorpusMetadata]] = {}
        self.tokens_map: Dict[str, List[str]] = {}
        self.distributions: Dict[str, FrequencyDistribution] = {}
        self.full_zipf_map: Dict[str, ZipfRegressionResult] = {}
        self.top100_zipf_map: Dict[str, ZipfRegressionResult] = {}
        self.graph_paths: Dict[str, Path] = {}
        self.comparison_csv_path: Optional[Path] = None
        self.top20_csv_path: Optional[Path] = None
        self.metadata_json_path: Optional[Path] = None
        self.pdf_report_path: Optional[Path] = None

    def step_download(self) -> Dict[str, Tuple[str, CorpusMetadata]]:
        """Acquire raw texts and verify caching."""
        logger.info(">>> Step 1: Downloading / loading corpora...")
        self.raw_corpora = load_all_corpora(
            raw_dir=self.paths.raw_data_dir,
            force_download=self.force_download,
        )
        for cid, (raw_text, meta) in self.raw_corpora.items():
            logger.info("Corpus '%s': %d raw characters loaded from %s", cid, len(raw_text), meta.local_file)
        return self.raw_corpora

    def step_preprocess(self) -> Dict[str, List[str]]:
        """Preprocess, normalize, and sample token lists."""
        logger.info(">>> Step 2: Preprocessing and tokenizing texts...")
        if not self.raw_corpora:
            self.step_download()

        for cid, (raw_text, meta) in self.raw_corpora.items():
            tokens, summary = preprocess_corpus(
                raw_text=raw_text,
                is_gutenberg=meta.is_gutenberg,
                target_tokens=meta.target_tokens,
            )
            self.tokens_map[cid] = tokens

            # Save processed token list for reproducibility
            processed_file = self.paths.processed_data_dir / f"{cid}_tokens.txt"
            processed_file.write_text("\n".join(tokens), encoding="utf-8")
            logger.info(
                "Corpus '%s': %d final tokens saved to %s",
                cid,
                len(tokens),
                processed_file,
            )

        return self.tokens_map

    def step_frequency_analysis(self) -> Dict[str, FrequencyDistribution]:
        """Compute frequency tables and export per-corpus CSVs."""
        logger.info(">>> Step 3: Computing word frequency distributions...")
        if not self.tokens_map:
            self.step_preprocess()

        for cid, tokens in self.tokens_map.items():
            dist = calculate_frequency_distribution(tokens=tokens, corpus_id=cid)
            self.distributions[cid] = dist

            # Export individual distribution CSV
            csv_path = self.paths.results_csv_dir / f"{cid}_word_frequencies.csv"
            dist.save_csv(csv_path)

        return self.distributions

    def step_zipf_analysis(self) -> Tuple[Dict[str, ZipfRegressionResult], Dict[str, ZipfRegressionResult]]:
        """Perform Zipf linear regression fitting (full and top-100 ranks)."""
        logger.info(">>> Step 4: Fitting Zipf's Law power-law regressions...")
        if not self.distributions:
            self.step_frequency_analysis()

        for cid, dist in self.distributions.items():
            full_fit, top100_fit = compare_zipf_fits(dist)
            self.full_zipf_map[cid] = full_fit
            self.top100_zipf_map[cid] = top100_fit

        return self.full_zipf_map, self.top100_zipf_map

    def step_generate_graphs(self) -> Dict[str, Path]:
        """Generate high-resolution PNG visualizations."""
        logger.info(">>> Step 5: Generating publication-quality 300 DPI visualizations...")
        if not self.full_zipf_map:
            self.step_zipf_analysis()

        # Graph 1: English vs Italian
        g1_path = self.paths.results_graphs_dir / "graph1_english_vs_italian.png"
        plot_english_vs_italian(
            en_res=self.full_zipf_map["frankenstein"],
            it_res=self.full_zipf_map["pinocchio"],
            output_path=g1_path,
        )
        self.graph_paths["graph1"] = g1_path

        # Graph 2: English comparison (Frankenstein vs Brown)
        g2_path = self.paths.results_graphs_dir / "graph2_english_comparison.png"
        plot_english_comparison(
            en_res=self.full_zipf_map["frankenstein"],
            brown_res=self.full_zipf_map["brown"],
            output_path=g2_path,
        )
        self.graph_paths["graph2"] = g2_path

        # Graph 3: Individual fits (Frankenstein, Pinocchio, Brown)
        g3_en = self.paths.results_graphs_dir / "graph3_individual_frankenstein.png"
        plot_individual_distribution(
            res=self.full_zipf_map["frankenstein"],
            title_corpus_name="Mary Shelley's Frankenstein (English, 1818)",
            color=COLOR_FRANKENSTEIN,
            output_path=g3_en,
        )
        self.graph_paths["graph3_frankenstein"] = g3_en

        g3_it = self.paths.results_graphs_dir / "graph3_individual_pinocchio.png"
        plot_individual_distribution(
            res=self.full_zipf_map["pinocchio"],
            title_corpus_name="Carlo Collodi's Le avventure di Pinocchio (Italian, 1883)",
            color=COLOR_PINOCCHIO,
            output_path=g3_it,
        )
        self.graph_paths["graph3_pinocchio"] = g3_it

        g3_brown = self.paths.results_graphs_dir / "graph3_individual_brown.png"
        plot_individual_distribution(
            res=self.full_zipf_map["brown"],
            title_corpus_name="Brown Corpus Sample (American English, 1961)",
            color=COLOR_BROWN,
            output_path=g3_brown,
        )
        self.graph_paths["graph3_brown"] = g3_brown

        # Graph 4: Top 20 words comparison
        g4_path = self.paths.results_graphs_dir / "graph4_top20_words.png"
        plot_top20_words_comparison(
            distributions=self.distributions,
            output_path=g4_path,
        )
        self.graph_paths["graph4"] = g4_path

        return self.graph_paths

    def step_generate_reports(self) -> Tuple[Path, Path, Path, Path]:
        """Create comparison CSVs, metadata JSON, and academic PDF report."""
        logger.info(">>> Step 6: Generating CSV tables, metadata JSON, and academic PDF report...")
        if not self.graph_paths:
            self.step_generate_graphs()

        metadata_map = {cid: meta for cid, (_, meta) in self.raw_corpora.items()}

        # 1. Consolidated comparison CSV
        comp_csv = self.paths.results_csv_dir / "corpus_comparison.csv"
        generate_comparison_csv(
            metadata_map=metadata_map,
            distributions=self.distributions,
            zipf_results=self.full_zipf_map,
            output_path=comp_csv,
        )
        self.comparison_csv_path = comp_csv

        # 2. Top 20 English vs Italian comparison CSV
        t20_csv = self.paths.results_csv_dir / "top20_english_italian_comparison.csv"
        generate_top20_comparison_csv(
            en_dist=self.distributions["frankenstein"],
            it_dist=self.distributions["pinocchio"],
            output_path=t20_csv,
        )
        self.top20_csv_path = t20_csv

        # 3. Metadata JSON
        meta_json = self.paths.results_reports_dir / "experiment_metadata.json"
        generate_metadata_json(
            metadata_map=metadata_map,
            distributions=self.distributions,
            full_zipf_map=self.full_zipf_map,
            top100_zipf_map=self.top100_zipf_map,
            output_path=meta_json,
        )
        self.metadata_json_path = meta_json

        # 4. Academic PDF report
        pdf_path = self.paths.results_reports_dir / "ACL_Seminar_3_Report.pdf"
        generate_pdf_report(
            metadata_map=metadata_map,
            distributions=self.distributions,
            full_zipf_map=self.full_zipf_map,
            top100_zipf_map=self.top100_zipf_map,
            graph_paths=self.graph_paths,
            output_path=pdf_path,
        )
        self.pdf_report_path = pdf_path

        return comp_csv, t20_csv, meta_json, pdf_path

    def run_all(self) -> None:
        """Execute the complete experiment pipeline from start to finish."""
        self.step_download()
        self.step_preprocess()
        self.step_frequency_analysis()
        self.step_zipf_analysis()
        self.step_generate_graphs()
        self.step_generate_reports()
        logger.info(">>> Experiment execution completed successfully!")

