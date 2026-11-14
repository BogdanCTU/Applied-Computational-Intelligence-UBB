from pathlib import Path
from src.database.connection import Database
from src.database.repository import RepositoryDB
from src.labeling.label_manager import LabelManager
from src.utils.source_classifier import is_production_csharp_file, is_test_source_path

db = Database('data/database/bug_detection.db')
repo_db = RepositoryDB(db)
label_mgr = LabelManager(repo_db)
local_path = Path('data/repositories/FluentValidation/FluentValidation')

clean_obs = label_mgr.sample_candidate_clean_methods(14, local_path, target_count=14)
print(f"Sampled clean observations: {len(clean_obs)}")
for c in clean_obs:
    print(f"  {c['file_path']} -> {c['class_name']}.{c['method_name']} | prod={is_production_csharp_file(c['file_path'])}, test={is_test_source_path(c['file_path'])}")

