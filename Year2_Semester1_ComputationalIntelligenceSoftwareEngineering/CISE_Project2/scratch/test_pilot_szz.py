import git
from pathlib import Path
from src.database.connection import Database
from src.database.repository import RepositoryDB
from src.mining.szz_analyzer import SZZAnalyzer
from src.utils.source_classifier import is_production_csharp_file

db = Database('data/database/bug_detection.db')
repo_db = RepositoryDB(db)
analyzer = SZZAnalyzer(repo_db)
local_path = Path('data/repositories/FluentValidation/FluentValidation')
repo = git.Repo(local_path)

with db.session() as conn:
    fixes = conn.execute('SELECT commit_sha FROM commits WHERE repository_id = 14 AND is_bug_fix = 1').fetchall()

total_traces = 0
unique_bics = set()
for f in fixes:
    sha = f['commit_sha']
    traces = analyzer.analyze_commit(repo, sha, 14)
    for t in traces:
        total_traces += 1
        unique_bics.add(t['inducing_commit_sha'])
        print(f"Trace: {t['file_path']}:{t['deleted_line_number']} -> {t['inducing_commit_sha'][:8]} | prod={is_production_csharp_file(t['file_path'])}")

print(f"Total production traces: {total_traces}, Unique BICs: {len(unique_bics)}")

