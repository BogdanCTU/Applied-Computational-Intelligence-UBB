# Agent-OM Source-Level Replication Parity Matrix (Phase 2)

**Date:** 2026-11-02  
**Project:** Agent-OM Guided Replication and Windows Desktop Application  
**Primary Paper Reference:** Qiang, Z., Wang, W., & Taylor, K. (2024/2025). *Agent-OM: Leveraging LLM Agents for Ontology Matching*. PVLDB 18(3), pp. 516–529 (`https://doi.org/10.14778/3712221.3712222`, arXiv:`2312.00326`).  
**Upstream Repository:** `https://github.com/qzc438/ontology-llm` (`original_repo/`, verified immutable via SHA-256 `afed3137d9905945c5167559b15ef62815c64220a0aa1038ea06893e97b7c7c0`).  
**Audit Method:** Direct Python/AST and line-by-line source inspection of `original_repo/` (`run_config.py`, `util.py`, `om_ontology_to_csv.py`, `om_csv_to_database.py`, `om_database_matching.py`, `generate_anatomy_mse_benchmark.py`, `web_overrides.py`, `CHANGES.md`, `DEBUGGING_LOG.md`) and `agent_om_local/` (`src/` and `scripts/`). Zero Git commands were executed.

---

## 1. Three-Way Lineage Definition

To prevent silent mixing of paper-era behavior with later OAEI extensions, every component below is evaluated across three explicit targets:

1. **Target 1 — PVLDB 2025 Reproducibility Release (`v1.0.0` / `v1.0.1`, April 2025):**
   * Primary paper-reproduction reference (`Agent-OM` Product: `gpt-4o-2024-05-13` + `text-embedding-ada-002` at `1536` dims; `Agent-OM-Lite`: `llama3:8b` chat + `llama3:8b` embeddings at `4096` dims, `temperature=0.0, seed=42, top_p=1.0, top_k=1, repeat_penalty=1.0`).
   * Lexical retrieval extracted **2** annotation predicates (`rdfs:comment`, `skos:definition`).
   * Semantic retrieval extracted **7** structural predicates (`rdfs:subClassOf`, `rdfs:subPropertyOf`, `skos:broader`, `skos:narrower`, `owl:disjointWith`, `rdfs:domain`, `rdfs:range`) without blank-node closure expansion.
   * `util.cleaning()` invoked `enchant`/`hunspell` (`us_dict.suggest(word)[0]`) on whole phrases (documented post-hoc in `original_repo/CHANGES.md:18-89` as a no-op on multi-word names and 55% erroneous on single-word British tokens).
   * Vocabulary exclusions were applied post-hoc on `Entity1` via `util.filter_exclude_concept()` in `om_database_matching.py`.
2. **Target 2 — Later Upstream Implementation (`v1.0.2` OAEI 2025 & Audited October 2026 `HEAD`):**
   * Expanded `lexical()` from 2 to **10** annotation predicates (`om_ontology_to_csv.py:136-157`).
   * Expanded `semantic()` from 7 to **18** structural predicates (`om_ontology_to_csv.py:204-210`) and added `expand_bnode_closure_named()` (`om_ontology_to_csv.py:238-246, 450-547`).
   * Replaced `util.filter_exclude_concept()` with pre-retrieval `util.remove_exceptions()` filtering 11 vocabulary URIs across all 4 entity lists (`util.py:249-275`, `om_ontology_to_csv.py:352`, `om_database_matching.py:343`).
   * Replaced broken `enchant`/`hunspell` spelling logic with word-by-word `breame==0.1.2` (`get_american_spelling`) in `util.cleaning()` (`util.py:7, 119-141`; `CHANGES.md:90-147`).
   * Added `web_app.py` and `web_overrides.py` (`MetaPathFinder` runtime override for `run_config.py`).
3. **Target 3 — Existing Local Implementation (`agent_om_local/` Pre-Phase-4 Baseline):**
   * Modular Python package (`src/config.py`, `src/ontology/`, `src/retrieval/`, `src/db/`, `src/matching/`, `src/agents/`, `src/utils/`) built against Target 2's 10-predicate lexical / 18-predicate + BNode semantic specification, configured by default with `qwen3.5:9b` + `nomic-embed-text` (`768` dims), and evaluated in Steps 5–7D.1 by loading upstream's committed `gpt-4o` `ontology_matching.csv`.

---

## 2. Summary Classification Table (22 Components)

Allowed classifications: `Equivalent` | `Adapted` | `Missing` | `Incorrect` | `Not applicable`

