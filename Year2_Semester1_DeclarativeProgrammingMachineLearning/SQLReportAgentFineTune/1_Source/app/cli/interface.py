"""Interactive CLI for the Text-to-SQL Fine-Tuning Laboratory."""

import argparse
import sys
from pathlib import Path
from app.core.config import get_project_root, load_config
from app.core.logging import get_logger, setup_logging
from app.datasets.preprocessor import DatasetPreprocessor
from app.evaluation.comparator import ModelComparator
from app.evaluation.execution_eval import ExecutionEvaluator
from app.inference.engine import InferenceEngine
from app.models.downloader import ModelDownloader
from app.models.registry import ModelRegistry
from app.training.config import TrainingHyperparameters
from app.training.lora_manager import LoRAManager
from app.training.trainer import LoRATrainer
from app.utils.hardware import get_hardware_info

logger = get_logger(__name__)


def cmd_verify(args: argparse.Namespace) -> int:
    """Verifies local Apple Silicon and MLX environment."""
    print("=" * 60)
    print("  SQLReportAgentFineTune - Environment Verification")
    print("=" * 60)

    hw = get_hardware_info()
    print(f"Platform:           {hw.platform}")
    print(f"Architecture:       {hw.machine}")
    print(f"Chipset:            {hw.chip}")
    print(f"RAM:                {hw.total_ram_gb} GB")
    print(f"CPU Cores:          {hw.cpu_cores}")
    print(f"Apple Silicon:      {hw.is_apple_silicon}")
    print(f"MLX Installed:      {hw.mlx_available}")
    print(f"MLX Device:         {hw.mlx_device}")
    print(f"Metal GPU Enabled:  {hw.metal_gpu_enabled}")

    if not hw.is_apple_silicon or not hw.mlx_available:
        print("\n[ERROR] Environment does not meet requirements for native MLX execution.")
        return 1

    print("\n[OK] Environment is certified for native MLX fine-tuning.")
    return 0


def cmd_data(args: argparse.Namespace) -> int:
    """Acquires and preprocessors training datasets and databases."""
    print("=" * 60)
    print("  Preparing Text-to-SQL Datasets & SQLite Test Databases")
    print("=" * 60)

    preprocessor = DatasetPreprocessor()
    splits, db_map = preprocessor.build_expanded_dataset(
        train_target=getattr(args, "train_target", 3500),
        val_target=getattr(args, "val_target", 350),
    )
    manifest = preprocessor.export_and_manifest(splits, db_map)

    print(f"\n[OK] Successfully processed dataset splits:")
    for split_name, info in manifest["splits"].items():
        print(f"  * {split_name}: {info['records']} records -> {info['file_path']} (SHA-256: {info['sha256'][:10]}...)")
    print(f"\n  * Available Databases: {manifest['total_databases']}")
    print(f"  * Track 1 (Known Schema) Test Records: {manifest['track_separation']['track1_known_schema']['test_records']}")
    print(f"  * Track 2 (Unseen Schema) Test Records: {manifest['track_separation']['track2_unseen_schema']['test_records']}")
    print(f"  * Manifest saved to: 2_Database/processed/dataset_manifest.json")

    return 0


def cmd_download(args: argparse.Namespace) -> int:
    """Downloads base pretrained model into 6_Models/base/."""
    model_id = args.model or ModelRegistry.get_default_model().model_id
    print("=" * 60)
    print(f"  Downloading Model: {model_id}")
    print("=" * 60)

    downloader = ModelDownloader()
    path = downloader.download(model_id)
    print(f"\n[OK] Model available at: {path}")
    return 0


def cmd_train(args: argparse.Namespace) -> int:
    """Executes LoRA / QLoRA fine-tuning."""
    config = load_config()
    model_id = args.model or config.model.model_id
    downloader = ModelDownloader()
    resolved_model = str(downloader.get_local_path(model_id)) if downloader.is_downloaded(model_id) else model_id

    run_name = args.run_name or ("pilot_run" if args.pilot else "full_lora_run")
    iters = 10 if args.pilot else (args.iters or config.lora.iters)
    rank = getattr(args, "rank", None) or config.lora.rank
    alpha = getattr(args, "alpha", None) or (rank * 2.0)

    print("=" * 60)
    print(f"  Training Run: {run_name} ({iters} iterations)")
    print(f"  Base Model:   {resolved_model}")
    print(f"  LoRA Config:  Rank={rank}, Alpha={alpha}")
    print("=" * 60)

    hyperparams = TrainingHyperparameters(
        fine_tune_type="lora",
        iters=iters,
        batch_size=args.batch_size or config.lora.batch_size,
        learning_rate=args.lr or config.lora.learning_rate,
        steps_per_report=2 if args.pilot else 10,
        steps_per_eval=5 if args.pilot else getattr(args, "eval_steps", 20),
        save_every=5 if args.pilot else getattr(args, "save_every", 20),
        lora_rank=rank,
        lora_alpha=alpha,
        val_batches=getattr(args, "val_batches", 10),
    )

    trainer = LoRATrainer(base_model=resolved_model, hyperparameters=hyperparams)
    summary = trainer.train(run_name=run_name)

    if summary.success:
        print(f"\n[OK] Training completed in {summary.duration_seconds}s.")
        print(f"  Adapter: {summary.adapter_path}")
        print(f"  Log:     {summary.log_file}")
        return 0
    else:
        print(f"\n[ERROR] Training failed: {summary.error}")
        return 1


