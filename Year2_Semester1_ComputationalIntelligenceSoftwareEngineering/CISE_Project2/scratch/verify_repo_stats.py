import sqlite3

conn = sqlite3.connect('data/database/bug_detection.db')
cursor = conn.cursor()

repos = cursor.execute('SELECT id, full_name FROM repositories ORDER BY id').fetchall()

for rid, name in repos:
    commits = cursor.execute('SELECT COUNT(*) FROM commits WHERE repository_id = ?', (rid,)).fetchone()[0]
    fixes = cursor.execute('SELECT COUNT(*) FROM commits WHERE repository_id = ? AND is_bug_fix = 1', (rid,)).fetchone()[0]
    traces = cursor.execute('SELECT COUNT(*) FROM szz_results WHERE repository_id = ?', (rid,)).fetchone()[0]
    bics = cursor.execute('SELECT COUNT(DISTINCT inducing_commit_sha) FROM szz_results WHERE repository_id = ?', (rid,)).fetchone()[0]
    
    obs_pos = cursor.execute('SELECT COUNT(*) FROM observations WHERE repository_id = ? AND label = 1', (rid,)).fetchone()[0]
    obs_clean = cursor.execute('SELECT COUNT(*) FROM observations WHERE repository_id = ? AND label = 0', (rid,)).fetchone()[0]
    obs_unc = cursor.execute('SELECT COUNT(*) FROM observations WHERE repository_id = ? AND label = -1', (rid,)).fetchone()[0]
    
    feat_succ = cursor.execute('SELECT COUNT(*) FROM features f JOIN observations o ON f.observation_id = o.id WHERE o.repository_id = ? AND f.status = ?', (rid, 'success')).fetchone()[0]
    feat_fail = cursor.execute('SELECT COUNT(*) FROM features f JOIN observations o ON f.observation_id = o.id WHERE o.repository_id = ? AND f.status = ?', (rid, 'failed')).fetchone()[0]
    
    ds1_cnt = cursor.execute('SELECT COUNT(*) FROM dataset_observations do JOIN observations o ON do.observation_id = o.id WHERE do.dataset_id = 1 AND o.repository_id = ?', (rid,)).fetchone()[0]
    ds1_pos = cursor.execute('SELECT COUNT(*) FROM dataset_observations do JOIN observations o ON do.observation_id = o.id WHERE do.dataset_id = 1 AND o.repository_id = ? AND o.label = 1', (rid,)).fetchone()[0]
    ds1_clean = cursor.execute('SELECT COUNT(*) FROM dataset_observations do JOIN observations o ON do.observation_id = o.id WHERE do.dataset_id = 1 AND o.repository_id = ? AND o.label = 0', (rid,)).fetchone()[0]
    
    print(f'Repo #{rid} ({name}):')
    print(f'  Commits: {commits}, Fixes: {fixes}')
    print(f'  SZZ Traces: {traces}, Unique BICs: {bics}')
    print(f'  DB Observations: Total={obs_pos + obs_clean + obs_unc} (Pos={obs_pos}, Clean={obs_clean}, Unc={obs_unc})')
    print(f'  Features: Success={feat_succ}, Failed={feat_fail}')
    print(f'  Dataset 1 Snapshot: Total={ds1_cnt} (Pos={ds1_pos}, Clean={ds1_clean})')