| # | Component | Pre-Phase-4 Classification (vs. PVLDB `v1.0.0`) | Pre-Phase-4 Classification (vs. Upstream `HEAD`) | Primary Issue / Parity Finding | Phase 4 Action |
|---:|---|:---:|:---:|---|---|
| 1 | Configuration and orchestration | `Adapted` | `Adapted` | `.env.example` / `AppConfig` env mismatch; missing `seed`, `top_k`, `top_p`, `repeat_penalty`, `llama3:8b` (`4096`), and explicit parity profiles; Steps 5–7D bypassed local feature generation. | `4.4`, `4.5`, `4.7`, `4.10` |
| 2 | Ontology parsing | `Adapted` | `Adapted` | Format-resilient multi-format parser (`xml`/`turtle`/`n3`); produces identical RDFLib triple sets on OAEI XML/RDF/OWL (`226` CMT, `199` ConfOf). | Retain + parity test (`4.11`) |
| 3 | Entity extraction | `Adapted` | `Equivalent` | Matches `HEAD`'s `owl:Class`/`skos:Concept`, `owl:ObjectProperty`, `owl:DatatypeProperty`, `owl:Thing` exclusion, `#`/`/` check, and 11-URI `remove_exceptions` list; deduplicates multi-typed classes via `set`. | Retain + parity test (`4.3`, `4.11`) |
| 4 | Entity ordering and IDs | `Incorrect` | `Incorrect` | Local sorts `ObjectProperty` before `DatatypeProperty`; upstream sorts all properties alphabetically together in one list, shifting 3-digit `entity_id` prefixes and RRF tie-breaking. | Fix in `EntityExtractor` (`4.3`) |
| 5 | Text normalization | `Adapted` | `Equivalent` | Matches `HEAD` `util.cleaning()` (`re.sub`, single-token `change_to_snake_case` + `repair_acronyms`, `.lower()`, per-word `breame` US spelling, `.strip()`) identically; supersedes `v1.0.0`'s broken `hunspell`. | Retain + parity test (`4.11`) |
| 6 | Syntactic retrieval | `Adapted` | `Equivalent` | Identical `cleaning(entity_name)` on non-code ontologies (`cmt-confof`); deterministic `rdfs:label` before `skos:prefLabel` on multi-label code IRIs (upstream iterates unsorted `set`). | Retain + parity test (`4.11`) |
| 7 | Lexical retrieval | `Adapted` | `Adapted` | Implements `HEAD` 10-predicate scope (`v1.0.0` used 2); sorts multi-annotation `set` deterministically; strips trailing whitespace; `_ensure_llm()` omits `reasoning=False` and parity sampling params. | Add PVLDB/HEAD predicate & join parity options + LLM config (`4.5`, `4.6`) |
| 8 | Semantic retrieval | `Adapted` | `Adapted` | Implements `HEAD` 18-predicate + `expand_bnode_closure_named` scope (`v1.0.0` used 7 predicates, no BNode closure); avoids writing CWD `subgraph.ttl` / `subgraph_complex.ttl`. | Add PVLDB 7-predicate vs HEAD 18+BNode option + LLM config (`4.5`, `4.6`) |
| 9 | Feature extraction and verbalization | `Adapted` | `Adapted` | Identical prompt templates (including upstream `"natual"` typo); local strips and joins 2-part semantic verbalization with `"\n"` (`HEAD` concatenates `+=` directly); BNode `set` stringification order is hash-dependent in both. | Add exact concatenation & deterministic BNode sort options (`4.6`) |
| 10 | Document chunking | `Incorrect` | `Incorrect` | Identical `RecursiveCharacterTextSplitter([".", "\n"], 500, 0)`, **except** local replaces empty/null text with `"Information is not available."` (`1` chunk) whereas upstream strips it to `""` (`0` chunks). | Fix empty/null chunking in parity mode (`4.1`) |
| 11 | Embedding generation | `Incorrect` | `Incorrect` | `AppConfig.embedding_dimensions` lacks `"llama3:8b": 4096` (silently defaulting to `768`) and `DatabaseManager` does not validate returned vector dimensions; Ollama `0.40.13` requires `--embeddings --pooling mean` bridge for `llama3:8b`. | Add `4096` mapping, runtime dim check & bridge (`4.4`) |
| 12 | PostgreSQL schema and storage | `Adapted` | `Adapted` | Synchronous `psycopg2` `execute_values` vs `asyncpg`; adds harmless `id SERIAL PRIMARY KEY` on vector tables; lacks safety guard preventing `tests/test_retrieval_agent.py` from dropping `agent_om_local` tables. | Add protected-DB guard & isolate test DB (`4.8`, `4.11`) |
| 13 | Similarity queries | `Equivalent` | `Equivalent` | Identical `1 - (embedding <=> query_vec) >= threshold` SQL filtered by opposing `source_or_target` and matching `entity_type`, `ORDER BY similarity DESC LIMIT num_matches`, first-chunk `fetchone()`, and `top_k` deduplication. | Retain + parity test (`4.11`) |
| 14 | Similarity threshold | `Equivalent` | `Equivalent` | Both default to `similarity_threshold = 0.90`, `top_k = 3`, `num_matches = 50` with `>=` comparison in SQL (`om_database_matching.py:153,162` vs `database_manager.py:189,204`). | Retain + parity test (`4.11`) |
| 15 | RRF | `Equivalent` | `Equivalent` | Identical unsmoothed `1.0 / position` (`k = 0`) formula, excluding `Entity-Dummy`, sorted by `(-score, entity_id)` lexicographically (`om_database_matching.py:249-260` vs `rank_fusion.py:10-62`). (Note: effective tie-breaking depends on Component 4 `entity_id` prefixes!) | Fix Component 4 so tie-breaking matches 100% (`4.3`) |
| 16 | Candidate grouping | `Equivalent` | `Equivalent` | Identical `itertools.groupby` by exact float RRF score; `validate=False` selects entire `group[0]`; `validate=True` iterates `groups[:top_k]` and `break`s after the first group with `>=1` accepted candidate. | Retain + parity test (`4.11`) |
| 17 | Candidate validation | `Adapted` | `Adapted` | Same wording & `r"\b(?:yes|no)\b"` parser, **except**: (a) upstream indents lines 2–5 by 28 spaces (`om_database_matching.py:450-454`); (b) upstream always puts query entity `{a}` first (`Target` name as `{a}` in `Target->Source`), whereas `MatchingAgent` passes `query_name` as `source_name` (`{a}`), matching upstream's order despite misleading parameter name `source_name`; (c) local lacks `o1_is_code`/`o2_is_code` label resolution in `MatchingAgent`! | Add code-IRI resolution (`4.2`) & 28-space prompt parity option (`4.6`) |
| 18 | Exact-name bypass | `Incorrect` | `Incorrect` | Exact `cleaning(a).casefold() == cleaning(b).casefold()` rule matches upstream on non-code ontologies (`cmt-confof`), **but** `MatchingAgent` feeds `uri_to_name()` instead of `rdfs:label`/`skos:prefLabel` when `o1_is_code`/`o2_is_code` is `True`, breaking bypass on code-IRI ontologies! | Fix code-IRI label resolution in `MatchingAgent` (`4.2`) |
| 19 | LLM tool routing | `Missing` | `Missing` | Upstream wraps every `syntactic`, `lexical`, `semantic`, `init`, `validate`, and `merge` step in `ChatPromptTemplate | llm | JsonOutputParser() | tool_chain` (~975+ extra LLM calls on CMT–ConfOf, prone to `KeyError` on small LLMs). Local uses deterministic Python orchestration (`0` router LLM calls). | Implement optional JSON tool-routing parity mode alongside deterministic mode (`4.9`) |
| 20 | Reciprocal merging | `Equivalent` | `Equivalent` | Upstream writes `Target->Source` CSVs with header `['Entity2', 'Entity1']` and inner-joins `pd.merge(df_source, df_target, on=['Entity1', 'Entity2']).drop_duplicates()`. Local normalizes `Target->Source` pairs to `(Source_URI, Target_URI)` and computes set intersection `s2t & t2s`. Mathematically identical. | Retain + parity test (`4.11`) |
| 21 | Final alignment generation | `Adapted` | `Adapted` | Upstream writes 6 CSV files (`predict_source_no_validation.csv`, `predict_source.csv`, `predict_target_no_validation.csv`, `predict_target.csv`, `predict_no_validation.csv`, `predict.csv`) in entity-loop order; `web_app.py` optionally exports Alignment API XML. Local returns `Set[Tuple[str, str]]` in `PipelineResult` and writes sorted CSVs in experiment scripts. | Add upstream-compatible 6-CSV & Alignment XML writer utility (`4.10`, Phase 5) |
| 22 | Evaluation | `Adapted` | `Adapted` | Identical set-based `TP`, `FP`, `FN`, `Precision`, `Recall`, `F1` over `=` cells in `reference.xml`. Upstream `util.calculate_metrics()` reads CSVs with `encoding="Windows-1250"` and formats percentages to 2 decimals (`"%.2f"`); local parses `reference.xml` in UTF-8/RDFLib directly and computes full float + 4-decimal metrics without encoding corruption on UTF-8 IRIs. | Retain UTF-8/RDFLib evaluation + emit 2-decimal upstream comparison columns (Phase 5) |

---

## 3. Detailed Component-by-Component Audit

### Component 1 — Configuration and Orchestration
* **Classification:** `Adapted` (both vs. PVLDB `v1.0.0` and vs. Upstream `HEAD`; contains `.env` mismatch defect).
* **Original File & Line Range:** `original_repo/run_config.py:19-356`; `original_repo/web_overrides.py:1-131` (`HEAD` only).
* **Local File & Line Range:** `agent_om_local/src/config.py:10-72`; `agent_om_local/.env.example:1-14`; `agent_om_local/scripts/run_experiments_step6.py:103-170`.
* **Actual Behavior:**
  * Upstream `run_config.py` defines module-level globals (`llm`, `embeddings_service`, `vector_length`, `similarity_threshold=0.90`, `top_k=3`, `num_matches=50`, `context`, `alignment`, `o1_is_code`, `o2_is_code`, `connection_string`), eagerly parses `o1` and `o2` at import time (`lines 291-292`), unconditionally assigns `os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")` (`lines 32-33`, raising `TypeError` if unset), and executes `om_ontology_to_csv.py`, `om_csv_to_database.py`, and `om_database_matching.py` sequentially via `subprocess.run(["python", script], check=True)` (`lines 336-347`), continuing to subsequent scripts even if a stage fails (`line 343`).
  * Local `src/config.py` defines an `AppConfig` dataclass (`default_llm="qwen3.5:9b"`, `default_embedding_model="nomic-embed-text"`, `similarity_threshold=0.90`, `top_k=3`, `num_matches=50`, `temperature=0.0`, `num_ctx=2048`).
* **Differences:**
  1. `.env.example` defines `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `OLLAMA_HOST`, `DEFAULT_CHAT_MODEL`, `DEFAULT_EMBEDDING_MODEL`, `NUM_CTX`, `TEMPERATURE`, whereas `AppConfig` reads `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `AGENT_OM_LLM`, `AGENT_OM_EMBEDDING` and never calls `dotenv.load_dotenv()`.
  2. `AppConfig` omits `seed`, `llm_top_k`, `top_p`, `repeat_penalty`, `ollama_host`, `o1_is_code`, `o2_is_code`, and named configuration profiles (`upstream_product_reference`, `upstream_lite_parity`, `local_adapted`, `experimental`).
  3. Historical `scripts/run_experiments_step6.py` loaded `original_repo/alignment/conference/cmt-confof/component/ontology_matching.csv` instead of orchestrating `RetrievalAgent.extract_representations_for_entities()`.
* **Scientific Impact:** High. Without explicit profile separation and deterministic parameter binding, local runs cannot distinguish `Agent-OM-Lite` parity (`llama3:8b`, `4096`-dim, `seed=42, top_k=1`) from adapted `qwen3.5:9b` + `nomic-embed-text` (`768`-dim) runs, and `.env` overrides silently fail.
* **Recommended Correction:** Align `.env.example` and `AppConfig` (supporting both canonical variable sets deterministically), add explicit LLM/embedding parameters and the 4 required profiles (`4.4`, `4.5`, `4.7`, `4.10`), and block cloud execution in `upstream_product_reference`.
* **Verification Test:** `tests/test_algorithmic_parity.py::TestConfigAndProfiles`.

---