def cmd_eval(args: argparse.Namespace) -> int:
    """Evaluates baseline or fine-tuned model on test queries."""
    run_name = args.run_name or "baseline"
    model_id = args.model or ModelRegistry.get_default_model().model_id
    downloader = ModelDownloader()
    resolved_model = str(downloader.get_local_path(model_id)) if downloader.is_downloaded(model_id) else model_id
    adapter_path = args.adapter
    track = getattr(args, "track", "unseen")  # 'unseen' (Track 2) or 'known' (Track 1)

    print("=" * 60)
    print(f"  Evaluating: {run_name} (Track: {track})")
    print(f"  Base Model: {resolved_model}")
    if adapter_path:
        print(f"  Adapter:    {adapter_path}")
    print("=" * 60)

    preprocessor = DatasetPreprocessor()
    splits, db_map = preprocessor.build_expanded_dataset()

    # Select proper held-out test split
    if track == "known":
        test_examples = splits["test_known"]
    else:
        test_examples = splits["test_unseen"]

    # Handle stratified sampling or manifest
    manifest_path = getattr(args, "manifest", None)
    if manifest_path:
        p = Path(manifest_path).resolve()
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                m_data = json.load(f)
            m_ids = set(m_data.get("sample_ids", []))
            test_examples = [ex for ex in test_examples if ex.example_id in m_ids]
            print(f"Loaded {len(test_examples)} samples from manifest: {p.name}")
    elif getattr(args, "stratified", False) and track == "unseen":
        from app.evaluation.sampler import StratifiedSampler
        sampler = StratifiedSampler(seed=42)
        test_examples = sampler.sample_unseen(test_examples, target_size=200)
        print(f"Selected {len(test_examples)} stratified unseen samples across all 22 DBs.")

    engine = InferenceEngine(model_path_or_id=resolved_model, adapter_path=adapter_path)
    evaluator = ExecutionEvaluator(engine=engine, db_map=db_map)

    # Apply limit if specified
    samples = test_examples[: args.limit] if args.limit else test_examples
    metrics, _ = evaluator.evaluate(samples, run_name=run_name)

    print("\n" + "=" * 60)
    print(f"  Evaluation Results: {run_name} [{track}]")
    print("=" * 60)
    print(f"Execution Accuracy (EX): {metrics.execution_accuracy}%")
    print(f"Exact Match Rate (EM):   {metrics.exact_match_rate}%")
    print(f"Valid SQL Rate (VSR):    {metrics.valid_sql_rate}%")
    print(f"Average Latency:         {metrics.average_latency_ms} ms")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    """Compares two evaluation runs."""
    base = args.baseline or "baseline"
    tuned = args.finetuned or "fine_tuned"

    print("=" * 60)
    print(f"  Comparing Runs: {base} vs {tuned}")
    print("=" * 60)

    comparator = ModelComparator()
    diff = comparator.compare(base, tuned)
    report = comparator.generate_markdown_report(diff, base, tuned)
    print("\n" + report)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Fuses LoRA adapter weights into the base model."""
    config = load_config()
    model_id = args.model or config.model.model_id
    downloader = ModelDownloader()
    resolved_model = str(downloader.get_local_path(model_id)) if downloader.is_downloaded(model_id) else model_id
    adapter = args.adapter
    if not adapter:
        print("[ERROR] Please specify an adapter run name or path using --adapter.")
        return 1

    print("=" * 60)
    print(f"  Fusing LoRA Adapter: {adapter}")
    print(f"  Base Model:          {resolved_model}")
    print("=" * 60)

    manager = LoRAManager()
    export_path = manager.fuse_model(
        base_model_path_or_id=resolved_model,
        adapter_run_name=adapter,
        export_dir=getattr(args, "output_dir", None),
        export_gguf=getattr(args, "gguf", False),
    )
    print(f"\n[OK] Model fused and exported successfully to:\n  {export_path}")
    return 0


def cmd_interactive(args: argparse.Namespace) -> int:
    """Interactive natural language to SQL query terminal."""
    model_id = args.model or ModelRegistry.get_default_model().model_id
    adapter = args.adapter

    print("=" * 60)
    print("  Text-to-SQL Interactive Session")
    print(f"  Model: {model_id}")
    if adapter:
        print(f"  Adapter: {adapter}")
    print("=" * 60)

    preprocessor = DatasetPreprocessor()
    _, db_map = preprocessor.build_all_examples()

    print("\nAvailable test databases:")
    for idx, name in enumerate(db_map.keys(), 1):
        print(f"  [{idx}] {name}")

    engine = InferenceEngine(model_path_or_id=model_id, adapter_path=adapter)
    engine.load()

    while True:
        try:
            q = input("\nEnter Question (or 'exit' to quit): ").strip()
            if not q or q.lower() in ("exit", "quit"):
                break
            # Default to retail_analytics
            from app.database.schema_manager import SchemaManager
            schema = SchemaManager.extract_schema_from_sqlite(db_map["retail_analytics"])
            sql, _ = engine.generate_sql(schema.to_prompt_schema(), q)
            print(f"\nGenerated SQL:\n{sql}\n")
        except (KeyboardInterrupt, EOFError):
            break
    return 0


def run_cli() -> int:
    """Parses command line arguments and delegates to commands."""
    setup_logging()
    parser = argparse.ArgumentParser(description="Standalone Text-to-SQL Fine-Tuning Laboratory (MLX)")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # verify
    subparsers.add_parser("verify", help="Check Apple Silicon MLX environment")

    # data
    subparsers.add_parser("data", help="Prepare datasets and test databases")

    # download
    p_dl = subparsers.add_parser("download", help="Download base pretrained model")
    p_dl.add_argument("--model", type=str, default=None, help="Hugging Face repo or model ID")

    # train
    p_tr = subparsers.add_parser("train", help="Run LoRA fine-tuning")
    p_tr.add_argument("--model", type=str, default=None, help="Base model identifier")
    p_tr.add_argument("--run-name", type=str, default=None, help="Name for adapter run")
    p_tr.add_argument("--pilot", action="store_true", help="Run quick 10-iteration verification pilot")
    p_tr.add_argument("--iters", type=int, default=None, help="Number of training iterations")
    p_tr.add_argument("--lr", type=float, default=None, help="Learning rate")
    p_tr.add_argument("--batch-size", type=int, default=None, help="Minibatch size")
    p_tr.add_argument("--rank", type=int, default=8, help="LoRA rank (e.g. 8, 16, 32)")
    p_tr.add_argument("--alpha", type=float, default=None, help="LoRA alpha scaling factor")
    p_tr.add_argument("--val-batches", type=int, default=10, help="Number of validation batches to evaluate")

    # eval
    p_ev = subparsers.add_parser("eval", help="Evaluate model execution accuracy")
    p_ev.add_argument("--run-name", type=str, default="baseline", help="Run identifier")
    p_ev.add_argument("--model", type=str, default=None, help="Base model identifier")
    p_ev.add_argument("--adapter", type=str, default=None, help="Path to LoRA adapter")
    p_ev.add_argument("--limit", type=int, default=None, help="Limit number of test samples")
    p_ev.add_argument("--track", type=str, choices=["unseen", "known"], default="unseen", help="Evaluation track: unseen (Track 2) or known (Track 1)")
    p_ev.add_argument("--stratified", action="store_true", help="Use stratified 200-sample unseen benchmark")
    p_ev.add_argument("--manifest", type=str, default=None, help="Path to sample manifest JSON")

    # compare
    p_cp = subparsers.add_parser("compare", help="Compare baseline vs fine-tuned results")
    p_cp.add_argument("--baseline", type=str, default="baseline", help="Baseline run name")
    p_cp.add_argument("--finetuned", type=str, default="fine_tuned", help="Fine-tuned run name")

    # export / fuse
    p_exp = subparsers.add_parser("export", help="Fuse adapter weights into standalone model")
    p_exp.add_argument("--adapter", type=str, required=True, help="Adapter run name or path")
    p_exp.add_argument("--model", type=str, default=None, help="Base model identifier")
    p_exp.add_argument("--output-dir", type=str, default=None, help="Output destination folder")
    p_exp.add_argument("--gguf", action="store_true", help="Also export weights in GGUF format")

    # interactive
    p_in = subparsers.add_parser("interactive", help="Interactive Text-to-SQL terminal")
    p_in.add_argument("--model", type=str, default=None, help="Base model identifier")
    p_in.add_argument("--adapter", type=str, default=None, help="Adapter path")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "verify": cmd_verify,
        "data": cmd_data,
        "download": cmd_download,
        "train": cmd_train,
        "eval": cmd_eval,
        "compare": cmd_compare,
        "export": cmd_export,
        "interactive": cmd_interactive,
    }
    return commands[args.command](args)
