"""Integration tests verifying Phase II dataset isolation, prompt consistency, and manifest integrity."""

import hashlib
import json
from pathlib import Path
from app.core.config import get_project_root
from app.inference.prompt_template import PromptBuilder, SYSTEM_PROMPT_DIRECT, SYSTEM_PROMPT_GROUNDED


def test_prompt_consistency_direct_and_grounded():
    p_direct = PromptBuilder(mode="direct")
    p_grounded = PromptBuilder(mode="grounded")

    assert p_direct.system_prompt == SYSTEM_PROMPT_DIRECT
    assert p_grounded.system_prompt == SYSTEM_PROMPT_GROUNDED

    msgs_direct = p_direct.build_messages("TABLE t (a INT);", "Find all a")
    msgs_grounded = p_grounded.build_messages("TABLE t (a INT);", "Find all a")

    assert "<SCHEMA_SELECTION>" in msgs_grounded[1]["content"]
    assert "<SCHEMA_SELECTION>" not in msgs_direct[1]["content"]


def test_phase2_manifest_and_file_integrity():
    root = get_project_root()
    manifest_path = root / "2_Database" / "processed" / "phase2_manifest.json"
    assert manifest_path.exists(), "Missing phase2_manifest.json"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    for ds_name, info in manifest["datasets"].items():
        file_path = Path(info["path"])
        assert file_path.exists(), f"Missing dataset file: {file_path}"

        # Verify SHA-256
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha.update(chunk)
        assert sha.hexdigest() == info["sha256"], f"SHA mismatch on {file_path}"
        assert info["records"] > 0


def test_confirmation_benchmark_zero_overlap_with_dev():
    root = get_project_root()
    dev_path = root / "2_Database" / "processed" / "evaluation_sample_unseen_200.json"
    conf_path = root / "2_Database" / "processed" / "confirmation_sample_unseen_200.json"

    assert dev_path.exists()
    assert conf_path.exists()

    with open(dev_path, "r", encoding="utf-8") as f:
        dev_data = json.load(f)
    with open(conf_path, "r", encoding="utf-8") as f:
        conf_data = json.load(f)

    dev_ids = set(dev_data["sample_ids"])
    conf_ids = set(conf_data["sample_ids"])

    assert len(dev_ids) == 200
    assert len(conf_ids) == 200
    overlap = dev_ids.intersection(conf_ids)
    assert len(overlap) == 0, f"Critical contamination: {len(overlap)} overlapping IDs found"
