import sys
sys.path.insert(0, 'agent_om_local')
import rdflib
import pandas as pd
from pathlib import Path
from src.db.database_manager import DatabaseManager
from src.utils.text_processing import uri_to_name

db = DatabaseManager()
ref_path = Path('original_repo/data/conference/cmt-confof/component/reference.xml')

g = rdflib.Graph().parse(ref_path)
align_cell = rdflib.URIRef("http://knowledgeweb.semanticweb.org/heterogeneity/alignment#Cell")
align_e1 = rdflib.URIRef("http://knowledgeweb.semanticweb.org/heterogeneity/alignment#entity1")
align_e2 = rdflib.URIRef("http://knowledgeweb.semanticweb.org/heterogeneity/alignment#entity2")
align_rel = rdflib.URIRef("http://knowledgeweb.semanticweb.org/heterogeneity/alignment#relation")

ref_pairs = []
for s in g.subjects(rdflib.RDF.type, align_cell):
    rel = str(g.value(s, align_rel, None))
    if rel == "=":
        e1 = str(g.value(s, align_e1, None))
        e2 = str(g.value(s, align_e2, None))
        ref_pairs.append((e1, e2))

print(f"Loaded {len(ref_pairs)} reference pairs.")

# Map URIs to entity_ids
with db.get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT entity_id, entity_uri, source_or_target, entity_type FROM ontology_matching;")
        rows = cur.fetchall()

uri_to_eid = {r[1]: r[0] for r in rows}
eid_to_type = {r[0]: r[3] for r in rows}

strategies = ["syntactic_matching", "lexical_matching", "semantic_matching"]

def get_directional_sim(query_eid: str, target_eid: str, table_name: str) -> float:
    """Computes exact similarity when query_eid is the query and target_eid is evaluated."""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            # Query embedding
            cur.execute(f"SELECT embedding FROM {table_name} WHERE entity_id = %s;", (query_eid,))
            q_row = cur.fetchone()
            if not q_row:
                return 0.0
            q_emb = q_row[0]
            
            # Target embeddings (could be multiple chunks)
            cur.execute(f"SELECT 1 - (embedding <=> %s) FROM {table_name} WHERE entity_id = %s;", (q_emb, target_eid))
            t_rows = cur.fetchall()
            if not t_rows:
                return 0.0
            return max(r[0] for r in t_rows)

results = []
for src_uri, tgt_uri in sorted(ref_pairs, key=lambda x: uri_to_name(x[0])):
    src_eid = uri_to_eid.get(src_uri)
    tgt_eid = uri_to_eid.get(tgt_uri)
    src_name = uri_to_name(src_uri)
    tgt_name = uri_to_name(tgt_uri)
    
    row = {
        "source_name": src_name,
        "target_name": tgt_name,
        "source_uri": src_uri,
        "target_uri": tgt_uri,
        "entity_type": eid_to_type.get(src_eid, "Unknown"),
    }
    
    for strat in strategies:
        prefix = strat.split("_")[0]
        s2t = get_directional_sim(src_eid, tgt_eid, strat)
        t2s = get_directional_sim(tgt_eid, src_eid, strat)
        row[f"{prefix}_sim_s2t"] = round(s2t, 4)
        row[f"{prefix}_sim_t2s"] = round(t2s, 4)
        
    s2t_max = max(row["syntactic_sim_s2t"], row["lexical_sim_s2t"], row["semantic_sim_s2t"])
    t2s_max = max(row["syntactic_sim_t2s"], row["lexical_sim_t2s"], row["semantic_sim_t2s"])
    row["max_sim_s2t"] = round(s2t_max, 4)
    row["max_sim_t2s"] = round(t2s_max, 4)
    row["min_threshold_s2t"] = round(s2t_max, 4)
    row["min_threshold_t2s"] = round(t2s_max, 4)
    row["retrievable_at_800_s2t"] = s2t_max >= 0.800
    row["retrievable_at_800_t2s"] = t2s_max >= 0.800
    row["reciprocal_retrievable_at_800"] = (s2t_max >= 0.800) and (t2s_max >= 0.800)
    
    results.append(row)

df = pd.DataFrame(results)
print(df[["source_name", "target_name", "max_sim_s2t", "max_sim_t2s", "reciprocal_retrievable_at_800"]].to_string())

