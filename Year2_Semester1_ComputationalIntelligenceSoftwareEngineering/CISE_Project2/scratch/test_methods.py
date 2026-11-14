from pathlib import Path
import git
from src.database.connection import Database
from src.database.repository import RepositoryDB
from src.labeling.label_manager import LabelManager
from src.utils.source_classifier import is_production_csharp_file

db = Database('data/database/bug_detection.db')
repo_db = RepositoryDB(db)
label_mgr = LabelManager(repo_db)
local_path = Path('data/repositories/FluentValidation/FluentValidation')

# Inspect what observations would be created from the DB's szz_results
szz_traces = repo_db.list_szz_results(14)
print(f"Total szz_results in DB: {len(szz_traces)}")

repo = git.Repo(local_path)
processed_keys = set()
buggy_methods = []

for trace in szz_traces:
    fix_sha = trace["fixing_commit_sha"]
    bic_sha = trace["inducing_commit_sha"]
    file_path = trace["file_path"]
    deleted_line = trace["deleted_line_number"]

    if not deleted_line or not is_production_csharp_file(file_path):
        continue

    fix_commit = repo.commit(fix_sha)
    if not fix_commit.parents:
        continue
    parent_sha = fix_commit.parents[0].hexsha

    pre_fix_code = label_mgr.get_file_content_at_commit(repo, parent_sha, file_path)
    if not pre_fix_code:
        continue

    pre_method = label_mgr.roslyn.find_enclosing_method(pre_fix_code, deleted_line)
    if not pre_method:
        continue

    dedup_key = f"{parent_sha}:{file_path}:{pre_method['method_signature']}"
    if dedup_key in processed_keys:
        continue
    processed_keys.add(dedup_key)

    buggy_methods.append({
        "file_path": file_path,
        "method_name": pre_method["method_name"],
        "class_name": pre_method["class_name"],
        "is_prod": is_production_csharp_file(file_path),
    })

print(f"Production Buggy Methods count: {len(buggy_methods)}")
for bm in buggy_methods:
    print(f"  {bm['file_path']} -> {bm['class_name']}.{bm['method_name']}")

