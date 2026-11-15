import sys
sys.path.insert(0, 'agent_om_local')
from src.db.database_manager import DatabaseManager
from scripts.run_experiments_step6 import ensure_database_populated

db = DatabaseManager()
print("=== RUN 1 ===")
ensure_database_populated(db)

with db.get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT source_or_target, count(*) FROM ontology_matching GROUP BY source_or_target;")
        print("Run 1 Counts:", dict(cur.fetchall()))
        cur.execute("SELECT count(*) FROM syntactic_matching;")
        syn1 = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM lexical_matching;")
        lex1 = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM semantic_matching;")
        sem1 = cur.fetchone()[0]
        print(f"Chunks: syn={syn1}, lex={lex1}, sem={sem1}")

print("\n=== RUN 2 ===")
ensure_database_populated(db)

with db.get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT source_or_target, count(*) FROM ontology_matching GROUP BY source_or_target;")
        print("Run 2 Counts:", dict(cur.fetchall()))
        cur.execute("SELECT count(*) FROM syntactic_matching;")
        syn2 = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM lexical_matching;")
        lex2 = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM semantic_matching;")
        sem2 = cur.fetchone()[0]
        print(f"Chunks: syn={syn2}, lex={lex2}, sem={sem2}")

assert syn1 == syn2 and lex1 == lex2 and sem1 == sem2
print("\nPASSED: Database counts are 100% invariant across consecutive runs.")

