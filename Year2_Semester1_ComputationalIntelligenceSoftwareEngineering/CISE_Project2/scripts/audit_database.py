"""Complete Database and Artifact Audit Script."""
import json
import sqlite3
import sys
import pandas as pd
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_settings

settings = get_settings()
conn = sqlite3.connect(settings.storage.database_path)
conn.row_factory = sqlite3.Row

print("=== DATABASE AND ARTIFACT AUDIT ===")

# 1. Repositories
repos = conn.execute("SELECT id, full_name, is_cloned, status, local_path, last_sync_at FROM repositories").fetchall()
print(f"\n1. Repositories: {len(repos)}")
for r in repos:
    p = Path(r["local_path"]) if r["local_path"] else None
    exists_on_disk = p.exists() if p else False
    print(f"  Repo #{r['id']}: {r['full_name']} | Cloned: {r['is_cloned']} | Status: {r['status']} | Disk Path Exists: {exists_on_disk}")

# 2. Commits
commits_total = conn.execute("SELECT COUNT(*) as total, SUM(is_bug_fix) as bug_fixes FROM commits").fetchone()
print(f"\n2. Commits: Total={commits_total['total']}, Bug-Fixes={commits_total['bug_fixes']}")
for r in repos:
    cnt = conn.execute("SELECT COUNT(*) as total, SUM(is_bug_fix) as bug_fixes FROM commits WHERE repository_id = ?", (r["id"],)).fetchone()
    print(f"  Repo #{r['id']} ({r['full_name']}): total_commits={cnt['total']}, bug_fixes={cnt['bug_fixes']}")

# 3. Commit files
cf_count = conn.execute("SELECT COUNT(*) as cnt, COUNT(DISTINCT commit_id) as commits_with_files FROM commit_files").fetchone()
print(f"\n3. Commit Files: Total entries={cf_count['cnt']}, across {cf_count['commits_with_files']} commits")

# 4. SZZ traces
szz_total = conn.execute("SELECT COUNT(*) as traces, COUNT(DISTINCT inducing_commit_sha) as bics FROM szz_results").fetchone()
print(f"\n4. SZZ Results: Total Traces={szz_total['traces']}, Unique BICs={szz_total['bics']}")
for r in repos:
    cnt = conn.execute("SELECT COUNT(*) as traces, COUNT(DISTINCT inducing_commit_sha) as bics FROM szz_results WHERE repository_id = ?", (r["id"],)).fetchone()
    print(f"  Repo #{r['id']} ({r['full_name']}): traces={cnt['traces']}, unique_bics={cnt['bics']}")

# 5. Observations
obs_total = conn.execute("SELECT COUNT(*) as total FROM observations").fetchone()["total"]
print(f"\n5. Observations: Total={obs_total}")
obs_breakdown = conn.execute("""
    SELECT 
        o.repository_id,
        r.full_name,
        o.label, 
        COUNT(*) as cnt 
    FROM observations o
    LEFT JOIN repositories r ON o.repository_id = r.id
    GROUP BY o.repository_id, o.label
    ORDER BY o.repository_id, o.label
""").fetchall()
for o in obs_breakdown:
    lbl_name = "Buggy (1)" if o["label"] == 1 else ("Clean (0)" if o["label"] == 0 else "Uncertain (-1)")
    print(f"  Repo #{o['repository_id']} ({o['full_name']}) | Label {o['label']} ({lbl_name}): {o['cnt']} methods")

# 6. Features
feat_total = conn.execute("SELECT COUNT(*) as cnt FROM features").fetchone()["cnt"]
feat_success = conn.execute("SELECT COUNT(*) as cnt FROM features WHERE loc IS NOT NULL").fetchone()["cnt"]
feat_orphans = conn.execute("SELECT COUNT(*) as cnt FROM features WHERE observation_id NOT IN (SELECT id FROM observations)").fetchone()["cnt"]
obs_without_feat = conn.execute("SELECT COUNT(*) as cnt FROM observations WHERE id NOT IN (SELECT observation_id FROM features)").fetchone()["cnt"]
print(f"\n6. Features: Total={feat_total}, Valid={feat_success}, Orphans={feat_orphans}, Unextracted Observations={obs_without_feat}")

# 7. Datasets
datasets = conn.execute("SELECT * FROM datasets").fetchall()
print(f"\n7. Datasets: {len(datasets)}")
for d in datasets:
    print(f"  Dataset #{d['id']}: '{d['name']}' v{d['version']} | Total Count={d['total_count']} | Buggy={d['buggy_count']} | Clean={d['non_buggy_count']} | Uncertain={d['uncertain_count']}")
    # Verify dataset_observations junction table
    junction_count = conn.execute("SELECT COUNT(*) as cnt FROM dataset_observations WHERE dataset_id = ?", (d["id"],)).fetchone()["cnt"]
    print(f"    Junction records in dataset_observations: {junction_count}")

# 8. Models
models = conn.execute("SELECT * FROM models").fetchall()
print(f"\n8. Models: {len(models)}")
for m in models:
    mf = Path(m["model_file_path"])
    print(f"  Model #{m['id']}: '{m['name']}' ({m['algorithm']}) | Dataset ID: #{m['dataset_id']} | Created: {m['created_at']}")
    print(f"    Artifact path: {m['model_file_path']} (Exists: {mf.exists()}, Size: {mf.stat().st_size if mf.exists() else 0} bytes)")
    metrics = json.loads(m["metrics_json"])
    print(f"    Saved Metrics: Accuracy={metrics.get('accuracy')}, Precision={metrics.get('precision')}, Recall={metrics.get('recall')}, F1={metrics.get('f1')}, ROC-AUC={metrics.get('roc_auc')}")

# 9. Predictions
preds_count = conn.execute("SELECT COUNT(*) as cnt FROM predictions").fetchone()["cnt"]
print(f"\n9. Predictions Recorded: {preds_count}")
