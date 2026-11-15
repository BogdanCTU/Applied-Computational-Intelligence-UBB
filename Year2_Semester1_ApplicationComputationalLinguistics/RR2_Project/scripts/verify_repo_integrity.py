"""Read-only filesystem SHA-256 manifest generator and verifier.

Used before and after upstream or local replication experiments to prove that:
1. `original_repo/` has zero created, modified, renamed, or deleted files.
2. Historical `agent_om_local/output/` and `agent_om_local/docs/step*` artifacts remain untouched.

Strictly uses Python stdlib (`pathlib`, `hashlib`, `json`) — NO Git commands.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def build_directory_manifest(
    root: Path,
    exclude_top_dirs: set[str] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Directory does not exist: {root}")

    exclude_top_dirs = exclude_top_dirs or set()
    files_record: dict[str, dict[str, Any]] = {}
    dirs_record: list[str] = []

    for item in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        rel = item.relative_to(root)
        if rel.parts and rel.parts[0] in exclude_top_dirs:
            continue
        rel_posix = rel.as_posix()
        if item.is_dir():
            dirs_record.append(rel_posix)
        elif item.is_file():
            stat = item.stat()
            files_record[rel_posix] = {
                "size": stat.st_size,
                "sha256": sha256_file(item),
            }

    aggregate = hashlib.sha256(
        json.dumps(
            {"dirs": dirs_record, "files": files_record},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "excluded_top_dirs": sorted(exclude_top_dirs),
        "directory_count": len(dirs_record),
        "file_count": len(files_record),
        "aggregate_sha256": aggregate,
        "directories": dirs_record,
        "files": files_record,
    }


def compare_manifests(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    base_dirs = set(baseline.get("directories", []))
    curr_dirs = set(current.get("directories", []))
    added_dirs = sorted(curr_dirs - base_dirs)
    removed_dirs = sorted(base_dirs - curr_dirs)

    base_files: dict[str, dict[str, Any]] = baseline.get("files", {})
    curr_files: dict[str, dict[str, Any]] = current.get("files", {})

    added_files = sorted(set(curr_files) - set(base_files))
    removed_files = sorted(set(base_files) - set(curr_files))
    modified_files: list[dict[str, Any]] = []

    for rel_path in sorted(set(base_files) & set(curr_files)):
        b_meta = base_files[rel_path]
        c_meta = curr_files[rel_path]
        if b_meta["sha256"] != c_meta["sha256"] or b_meta["size"] != c_meta["size"]:
            modified_files.append(
                {
                    "path": rel_path,
                    "baseline_size": b_meta["size"],
                    "current_size": c_meta["size"],
                    "baseline_sha256": b_meta["sha256"],
                    "current_sha256": c_meta["sha256"],
                }
            )

    identical = (
        not added_dirs
        and not removed_dirs
        and not added_files
        and not removed_files
        and not modified_files
    )

    return {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "identical": identical,
        "baseline_aggregate_sha256": baseline.get("aggregate_sha256"),
        "current_aggregate_sha256": current.get("aggregate_sha256"),
        "baseline_file_count": baseline.get("file_count"),
        "current_file_count": current.get("file_count"),
        "added_directories": added_dirs,
        "removed_directories": removed_dirs,
        "added_files": added_files,
        "removed_files": removed_files,
        "modified_files": modified_files,
    }


def atomic_write_json(target: Path, payload: dict[str, Any]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.with_suffix(target.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp_path.replace(target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or verify SHA-256 directory manifests.")
    sub = parser.add_subparsers(dest="command", required=True)

    snap = sub.add_parser("snapshot", help="Write a baseline SHA-256 manifest JSON.")
    snap.add_argument("--root", type=Path, required=True, help="Directory to snapshot.")
    snap.add_argument("--output", type=Path, required=True, help="Destination JSON file.")
    snap.add_argument(
        "--exclude-top-dir",
        action="append",
        default=[],
        help="Optional top-level subdirectory name(s) under --root to skip.",
    )

    ver = sub.add_parser("verify", help="Verify a directory against a baseline SHA-256 manifest.")
    ver.add_argument("--root", type=Path, required=True, help="Directory to verify.")
    ver.add_argument("--baseline", type=Path, required=True, help="Baseline JSON manifest.")
    ver.add_argument("--report", type=Path, default=None, help="Optional JSON diff report path.")

    args = parser.parse_args(argv)

    if args.command == "snapshot":
        manifest = build_directory_manifest(args.root, set(args.exclude_top_dir))
        atomic_write_json(args.output.resolve(), manifest)
        print(
            json.dumps(
                {
                    "status": "SNAPSHOT_CREATED",
                    "root": manifest["root"],
                    "output": str(args.output.resolve()),
                    "directory_count": manifest["directory_count"],
                    "file_count": manifest["file_count"],
                    "aggregate_sha256": manifest["aggregate_sha256"],
                },
                indent=2,
            )
        )
        return 0

    if args.command == "verify":
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        excluded = set(baseline.get("excluded_top_dirs", []))
        current = build_directory_manifest(args.root, excluded)
        diff = compare_manifests(baseline, current)
        if args.report is not None:
            atomic_write_json(args.report.resolve(), diff)
        print(json.dumps(diff, indent=2))
        return 0 if diff["identical"] else 2

    return 1


if __name__ == "__main__":
    sys.exit(main())

