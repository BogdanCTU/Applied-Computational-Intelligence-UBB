import sqlite3
from src.utils.source_classifier import is_production_csharp_file, is_test_source_path

conn = sqlite3.connect('data/database/bug_detection.db')
cursor = conn.cursor()

# 1. 14 positive and 14 candidate-clean
obs = cursor.execute('''
    SELECT id, file_path, method_name, method_signature, label, source_code
    FROM observations
    WHERE repository_id = 14
    ORDER BY label DESC, id ASC
''').fetchall()

print(f"Total FluentValidation observations: {len(obs)}")
pos = [o for o in obs if o[4] == 1]
clean = [o for o in obs if o[4] == 0]
print(f"Positive (Label 1): {len(pos)}, Clean (Label 0): {len(clean)}")

# 2. Production source classification check
test_leaks = []
for o in obs:
    fpath = o[1]
    is_prod = is_production_csharp_file(fpath)
    is_test = is_test_source_path(fpath)
    if not is_prod or is_test:
        test_leaks.append((o[0], fpath, is_prod, is_test))
print(f"Test leaks detected: {len(test_leaks)}")

# 3. Duplicate methods and fingerprints
fingerprints = set()
duplicates = []
for o in obs:
    fp = f"{o[1]}:{o[3]}:{o[5]}"
    if fp in fingerprints:
        duplicates.append((o[0], o[1], o[2]))
    fingerprints.add(fp)
print(f"Duplicate fingerprints among observations: {len(duplicates)}")

# 4. SZZ traces & unique BICs
traces = cursor.execute('SELECT inducing_commit_sha, fixing_commit_sha, file_path FROM szz_results WHERE repository_id = 14').fetchall()
unique_bics = set(t[0] for t in traces)
unique_fixes = set(t[1] for t in traces)
print(f"SZZ traces: {len(traces)}, Unique BICs: {len(unique_bics)}, Fixes producing traces: {len(unique_fixes)}")

# 5. Fixes in commits table
total_fixes = cursor.execute('SELECT COUNT(*) FROM commits WHERE repository_id = 14 AND is_bug_fix = 1').fetchone()[0]
print(f"Total candidate bug-fixing commits in DB: {total_fixes}")

# 6. Historical snapshot 1 integrity
ds1_count = cursor.execute('SELECT COUNT(*) FROM dataset_observations WHERE dataset_id = 1').fetchone()[0]
ds1_fv = cursor.execute('''
    SELECT COUNT(*) 
    FROM dataset_observations do
    JOIN observations o ON do.observation_id = o.id
    WHERE do.dataset_id = 1 AND o.repository_id = 14
''').fetchone()[0]
print(f"Dataset 1 total rows: {ds1_count}, FluentValidation rows in Dataset 1: {ds1_fv}")

