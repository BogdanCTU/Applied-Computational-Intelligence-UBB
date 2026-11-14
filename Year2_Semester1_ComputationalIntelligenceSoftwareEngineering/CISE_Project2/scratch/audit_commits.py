from src.database.connection import Database

db = Database('data/database/bug_detection.db')
with db.session() as conn:
    rows = conn.execute("""
        SELECT commit_sha, author_name, committed_date, message, is_bug_fix, bug_fix_confidence, bug_fix_evidence
        FROM commits
        WHERE repository_id = 14 AND is_bug_fix = 1
        ORDER BY committed_date DESC
    """).fetchall()

print(f"Total classified bug-fixing commits: {len(rows)}")
for i, r in enumerate(rows, 1):
    first_line = r['message'].splitlines()[0] if r['message'] else ''
    print(f"\n--- Commit {i}: {r['commit_sha'][:8]} (Conf: {r['bug_fix_confidence']}) ---")
    print(f"Date: {r['committed_date']}")
    print(f"Author: {r['author_name']}")
    print(f"Message: {first_line}")
    print(f"Evidence: {r['bug_fix_evidence']}")