### Component 2 — Ontology Parsing
* **Classification:** `Adapted` (both vs. PVLDB `v1.0.0` and vs. Upstream `HEAD`).
* **Original File & Line Range:** `original_repo/run_config.py:19-24, 290-292`; `original_repo/util.py:38-42`.
* **Local File & Line Range:** `agent_om_local/src/ontology/parser.py:19-165`.
* **Actual Behavior:**
  * Upstream locates `source.{xml,rdf,owl}` and `target.{xml,rdf,owl}` via `find_file()` and calls `rdflib.Graph().parse(path)` using RDFLib's default parser inference.
  * Local `OntologyGraph.from_file()` maps `.xml`/`.owl`/`.rdf` → `"xml"`, `.ttl` → `"turtle"`, `.n3` → `"n3"`, `.nt` → `"nt"`, `.jsonld` → `"json-ld"`, retries fallback formats `["xml", "turtle", "n3"]` if an `.owl` file contains Turtle/N3 syntax, and wraps failures in `OntologyParseError`.
* **Differences:**
  1. Multi-format fallback and explicit `FileNotFoundError`/`OntologyParseError` handling vs. raw `rdflib.Graph().parse()`.
  2. `OntologyGraph.find_base_uri()` (`parser.py:125-126`) falls back to the first declared namespace if no empty-prefix `""` namespace exists, whereas `util.find_uri()` (`util.py:38-42`) returns `""` (note: neither upstream nor local uses `find_uri` in matching).
* **Scientific Impact:** Zero divergence on OAEI RDF/XML benchmarks (`226` triples in CMT `source.xml`; `199` triples in ConfOf `target.xml`), with improved resilience on Turtle-encoded `.owl` files.
* **Recommended Correction:** Retain `OntologyGraph.from_file()` and verify exact triple-set equality against `rdflib.Graph().parse()` on CMT and ConfOf.
* **Verification Test:** `tests/test_ontology.py::TestOntologyParser` and `tests/test_algorithmic_parity.py::TestEndToEndMiniPipeline`.

---

### Component 3 — Entity Extraction
* **Classification:** `Adapted` vs. PVLDB `v1.0.0` | `Equivalent` vs. Upstream `HEAD` (on standard OWL/SKOS ontologies).
* **Original File & Line Range:** `original_repo/om_ontology_to_csv.py:256-293, 350-352`; `original_repo/util.py:249-275`.
* **Local File & Line Range:** `agent_om_local/src/ontology/entity_extractor.py:60-240`.
* **Actual Behavior:**
  * Upstream `find_all_entities()` extracts subjects `x` where `(x, rdf:type, owl:Class)` or `(x, rdf:type, skos:Concept)` is in the graph, `x != owl:Thing`, and `"#" in x or "/" in x`, plus subjects of `(x, rdf:type, owl:ObjectProperty)` and `(x, rdf:type, owl:DatatypeProperty)` with `"#" in x or "/" in x`, then filters out the 11 anatomy/SKOS vocabulary URIs in `util.remove_exceptions()`.
  * Local `EntityExtractor.extract_entities()` applies the exact same class/concept (`owl:Class` or `skos:Concept`, `!= owl:Thing`, `"#"` or `"/"`), property (`owl:ObjectProperty`, `owl:DatatypeProperty`), BNode exclusion, and 11-URI `DEFAULT_EXCLUSIONS` rules (`lines 64-76, 141-183`).
* **Differences:**
  1. PVLDB `v1.0.0` filtered 9 URIs post-hoc on `Entity1` via `filter_exclude_concept()`; `HEAD` and local both filter the 11 URIs pre-retrieval across Source and Target.
  2. Upstream `for x in o1.subjects(RDF.type, None)` iterates once per `rdf:type` triple without deduplicating `e1_list_class`, so an entity declared with two `rdf:type` statements (e.g., punned `owl:Class` + `owl:NamedIndividual`) would appear twice in `e1_list_class`; local `raw_classes: Set[URIRef]` deduplicates classes while preserving punned `ObjectProperty` + `DatatypeProperty` entries (`lines 204-225`). On CMT–ConfOf, both extract the exact same **88 Source (29 Class, 59 Property)** and **74 Target (38 Class, 36 Property)** entities.
* **Scientific Impact:** None on CMT–ConfOf (`162` entities identical as sets). Deduplicating accidental double-`rdf:type` class rows prevents `PRIMARY KEY` collisions in `ontology_matching` (`entity_id` is indexed by row number, so duplicate rows in upstream create duplicate `entity_uri` entries).
* **Recommended Correction:** Retain `DEFAULT_EXCLUSIONS` and punned property preservation; fix property ordering in Component 4 (`4.3`).
* **Verification Test:** `tests/test_ontology.py` (`test_skos_concept_extracted_as_class`, `test_punning_property_both_object_and_datatype`).

---

### Component 4 — Entity Ordering and IDs
* **Classification:** `Incorrect` (both vs. PVLDB `v1.0.0` and vs. Upstream `HEAD`).
* **Original File & Line Range:** `original_repo/om_ontology_to_csv.py:268-286, 360-365`; `original_repo/om_csv_to_database.py:34-38`.
* **Local File & Line Range:** `agent_om_local/src/ontology/entity_extractor.py:185-226`; `agent_om_local/src/agents/retrieval_agent.py:100-117`.
* **Actual Behavior:**
  * Upstream appends `owl:ObjectProperty` and `owl:DatatypeProperty` URIs into a **single combined list** `e1_list_property` (and `e2_list_property`) and calls `.sort()` (`om_ontology_to_csv.py:270-286`), ordering all properties alphabetically by full URI regardless of property subtype. `om_csv_to_database.py:38` then assigns `entity_id = zfill(index + 1, num_digits) + "-" + source_or_target + "-" + entity_type + "-" + uri_to_name(entity_uri)`.
  * Local `EntityExtractor.extract_entities()` sorts `sorted_obj_props` (`lines 186, 204-213`) and `sorted_data_props` (`lines 187, 216-225`) **separately**, emitting all `ObjectProperty` entities before any `DatatypeProperty` entity.
* **Differences:**
  * On CMT (`49` ObjectProperties + `10` DatatypeProperties) and ConfOf (`13` ObjectProperties + `23` DatatypeProperties), datatype properties such as `http://cmt#addedBy` or `http://confOf#earlyRegistration` appear at the end of the property block in local extraction instead of at their alphabetical URI position. This changes the 3-digit `entity_id` prefix (`030-Source-Property-...` through `088-Source-Property-...` and `127-Target-Property-...` through `162-Target-Property-...`) for most properties.
* **Scientific Impact:** Moderate to High. `reciprocal_rank_fusion` breaks score ties lexicographically on `entity_id` (`(-score, entity_id)`). Changing the leading 3-digit numeric index changes tie-breaking order whenever two property candidates share an identical RRF score (e.g., `1.0` vs `1.0` or `0.5` vs `0.5`), and prevents 1-to-1 `entity_id` alignment when comparing intermediate tables in Phase 3.
* **Recommended Correction:** Update `EntityExtractor.extract_entities()` (`4.3`) so combined alphabetical property sorting (`combine_properties_sort=True` by default, matching upstream) sorts `(uri, property_kind)` pairs by `(str(uri), property_kind)` while still preserving punned `ObjectProperty` + `DatatypeProperty` entries and recording `total_object_properties` / `total_datatype_properties` accurately.
* **Verification Test:** `tests/test_algorithmic_parity.py::TestPropertyOrderingAndPunning`.

---

### Component 5 — Text Normalization
* **Classification:** `Adapted` vs. PVLDB `v1.0.0` | `Equivalent` vs. Upstream `HEAD`.
* **Original File & Line Range:** `original_repo/util.py:52-57, 88-142`; `original_repo/CHANGES.md:3-147`.
* **Local File & Line Range:** `agent_om_local/src/utils/text_processing.py:11-90`.
* **Actual Behavior:**
  * Upstream `HEAD` `util.cleaning(name)`: (1) replaces `[^A-Za-z0-9]+` with `' '`; (2) if `" "` is not in `cleaned_name`, splits camelCase via `re.compile(r'(?<!^)(?=[A-Z])').sub(' ', name)` and merges consecutive single-letter tokens via `repair_acronyms()`; (3) lowercases; (4) applies `breame.spelling.get_american_spelling` per whitespace token; (5) `.strip()`, returning original `name` if empty.
  * Local `text_processing.cleaning(name)` executes the exact same 5-step transformation using identical regexes and `breame.spelling.get_american_spelling`.
