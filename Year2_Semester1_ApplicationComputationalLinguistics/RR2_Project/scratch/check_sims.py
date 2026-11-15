import psycopg2

conn = psycopg2.connect(dbname='agent_om_local', user='postgres', host='127.0.0.1', port=5432)
cur = conn.cursor()

pairs = [
    ('hasAuthor', 'writtenBy'),
    ('hasBeenAssigned', 'reviewes'),
    ('hasSubjectArea', 'dealsWith'),
    ('ProgramCommitteeChair', 'Chair_PC'),
    ('ProgramCommitteeMember', 'Member_PC'),
]

for p1, p2 in pairs:
    cur.execute("""
        SELECT 'syntactic_matching' as tbl, 1 - (s.embedding <=> t.embedding) as sim
        FROM (SELECT embedding FROM syntactic_matching WHERE entity_id LIKE %s LIMIT 1) s,
             (SELECT embedding FROM syntactic_matching WHERE entity_id LIKE %s LIMIT 1) t
        UNION ALL
        SELECT 'lexical_matching' as tbl, 1 - (s.embedding <=> t.embedding) as sim
        FROM (SELECT embedding FROM lexical_matching WHERE entity_id LIKE %s LIMIT 1) s,
             (SELECT embedding FROM lexical_matching WHERE entity_id LIKE %s LIMIT 1) t
        UNION ALL
        SELECT 'semantic_matching' as tbl, 1 - (s.embedding <=> t.embedding) as sim
        FROM (SELECT embedding FROM semantic_matching WHERE entity_id LIKE %s LIMIT 1) s,
             (SELECT embedding FROM semantic_matching WHERE entity_id LIKE %s LIMIT 1) t;
    """, (f'%{p1}%', f'%{p2}%', f'%{p1}%', f'%{p2}%', f'%{p1}%', f'%{p2}%'))
    print(f"=== {p1} <-> {p2} ===")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]:.4f}")

conn.close()