* **Differences:**
  * Relative to PVLDB `v1.0.0`, both Upstream `HEAD` and Local replace `hunspell`/`pyenchant` with `breame` (`CHANGES.md` proves `v1.0.0`'s `hunspell` depended on Linux `/usr/share/hunspell/en_GB.dic`, silently skipped multi-word phrases, and corrupted `programme` → `programmer`).
  * Between Upstream `HEAD` and Local: zero algorithmic difference (`str(name)` vs `name` on empty-string fallback).
* **Scientific Impact:** 100% parity with Upstream `HEAD`; scientifically superior and cross-platform reproducible compared to `v1.0.0`'s broken Linux-only `hunspell` dictionary guesser.
* **Recommended Correction:** Retain `text_processing.py` unchanged.
* **Verification Test:** `tests/test_text_processing.py` and Phase 3 162-entity `cleaned_name` exact-match comparison.

---

### Component 6 — Syntactic Retrieval (Feature Generation)
* **Classification:** `Adapted` vs. PVLDB `v1.0.0` | `Equivalent` vs. Upstream `HEAD` (on single-label and non-code ontologies).
* **Original File & Line Range:** `original_repo/om_ontology_to_csv.py:98-126`.
* **Local File & Line Range:** `agent_om_local/src/retrieval/syntactic_retriever.py:19-62`; `agent_om_local/src/ontology/parser.py:129-139`.
* **Actual Behavior:**
  * Resolves `entity_name` (from label if `ontology_is_code=True`, else `uri_to_name(entity)`) and returns `cleaning(entity_name)`.
* **Differences:**
  * When `ontology_is_code=True` and an entity has multiple `rdfs:label` / `skos:prefLabel` triples, upstream `get_entity_label()` (`om_ontology_to_csv.py:100-105`) unions two `set`s and iterates over them, returning whichever label happens to be **last** in hash order (`PYTHONHASHSEED`-dependent). Local `OntologyGraph.get_entity_label()` checks `rdfs:label` before `skos:prefLabel` deterministically (`EntityExtractor.extract_entity_label` currently unions sets and returns first; in Phase 4 we make all label resolvers deterministic `sorted` `rdfs:label` then `skos:prefLabel`).
* **Scientific Impact:** Zero difference on `cmt-confof` (`o1_is_code=False, o2_is_code=False`). Eliminates hash-seed non-determinism on multi-label code-IRI ontologies.
* **Recommended Correction:** Standardize deterministic label resolution across `OntologyGraph`, `EntityExtractor`, `LexicalRetriever`, `SemanticRetriever`, and `MatchingAgent` (`4.2`).
* **Verification Test:** `tests/test_syntactic_retriever.py` and `tests/test_algorithmic_parity.py::TestCodeIRILabelResolution`.

---

### Component 7 — Lexical Retrieval (Feature Generation)
* **Classification:** `Adapted` (both vs. PVLDB `v1.0.0` and vs. Upstream `HEAD`).
* **Original File & Line Range:** `original_repo/om_ontology_to_csv.py:128-190` (PVLDB `v1.0.0` diff in Step 83 `lines 88-112`).
* **Local File & Line Range:** `agent_om_local/src/retrieval/lexical_retriever.py:20-167`.
* **Actual Behavior:**
  * Extracts annotation literals for the entity, builds `Question: What is the meaning of {entity_name}?\nContext: {context}\n[Extra Information: {extra_information}\n]Answer the question within the context[ and using the extra information].\n`, and invokes the chat LLM.
* **Differences:**
  1. **Predicate scope (`v1.0.0` vs `HEAD`):** PVLDB `v1.0.0` extracted only 2 predicates (`rdfs:comment`, `skos:definition`); `v1.0.2`/`HEAD` and Local extract 10 predicates (`rdfs:comment`, `rdf:value`, `skos:definition`, `skos:notation`, `skos:note`, `skos:scopeNote`, `skos:editorialNote`, `skos:historyNote`, `skos:changeNote`, `skos:example`). (On CMT–ConfOf, only `rdfs:comment` is present, so 2-predicate and 10-predicate inputs are identical!)
  2. **Annotation set ordering:** Upstream `om_ontology_to_csv.py:157` joins `' '.join(extra_information_set)` (unsorted `set`, `PYTHONHASHSEED`-dependent when `>=2` annotations exist); Local `lexical_retriever.py:97` uses `" ".join(sorted(list(extra_set)))` deterministically.
  3. **Whitespace stripping:** Local strips outer whitespace via `str(response.content).strip()` (`line 155`); upstream returns `response.content` directly (`line 187`).
  4. **Default LLM instantiation (`DISC-07`):** `LexicalRetriever._ensure_llm()` (`lines 73-77`) only passes `model`, `temperature`, `num_ctx`—omitting `reasoning=False` (critical for `qwen3.5:9b`) and `seed`, `top_k`, `top_p`, `repeat_penalty` (critical for `Agent-OM-Lite` parity).
* **Scientific Impact:** High for `_ensure_llm()` parameters (omitting `seed=42, top_k=1, repeat_penalty=1.0` changes LLM verbalizations; omitting `reasoning=False` on `qwen3.5:9b` causes massive CoT latency). Minor/beneficial for deterministic `sorted()` set joining.
* **Recommended Correction:** Centralize LLM factory on `AppConfig` (`4.5`) so `LexicalRetriever` inherits full parity sampling parameters (`seed`, `top_k`, `top_p`, `repeat_penalty`, `reasoning`) and add `strip_responses` parity flag (`4.6`).
* **Verification Test:** `tests/test_lexical_retriever.py` and `tests/test_algorithmic_parity.py::TestLLMParametersAndFormatting`.

---

### Component 8 — Semantic Retrieval (Subgraph Extraction)
* **Classification:** `Adapted` (both vs. PVLDB `v1.0.0` and vs. Upstream `HEAD`).
* **Original File & Line Range:** `original_repo/om_ontology_to_csv.py:192-226, 238, 450-548` (PVLDB `v1.0.0` diff in Step 83 `lines 114-160, 182-282`).
* **Local File & Line Range:** `agent_om_local/src/retrieval/semantic_retriever.py:24-206`.
* **Actual Behavior:**
  * Extracts 1-hop structural triples `(entity, p, o)` (where `o != owl:Thing` and `not isinstance(o, BNode)`) and `(s, p, entity)` (where `s != owl:Thing`) across 18 OWL/RDFS/SKOS predicates, replacing subject/object URIs with `Literal(entity_name)`, plus blank-node closure triples via `expand_bnode_closure_named()`.
* **Differences:**
  1. **PVLDB `v1.0.0` vs `HEAD`:** `v1.0.0` extracted only 7 predicates and had **no** `expand_bnode_closure_named()` (OWL restriction blank nodes such as `rdfs:subClassOf [ a owl:Restriction ; owl:onProperty ... ]` in CMT and ConfOf were ignored in `v1.0.0` and added in `v1.0.2`/`HEAD`!).
  2. **Filesystem side effects:** Upstream `om_ontology_to_csv.py:225, 238, 545` overwrites `subgraph.ttl` and `subgraph_complex.ttl` in CWD on every entity (`324` file writes per CMT–ConfOf run); Local `SemanticRetriever` serializes `subgraph.serialize(format="turtle")` purely in memory (`line 239`).
  3. **Incoming BNode subjects:** In `lines 218-223` (both upstream and local `lines 120-126`), incoming triples `(s, predicate, entity)` check `if s != OWL.Thing:` without `not isinstance(s, BNode)` — matching upstream exactly.
* **Scientific Impact:** Zero difference vs. Upstream `HEAD` on extracted subgraphs, while eliminating CWD race conditions and disk writes. Substantial difference vs. PVLDB `v1.0.0` on ontologies containing OWL anonymous class restrictions (`cmt` and `confOf` both use `owl:Restriction` blank nodes!).
* **Recommended Correction:** Retain `HEAD` 18-predicate + BNode closure as default for `upstream_lite_parity` (matching `original_repo/` `HEAD`), and add optional `semantic_mode="pvl_v1"` (7 predicates, no BNode closure) in `experimental` / config if users wish to ablate `v1.0.0` vs `v1.0.2`/`HEAD` (`4.6`, `4.10`).
* **Verification Test:** `tests/test_semantic_retriever.py` and `tests/test_algorithmic_parity.py::TestLLMParametersAndFormatting`.

---

### Component 9 — Feature Extraction and Verbalization
* **Classification:** `Adapted` (both vs. PVLDB `v1.0.0` and vs. Upstream `HEAD`).
* **Original File & Line Range:** `original_repo/om_ontology_to_csv.py:227-252`.
* **Local File & Line Range:** `agent_om_local/src/retrieval/semantic_retriever.py:52-60, 207-260`.
* **Actual Behavior:**
  * Prompts LLM with `"Verbalise triples into phrases: {subgraph}"` for the 18-predicate Turtle graph and `"Verbalise the subgraph into a natual language description: {subgraph}"` for `complex_triples` (preserving upstream's exact `"natual"` spelling), falling back to `"Information is not available."` when both are empty.
* **Differences:**
  1. **Concatenation separator:** Upstream concatenates `answer += response.content` (`lines 236, 246`) with no delimiter; Local appends `str(resp.content).strip() + "\n"` (`line 242`) and `answer.strip()` (`line 255`). Because `RecursiveCharacterTextSplitter` splits on `[".", "\n"]`, inserting `"\n"` between the two verbalizations creates a clean split boundary if combined length exceeds `500` chars.
  2. **BNode `set` stringification:** Both upstream (`line 245`) and local (`line 250`) pass `Set[Tuple[str, str, str]]` directly into `PromptTemplate.format(subgraph=...)`, whose string representation order varies across processes unless `PYTHONHASHSEED` is fixed or the tuple list is sorted.
  3. **LLM config (`DISC-07`):** `SemanticRetriever._ensure_llm()` omits `reasoning=False` and parity sampling parameters (`seed`, `top_k`, `top_p`, `repeat_penalty`).
* **Scientific Impact:** Moderate. Uncontrolled LLM sampling parameters or BNode set ordering can alter semantic verbalizations and chunk embeddings.
* **Recommended Correction:** Bind `SemanticRetriever` to `AppConfig`'s LLM factory (`4.5`), support `concat_separator=""` in strict `upstream_lite_parity` vs `"\n"` in `local_adapted` (`4.6`), and optionally sort `complex_triples` when `deterministic_prompts=True`.
* **Verification Test:** `tests/test_algorithmic_parity.py::TestLLMParametersAndFormatting`.

---

### Component 10 — Document Chunking
* **Classification:** `Incorrect` (both vs. PVLDB `v1.0.0` and vs. Upstream `HEAD`).
* **Original File & Line Range:** `original_repo/om_csv_to_database.py:39-41, 78-93`.
* **Local File & Line Range:** `agent_om_local/src/db/database_manager.py:97-115`; `agent_om_local/src/agents/retrieval_agent.py:100-128`.
* **Actual Behavior:**
  * Upstream `om_csv_to_database.py:40-41` executes `df = df.fillna('')` and `df.replace(null_value_sentence, "", inplace=True)` **before** storing `ontology_matching` and **before** chunking. When `matching == ""`, `RecursiveCharacterTextSplitter(separators=[".", "\n"], chunk_size=500, chunk_overlap=0, length_function=len).create_documents([""])` returns `[]` (**0 chunks**).
  * Local `RetrievalAgent.build_features_dataframe()` leaves `"Information is not available."` intact in `df`, and `DatabaseManager.create_embedding_table()` (`lines 108-110`) additionally forces empty strings back to `config.null_value_sentence` (`if not matching_text.strip(): matching_text = config.null_value_sentence`), producing **1 embedded chunk** (`"Information is not available."`) for every entity lacking semantic (or lexical) information!
* **Differences:**
  * `0` vector rows in `semantic_matching` for isolated entities in upstream vs. `1` placeholder vector row in local.
* **Scientific Impact:** **High (`DISC-04` defect).** Two completely unrelated isolated entities in Source and Target share the exact same `"Information is not available."` embedding vector, yielding cosine similarity `1.000000 >= 0.90`! This injects false-positive Rank-1 (`score = 1.0`) semantic candidates into RRF for isolated entities. (In CMT–ConfOf's committed CSV, all 162 entities had non-empty semantic text so Steps 5–7D were spared, but any ontology with isolated classes/properties—such as `conference#Organization` or `mouse.owl#MA_0001017` noted in `DEBUGGING_LOG.md:157,170`—suffers false semantic matches.)
* **Recommended Correction:** In `DatabaseManager.create_embedding_table()` and `RetrievalAgent.build_features_dataframe()` (`4.1`), strip `null_value_sentence` (`"Information is not available."`) to `""` and skip empty strings (`0` chunks) when `skip_empty_chunks=True` (default in `upstream_lite_parity` and `local_adapted`, with legacy behavior opt-in only if explicitly requested). Also handle `0`-chunk tables cleanly without issuing empty `INSERT` SQL.
* **Verification Test:** `tests/test_algorithmic_parity.py::TestEmptySemanticFeatureHandling`.

---

### Component 11 — Embedding Generation
* **Classification:** `Incorrect` (silent `768`-dim fallback for `llama3:8b` and no runtime dimension check).
* **Original File & Line Range:** `original_repo/run_config.py:74-82`; `original_repo/om_csv_to_database.py:95-119`.
* **Local File & Line Range:** `agent_om_local/src/config.py:39-53`; `agent_om_local/src/db/database_manager.py:96, 117-123`; `agent_om_local/src/utils/llama_embed_bridge.py:1-315`.
* **Actual Behavior:**
  * Upstream configures `OpenAIEmbeddings("text-embedding-ada-002")` (`vector_length=1536`) for Product or `OllamaEmbeddings("llama3:8b")` (`vector_length=4096`) for `Agent-OM-Lite`, embedding in batches of `5` with 10-attempt exponential backoff.
  * Local `AppConfig.embedding_dimensions` only maps `nomic-embed-text` (`768`) and `bge-m3` (`1024`), falling back to `768` (`config.py:52`) for any other model name! `DatabaseManager` embeds in batches of `16` without verifying `len(vec) == v_len`.
  * Furthermore, empirical testing in Phase 1.2 proved that Ollama `0.40.13` rejects `/api/embed` and `/api/embeddings` for `llama3:8b` (`HTTP 501: This server does not support embeddings. Start it with --embeddings`), requiring `LlamaEmbeddingBridge` (`llama-server.exe --embeddings --pooling mean` on `127.0.0.1`).
* **Differences:**
  1. Missing `"llama3:8b": 4096` mapping + dangerous silent `768` default fallback.
  2. Missing pre-table / runtime vector dimension assertion.
  3. Ollama `0.40.13` capability restriction for causal LLM embeddings.
* **Scientific Impact:** Critical. Silent fallback to `768` causes PostgreSQL `expected 768 dimensions, not 4096` crashes or silently misconfigures vector tables; unpooled/last-token embeddings degrade cosine similarity from `0.855` to `0.546`.
* **Recommended Correction:** Register `"llama3:8b": 4096` (and `"llama3:latest": 4096`), raise an explicit `ValueError` for unknown embedding models unless `embedding_dim` is explicitly supplied, validate `len(vec) == v_len` at runtime before/during `create_embedding_table()`, and integrate `LlamaEmbeddingBridge` seamlessly for `llama3:8b` (`4.4`).
* **Verification Test:** `tests/test_algorithmic_parity.py::TestLlamaEmbeddingDimensions`.

---

### Component 12 — PostgreSQL Schema and Storage
* **Classification:** `Adapted` (both vs. PVLDB `v1.0.0` and vs. Upstream `HEAD`).
* **Original File & Line Range:** `original_repo/om_csv_to_database.py:57-73, 121-147`.
* **Local File & Line Range:** `agent_om_local/src/db/database_manager.py:18-149`; `agent_om_local/tests/test_retrieval_agent.py:40-45, 114, 157`.
* **Actual Behavior:**
  * Upstream uses `asyncpg` (`copy_records_to_table` for `ontology_matching`, row-by-row `INSERT` for `{syntactic,lexical,semantic}_matching`), executing `DROP TABLE IF EXISTS ontology_matching CASCADE` and `DROP TABLE IF EXISTS {table_name}` unconditionally on `config.connection_string`.
  * Local uses synchronous `psycopg2` with `execute_values` bulk inserts and adds `id SERIAL PRIMARY KEY` (`database_manager.py:131`) alongside `entity_id VARCHAR(1024) NOT NULL REFERENCES ontology_matching(entity_id), content TEXT, embedding vector({v_len})`.
* **Differences:**
  1. `psycopg2` bulk `execute_values` vs `asyncpg` loop (faster, fewer event-loop issues on Windows).
  2. `id SERIAL PRIMARY KEY` column added on vector tables (harmless and preserves chunk insertion order).
  3. **Test-suite hazard discovered in audit:** `tests/test_retrieval_agent.py` connects to default `DatabaseManager()` (`agent_om_local`!), drops all 4 tables with `dim=4` mock vectors, and relies on `teardown_class` (`ensure_database_populated`) to repopulate from upstream's CSV—violating the database protection rule!
* **Scientific Impact:** Schema semantics are equivalent, but unprotected `DROP TABLE` on `agent_om_local` risks destroying historical experiment state if a test interrupts before teardown.
* **Recommended Correction:** Add a database protection guard in `DatabaseManager` refusing `DROP TABLE` on `agent_om_local` unless an explicit authorization flag is passed, and update `tests/test_retrieval_agent.py` to use an isolated test database `agent_om_test` (`4.8`, `4.11`).
* **Verification Test:** `tests/test_retrieval_agent.py` and `tests/test_algorithmic_parity.py::TestDatabaseIsolationGuard`.

---

### Component 13 — Similarity Queries
* **Classification:** `Equivalent` (both vs. PVLDB `v1.0.0` and vs. Upstream `HEAD`).
* **Original File & Line Range:** `original_repo/om_database_matching.py:119-230`.
* **Local File & Line Range:** `agent_om_local/src/db/database_manager.py:150-227`.
* **Actual Behavior:**
  * Both fetch `(m.embedding, o.source_or_target, o.entity_type)` for `o.entity_id = %s` via `fetchone()` (returning `["Entity-Dummy"]` if the query entity has 0 chunks in `table_name`).
  * Both execute a CTE `vector_matches` computing cosine similarity `1 - (embedding <=> query_embedding) >= similarity_threshold`, join `ontology_matching` filtered to the opposing `source_or_target` (`Source` ↔ `Target`) and identical `entity_type` (`Class` ↔ `Class`, `Property` ↔ `Property`), `ORDER BY v.similarity DESC LIMIT num_matches`, deduplicate `entity_id` preserving highest-similarity rank order, and return the top `top_k` `entity_id`s (or `["Entity-Dummy"]` if empty).
* **Differences:**
  * Upstream interpolates `'{content_embedding}'` into the SQL string literal whereas local binds `%s` safely via `pgvector.psycopg2` parameterized queries (`lines 187-208`). Both evaluate the exact same `pgvector` `<=>` cosine distance operator on `float32` vectors.
* **Scientific Impact:** 100% mathematical and behavioral parity (verified in Step 5 audit and Phase 1 smoke test), with SQL-injection-safe parameter binding locally.
* **Recommended Correction:** Retain `DatabaseManager.query_strategy()` (optionally add `ORDER BY m.id ASC` on the query-chunk `fetchone()` so multi-chunk query selection is guaranteed deterministic even after PostgreSQL `VACUUM`).
* **Verification Test:** `tests/test_retrieval_agent.py` and Phase 3 cosine similarity comparison.

---

### Component 14 — Similarity Threshold
* **Classification:** `Equivalent` (both vs. PVLDB `v1.0.0` and vs. Upstream `HEAD`).
* **Original File & Line Range:** `original_repo/run_config.py:84-86`; `original_repo/om_database_matching.py:153, 162, 506-515`.
* **Local File & Line Range:** `agent_om_local/src/config.py:55-57`; `agent_om_local/src/db/database_manager.py:154, 189`.
* **Actual Behavior:**
  * Both enforce `1 - (embedding <=> query_vec) >= similarity_threshold` with default `similarity_threshold = 0.90`, `top_k = 3`, `num_matches = 50`, and both support passing custom thresholds for sensitivity sweeps (`om_database_matching.py:506` CLI `sys.argv[1]` vs `MatchingAgent(similarity_threshold=...)`).
* **Differences:** None.
* **Scientific Impact:** Exact parity. (Historical Step 7A/7B empirical finding: `0.90` is calibrated for anisotropic `ada-002` / `llama3:8b` embeddings, whereas isotropic `nomic-embed-text` benefits from lower thresholds in exploratory ablations—properly kept separate from unbiased `0.90` reproduction.)
* **Recommended Correction:** Retain default `0.90` in `upstream_lite_parity` and `local_adapted`, and expose configurable thresholds only in `experimental` / threshold sweeps.
* **Verification Test:** `tests/test_threshold_sensitivity.py`.

---

### Component 15 — Reciprocal Rank Fusion (RRF)
* **Classification:** `Equivalent` (formula and sorting logic; subject to Component 4 `entity_id` prefix parity).
* **Original File & Line Range:** `original_repo/om_database_matching.py:249-260, 272`.
* **Local File & Line Range:** `agent_om_local/src/retrieval/rank_fusion.py:10-62`.
* **Actual Behavior:**
  * Upstream `reciprocal_rank_fusion_all_with_grouped_scores_exclude_none(*rankings)` filters out `[null_value_matching]` (`["Entity-Dummy"]`) before calling RRF, accumulates `1 / position` (`position` starting at `1`, i.e., smoothing constant `k = 0`) across the 3 strategy rankings (`syntactic`, `lexical`, `semantic`), sorts by `(-score, item)` lexicographically, and groups ties via `itertools.groupby`.
  * Local `reciprocal_rank_fusion(*rankings, k=0, exclude_items=["Entity-Dummy"])` computes `1.0 / (k + position)` with default `k = 0`, skips excluded items before incrementing `position`, sorts by `(-x[1], str(x[0]))`, and groups by score via `itertools.groupby`.
* **Differences:**
  * Local generalizes `k` (`k=0` default matching upstream; `k=60` available for IR ablations) and filters `"Entity-Dummy"` safely inside `reciprocal_rank_fusion` as well as in `MatchingAgent.retrieve_entity_rankings()`. When inputs match, outputs are 100% identical.
* **Scientific Impact:** Exact mathematical parity (`k=0`), once Component 4 (`entity_id` property numbering) is aligned so lexicographical tie-breaking on `entity_id` uses identical prefixes.
* **Recommended Correction:** Retain `rank_fusion.py` with `k=0` default and fix Component 4 (`4.3`).
* **Verification Test:** `tests/test_rank_fusion.py` and `tests/test_algorithmic_parity.py::TestPropertyOrderingAndPunning`.

---

### Component 16 — Candidate Grouping and Early-Stopping Selection
* **Classification:** `Equivalent` (both vs. PVLDB `v1.0.0` and vs. Upstream `HEAD`).
* **Original File & Line Range:** `original_repo/om_database_matching.py:286-327`.
* **Local File & Line Range:** `agent_om_local/src/agents/matching_agent.py:133-164`.
* **Actual Behavior:**
  * **Without validation (`no_validation`):** Both take **all** candidates in the highest RRF score group (`predict_entity_list[0]`). Note that if 2 candidates tie for top score (e.g., two `1.0` single-modality rank-1 hits), both emit 2 pairs for that query entity!
  * **With validation:** Both slice the grouped RRF list to at most `top_k` score groups (`predict_entity_list[:top_k]`), validate every candidate inside the current score group in lexicographical `entity_id` order, append all `"yes"` (or bypassed) candidates in that group, and **`break` immediately after the first score group that produces at least one accepted candidate** (`if candidates_with_validation_and_merge: break` / `if accepted_in_group: break`).
* **Differences:** None.
* **Scientific Impact:** Exact behavioral parity.
* **Recommended Correction:** Retain unchanged.
* **Verification Test:** `tests/test_matching_agent.py`.

---

### Component 17 — Candidate Validation (Prompt & Directionality)
* **Classification:** `Adapted` (prompt indentation & missing code-IRI label lookup in `MatchingAgent`).
* **Original File & Line Range:** `original_repo/om_database_matching.py:263-266, 297-323, 442-459`.
* **Local File & Line Range:** `agent_om_local/src/matching/validator.py:45-182`; `agent_om_local/src/agents/matching_agent.py:130-158`.
* **Actual Behavior:**
  * Upstream `validate()` constructs:
    ```python
    prompt_validate_question = f"""Question: Is {a} equivalent to {b}?
                                Context: {context}
                                Answer the question within the context.
                                Answer yes or no. Give a short explanation.
                                """
    ```
    where `a` is the cleaned **query** entity name (`Source` entity in `Source->Target`; `Target` entity in `Target->Source`) and `b` is the cleaned **candidate** entity name (`Target` entity in `Source->Target`; `Source` entity in `Target->Source`), then parses `re.search(r'\b(?:yes|no)\b', str(text), flags=re.IGNORECASE)`.
  * Local `MatchingValidator` uses the identical regex `r"\b(?:yes|no)\b"` (`validator.py:77`) and `MatchingAgent.match_entity()` passes `source_name=query_name, target_name=cand_name` (`matching_agent.py:149-150`), which—despite the parameter names—places the **query** entity in `{a}` and **candidate** entity in `{b}` in both `Source->Target` and `Target->Source`, matching upstream's `{a}`/`{b}` order!
* **Differences:**
  1. **28-space indentation (`DISC-08`):** Upstream's triple-quoted f-string (`lines 450-454`) includes **28 leading spaces** before `Context:`, `Answer the question...`, `Answer yes or no...`, and on the trailing line; local `PROMPT_TEMPLATE` (`validator.py:45-50`) has 0 leading spaces.
  2. **Missing code-IRI resolution (`DISC-05`):** Upstream resolves `get_entity_name(..., o1, o1_is_code)` and `get_entity_name(..., o2, o2_is_code)` (`lines 297-303`) before cleaning and validating; local `MatchingAgent` calls `uri_to_name()` unconditionally (`lines 131, 144`).
  3. **Unparsed response fallback:** If `extract_yes_no` returns `None`, upstream `None == "yes"` evaluates to `False` (rejects); local `decision = parsed if parsed in ("yes", "no") else "no"` also rejects (`Equivalent`).
* **Scientific Impact:**
  * Indentation: Low on strong models, potentially non-zero on greedy (`top_k=1`) small models (`llama3:8b`) where whitespace tokenization can shift logprobs on borderline pairs.
  * Code-IRI resolution: Zero impact on `cmt-confof` (`o1_is_code=False, o2_is_code=False`), **catastrophic** on code-IRI tracks (`Anatomy` `MA_0000006` vs `NCI_C12419`, `MultiFarm`, `DH`, `Bio-ML`), where validating `"ma 0000006"` against `"nci c12419"` instead of `"head neck"` against `"head and neck"` destroys validation accuracy!
* **Recommended Correction:** Pass `source_ontology`, `target_ontology`, `o1_is_code`, `o2_is_code` (or pre-resolved label lookup map) into `MatchingAgent` (`4.2`), and add `indent_validation_prompt: bool` (`True` in `upstream_lite_parity`, `False` in `local_adapted`) to `MatchingValidator` (`4.6`).
* **Verification Test:** `tests/test_validator.py` and `tests/test_algorithmic_parity.py::TestCodeIRILabelResolution`, `TestLLMParametersAndFormatting`.

---

### Component 18 — Exact-Name Bypass
* **Classification:** `Incorrect` (on code-IRI ontologies due to `DISC-05`; `Equivalent` on non-code ontologies).
* **Original File & Line Range:** `original_repo/om_database_matching.py:297-310`.
* **Local File & Line Range:** `agent_om_local/src/matching/validator.py:80-92, 114-130`; `agent_om_local/src/agents/matching_agent.py:130-154`.
* **Actual Behavior:**
  * Both clean both entity names via `cleaning()` and compare `.casefold() == .casefold()`, immediately accepting the candidate without an LLM call when equal.
* **Differences:**
  * Because `MatchingAgent` did not resolve `rdfs:label` / `skos:prefLabel` when `o1_is_code` / `o2_is_code` is `True`, two code-IRI entities with identical human-readable labels (e.g., `ex1:C001 rdfs:label "Author"` and `ex2:D999 rdfs:label "Author"`) failed exact-name bypass in `MatchingAgent` because `"c001" != "d999"`.
* **Scientific Impact:** Zero on `cmt-confof`; high on code-IRI benchmarks (`Anatomy`, `Bio-ML`, `Biodiv`, `MSE-3`, `DH`).
* **Recommended Correction:** Resolve entity names via `o1_is_code` / `o2_is_code` (`rdfs:label` → `skos:prefLabel` → `uri_to_name`) in `MatchingAgent` before calling `validator.validate_candidate_pair()` (`4.2`).
* **Verification Test:** `tests/test_algorithmic_parity.py::TestCodeIRILabelResolution`.

---

### Component 19 — LLM Tool Routing
* **Classification:** `Missing` (intentionally replaced by deterministic Python orchestration in local baseline; optional parity mode added in Phase 4).
* **Original File & Line Range:** `original_repo/om_ontology_to_csv.py:313-322, 369-445, 556-557`; `original_repo/om_csv_to_database.py:163-196`; `original_repo/om_database_matching.py:233-246, 312-321, 399-401, 477-501, 519-520`.
* **Local File & Line Range:** `agent_om_local/src/agents/retrieval_agent.py:58-98`; `agent_om_local/src/agents/matching_agent.py:78-165, 221-260`.
* **Actual Behavior:**
  * Upstream wraps every single pipeline action (`init`, `syntactic`, `lexical`, `semantic`, `validate`, `merge`) in a LangChain LCEL chain `ChatPromptTemplate | llm | JsonOutputParser() | tool_chain`, asking the LLM to emit `{"name": "<tool>", "arguments": {...}}` on every call! On CMT–ConfOf (`162` entities), this executes:
    * Stage 1 (`om_ontology_to_csv.py`): `1` (`init`) + `162 * 3` (`486` router calls) = **`487` router LLM calls** (on top of `162` lexical + `~162` semantic verbalization calls)!
    * Stage 2 (`om_csv_to_database.py`): **`1` router LLM call** (`init`).
    * Stage 3 (`om_database_matching.py`): `1` (`init`) + `162 * 3` (`486` search router calls) + `N_val` (`validate` router calls, where `compare_list` is passed via a Python `global` variable rather than tool arguments!) + `1` (`merge`) = **`488 + N_val` router LLM calls**!
  * Total router overhead: **`~1,000+` redundant LLM invocations** whose target tool is 100% predetermined by the hardcoded prompt string (`"Retrieve syntactic information about ..."`, `"Syntactic matching for ..."`, `"Validate matching."`, `"Merge matching."`)! Furthermore, as upstream's own `CHANGES.md:178-179` and `DEBUGGING_LOG.md:155-156` document, small LLMs occasionally return `"tool"` instead of `"name"` or malformed JSON escapes, crashing the entire run with `KeyError` or `OutputParserException`.
  * Local `RetrievalAgent` and `MatchingAgent` invoke Python methods directly (`0` router LLM calls), using the LLM strictly for genuine semantic/lexical generation and candidate equivalence validation.
* **Differences:** ~1,000 LLM JSON-routing calls vs. deterministic Python method dispatch.
* **Scientific Impact:**
  * **Theoretical/Methodological:** In `Agent-OM`, every router prompt has a 1-to-1 deterministic mapping to a single tool (`"Syntactic matching for X"` → `syntactic(X)`). When the LLM obeys the JSON schema, tool routing changes **zero** algorithmic outputs while tripling LLM call count and runtime; when a small LLM violates the JSON schema, tool routing causes catastrophic runtime crashes unrelated to ontology matching quality.
* **Recommended Correction:** Preserve deterministic Python orchestration as default in `local_adapted`, and implement an explicit, opt-in `LLMJsonToolRouter` (`tool_routing_mode="llm_json"` vs `"deterministic"`, with configurable strict vs. tolerant `"name"`/`"tool"` key parsing) in `src/agents/` (`4.9`) so parity overhead and reliability can be measured empirically without slowing down every run.
* **Verification Test:** `tests/test_algorithmic_parity.py::TestLLMToolRoutingParity`.

---

### Component 20 — Reciprocal Merging
* **Classification:** `Equivalent` (both vs. PVLDB `v1.0.0` and vs. Upstream `HEAD`).
* **Original File & Line Range:** `original_repo/om_database_matching.py:349-365, 374-391, 408-429`.
* **Local File & Line Range:** `agent_om_local/src/matching/merger.py:8-81`; `agent_om_local/src/agents/matching_agent.py:203-208, 240-247`.
* **Actual Behavior:**
  * Upstream writes `Source->Target` pairs `[entity1, candidate]` under header `['Entity1', 'Entity2']` (`lines 349-365`) and writes `Target->Source` pairs `[entity2, candidate]` under **reversed header `['Entity2', 'Entity1']`** (`lines 374-391`). In `merge()` (`lines 415, 424`), `pd.merge(df_source, df_target, on=['Entity1', 'Entity2']).drop_duplicates()` aligns columns by name (`Entity1` = Source URI, `Entity2` = Target URI), computing the exact set intersection $M_{S \to T} \cap M_{T \to S}$.
  * Local `MatchingAgent.run_directional_matching()` normalizes `Target->Source` pairs to `(cand_uri, e_uri)` = `(Source_URI, Target_URI)` (`line 207`), and `ReciprocalMerger.merge_alignments()` computes `s2t.intersection(t2s)` (also supporting `target_to_source_is_reversed=True` when given raw `(Target, Source)` tuples).
* **Differences:** Pandas DataFrame inner join + `drop_duplicates()` vs. Python `set.intersection()`.
* **Scientific Impact:** 100% mathematically identical.
* **Recommended Correction:** Retain unchanged.
* **Verification Test:** `tests/test_merger.py`.

---

### Component 21 — Final Alignment Generation
* **Classification:** `Adapted` (both vs. PVLDB `v1.0.0` and vs. Upstream `HEAD`).
* **Original File & Line Range:** `original_repo/om_database_matching.py:349-391, 413-438`; `original_repo/csv_to_alignment_api.py:1-125`; `original_repo/web_app.py:553-568`.
* **Local File & Line Range:** `agent_om_local/src/agents/matching_agent.py:31-46, 260-273`; `agent_om_local/scripts/run_experiments_step6.py:220-265`.
* **Actual Behavior:**
  * Upstream writes 6 CSV files per run (`predict_source_no_validation.csv`, `predict_source.csv`, `predict_target_no_validation.csv`, `predict_target.csv`, `predict_no_validation.csv`, `predict.csv`) with columns `Entity1,Entity2` (or `Entity2,Entity1` for target directional CSVs). `web_app.py` (`HEAD`) additionally converts `predict.csv` to OAEI Alignment API RDF/XML (`predict.xml`).
  * Local `MatchingAgent.run_pipeline()` returns in-memory `PipelineResult` (`final_predictions`, `source_to_target`, `target_to_source`, `merger_details`, validation logs, token counts); experiment runners serialize predictions and rich JSON/CSV audit logs.
* **Differences:** In-memory structured dataclass + sorted CSV/JSON writers vs. incremental file appends during entity loops.
* **Scientific Impact:** Set of final predicted alignments is unaffected by row ordering; producing all 6 upstream CSV variants in local replication runners enables direct file-for-file comparison against upstream runs.
* **Recommended Correction:** Add a reusable artifact exporter in `src/evaluation/` / replication runner that emits all 6 upstream-compatible prediction CSVs plus Alignment API XML and JSON summaries (`Phase 3` & `Phase 5`).
* **Verification Test:** `tests/test_algorithmic_parity.py::TestEndToEndMiniPipeline`.

---

### Component 22 — Evaluation
* **Classification:** `Adapted` (UTF-8/RDFLib reference parsing & full-precision metrics vs. `Windows-1250` CSV reader).
* **Original File & Line Range:** `original_repo/om_ontology_to_csv.py:68-95`; `original_repo/util.py:144-210`.
* **Local File & Line Range:** `agent_om_local/scripts/run_experiments_step6.py:65-101`; `agent_om_local/scripts/run_upstream_isolated.py:381-425`.
* **Actual Behavior:**
  * Upstream `find_reference()` (`om_ontology_to_csv.py:68-95`) parses `reference.xml` via RDFLib, extracts `Alignment#Cell` triples where `relation == "="`, writes `[e1_uri, e2_uri]` to `true.csv`, and sorts `true.csv` lexicographically (**bug note:** `lines 86-94` read `true_path` **including the header row `['Entity1', 'Entity2']`** and sort `data` by `x[0]`; it only works because `'E'` in `'Entity1'` sorts before `'h'` in `'http://...'` in ASCII!). Then `util.calculate_metrics()` reads `true.csv` and `predict*.csv` with **`encoding="Windows-1250"`** (`lines 145-146`), inner-joins on `['Entity1', 'Entity2']`, drops duplicates, and formats `Precision`, `Recall`, `F1` as 2-decimal percentage strings (`"%.2f" % (p * 100)`), returning `[0, 0, 0]` if `ra == 0` or `df_predict.empty` (without appending to `result.csv` when `ra == 0`!).
  * Local evaluation parses `reference.xml` directly via RDFLib (`relation == "="`, deduplicated set of `(Entity1, Entity2)` pairs) in UTF-8, computes exact `TP`, `FP`, `FN`, full-precision `Precision`, `Recall`, `F1` (plus 2-decimal percentages for upstream comparison), and records `0.0` runs cleanly instead of silently omitting rows from `result.csv`.
* **Differences:**
  1. `encoding="Windows-1250"` in upstream `util.calculate_metrics()` vs. UTF-8 locally (`Windows-1250` can corrupt non-ASCII IRIs in multilingual `MultiFarm` ontologies!).
  2. Upstream omits writing a row to `result.csv` when `TP == 0` (`lines 147-148, 158-159`); local always records `TP=0, P=0.0, R=0.0, F1=0.0`.
  3. Upstream's `find_reference()` sorts header + data together (`'Entity1' < 'http://'`), which would corrupt `true.csv` if an ontology used `urn:` or `ftp:` or uppercase `A://` IRIs (`'A' < 'E'`)!
* **Scientific Impact:** Identical `TP`, `FP`, `FN`, `P`, `R`, `F1` on CMT–ConfOf (`16` ASCII `http://` gold pairs), while preventing `Windows-1250` mojibake, header-sort corruption, and missing zero-score rows.
* **Recommended Correction:** Retain UTF-8 RDFLib ground-truth evaluation in local evaluation modules and report both exact float (`4`/`6` decimals) and upstream `2`-decimal percentage columns side by side.
* **Verification Test:** `tests/test_upstream_isolated_runner.py` and `tests/test_algorithmic_parity.py::TestEvaluationParity`.

---

## 4. Consolidated Phase 4 Engineering Checklist Derived from Parity Matrix

Every `Incorrect`, `Missing`, or parameter-sensitive `Adapted` item above maps directly to a concrete, regression-tested Phase 4 deliverable:

1. **`4.1` Empty Semantic Feature Handling (Component 10):** Strip `null_value_sentence` (`"Information is not available."`) to `""` and emit `0` chunks in `DatabaseManager.create_embedding_table()` when `skip_empty_chunks=True` (default in parity and adapted profiles).
2. **`4.2` Code-IRI Label Resolution (Components 6, 17, 18):** Resolve `rdfs:label` → `skos:prefLabel` → `uri_to_name` deterministically in `MatchingAgent` for both `o1_is_code` and `o2_is_code` across both matching directions (`Source->Target` and `Target->Source`).
3. **`4.3` Combined Property Ordering & Punning (Components 3, 4, 15):** Sort `ObjectProperty` and `DatatypeProperty` entities together alphabetically by URI in `EntityExtractor` (`combine_properties_sort=True` default) while preserving punned dual-type declarations, guaranteeing exact 1-to-1 `entity_id` prefixes and RRF tie-breaking parity with upstream.
4. **`4.4` Llama 4096-Dim Embedding Support & Runtime Verification (Component 11):** Add `"llama3:8b": 4096` to `AppConfig`, disallow silent `768` fallback on unknown models, validate returned embedding vector length at runtime before/during DB ingestion, and wire `LlamaEmbeddingBridge` for Ollama `0.40.13`.
5. **`4.5` Explicit LLM Sampling & Context Configuration (Components 1, 7, 8, 9, 17):** Support `temperature`, `seed`, `llm_top_k`, `top_p`, `repeat_penalty`, `num_ctx`, and `reasoning` across `LexicalRetriever`, `SemanticRetriever`, and `MatchingValidator`, verified empirically against Ollama `0.40.13`.
6. **`4.6` Prompt Formatting & Concatenation Parity Options (Components 7, 8, 9, 17):** Support 28-space validation prompt indentation, exact `""` vs `"\n"` semantic verbalization concatenation, deterministic BNode tuple sorting, and optional PVLDB `v1.0.0` (2-lexical / 7-semantic) vs `HEAD` (10-lexical / 18+BNode-semantic) retrieval scope.
7. **`4.7` Deterministic `.env` & `AppConfig` Alignment (Component 1):** Harmonize `.env.example` and `AppConfig` with `dotenv` support and strict loopback validation (zero cloud APIs).
8. **`4.8` Portable Test Paths & Protected Database Guard (Components 1, 12):** Replace stale `E:\_3_Master\_9_ACL_Project` paths in 3 test files with workspace-relative paths, add a `DatabaseManager` guard protecting `agent_om_local` against destructive `DROP TABLE`, and isolate `tests/test_retrieval_agent.py` to `agent_om_test`.
9. **`4.9` Optional LLM JSON Tool-Routing Parity Mode (Component 19):** Implement `LLMJsonToolRouter` (`tool_routing_mode="llm_json"` vs `"deterministic"`) reproducing upstream's `ChatPromptTemplate | llm | JsonOutputParser()` semantics while keeping deterministic orchestration as a separate zero-overhead mode.
10. **`4.10` Explicit Configuration Profiles (Component 1):** Provide `upstream_product_reference` (reference-only, blocks execution), `upstream_lite_parity`, `local_adapted`, and `experimental`.
11. **`4.11` Full Regression & Integration Test Suite:** Verify 100% pass rate across all existing and new `pytest` suites with zero changes to `original_repo/`, `agent_om_local` DB, or historical `output/step*` artifacts.

