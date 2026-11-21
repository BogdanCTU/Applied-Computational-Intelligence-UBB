# System Architecture — Agent-OM Local Replication and Desktop Workbench

## 1. Architectural Overview

Agent-OM implements a **Modular Layered and Siamese Agent Architecture**. The system separates user interface presentation (`1_Source/gui/`), application services (`1_Source/services/`), domain agent orchestration (`1_Source/agents/`), retrieval and matching algorithms (`1_Source/retrieval/`, `1_Source/matching/`), local LLM and embedding providers (`1_Source/llm/`), and relational-vector persistence (`1_Source/database/`).

```mermaid
flowchart TD
    subgraph UI["Presentation Layer (1_Source/gui/ & run_gui.py)"]
        MW["MainWindow (10 Views)"]
    end

    subgraph SVC["Application Service Layer (1_Source/services/)"]
        ES["EnvironmentService"]
        DS["DatasetService"]
        CS["ConfigurationService"]
        RS["ExperimentRunnerService (QThread)"]
        IS["PipelineInspectionService"]
        EVS["EvaluationService & ReportGenerationService"]
    end

    subgraph AGENTS["Siamese Agent Layer (1_Source/agents/)"]
        RA["RetrievalAgent"]
        MA["MatchingAgent"]
        TR["LLMJsonToolRouter / Deterministic Orchestrator"]
    end

    subgraph ALGO["Core Domain & Algorithm Layer (1_Source/core/, retrieval/, matching/)"]
        OP["OntologyGraph & EntityExtractor"]
        SR["SyntacticRetriever (breame)"]
        LR["LexicalRetriever (10 Predicates)"]
        SMR["SemanticRetriever (18 Predicates + BNodes)"]
        RRF["Reciprocal Rank Fusion (k=0)"]
        MV["MatchingValidator (Exact Bypass + LLM)"]
        RM["ReciprocalMerger (Bidirectional Intersection)"]
    end

    subgraph INFRA["Local Infrastructure Layer (1_Source/llm/ & 1_Source/database/)"]
        LCP["LocalChatProvider & ModelValidator (<=4.0B Check)"]
        LEP["LocalEmbeddingProvider & LlamaEmbeddingBridge"]
        DBM["DatabaseManager (Write-Guard on agent_om_local)"]
        OLLAMA[("Local Ollama Daemon\n127.0.0.1:11434")]
        PG[("PostgreSQL 16 + pgvector\n127.0.0.1:5432")]
    end

    MW --> SVC
    RS --> RA
    RS --> MA
    RA --> TR
    MA --> TR
    RA --> OP
    RA --> SR
    RA --> LR
    RA --> SMR
    RA --> RRF
    MA --> RRF
    MA --> MV
    MA --> RM
    LR --> LCP
    SMR --> LCP
    MV --> LCP
    RA --> LEP
    RA --> DBM
    MA --> DBM
    LCP --> OLLAMA
    LEP --> OLLAMA
    DBM --> PG
```

---

## 2. Component Responsibilities and Dependencies

1. **Presentation Layer (`1_Source/gui/views/`, `1_Source/gui/main_window.py`):**
   - Renders 10 screens using `PySide6.QtWidgets` and `matplotlib.backends.backend_qtagg`.
   - Never executes blocking I/O, SQL queries, or HTTP calls directly on the Qt event thread; delegates all long-running runs to `ExperimentRunnerService` (`QThread`).
2. **Service Layer (`1_Source/services/` / `1_Source/gui/services/`):**
   - `EnvironmentService`, `DatabaseService`, and `OllamaService` inspect local loopback sockets and database schemas.
   - `ConfigurationService` validates the 7 profiles (`AppConfig`) and enforces database write protection and strict $\le 4.0\text{B}$ model constraints.
   - `PipelineInspectionService`, `ArtifactComparisonService`, `EvaluationService`, and `ReportGenerationService` load run bundles and compute 17-point comparisons.
3. **Siamese Agent Layer (`1_Source/agents/`):**
   - `RetrievalAgent` coordinates ontology parsing, entity extraction, 3-view representation generation, vector ingestion, and directional candidate retrieval.
   - `MatchingAgent` coordinates directional RRF candidate grouping, exact-name bypasses, score-group LLM validation, and reciprocal alignment merging.
4. **LLM & Embedding Provider Layer (`1_Source/llm/`):**
   - `OllamaClient` manages loopback HTTP calls to `127.0.0.1:11434`.
   - `ModelRegistry` and `ModelValidator` inspect `/api/show` (`general.parameter_count`), block models exceeding $4,000,000,000$ parameters in strict $\le 4\text{B}$ profiles, and probe live embedding dimensions.
5. **Database Layer (`1_Source/database/database_manager.py`):**
   - Manages synchronous `psycopg2` connections with `pgvector` registration, creates `ontology_matching` and the three `vector(N)` chunk tables, executes cosine similarity queries (`1 - (embedding <=> query) >= threshold`), and blocks destructive operations on `agent_om_local`.

---

## 3. End-to-End Execution Data Flow

```mermaid
sequenceDiagram
    participant User as User / CLI / GUI
    participant Runner as run_local_replication.py
    participant Val as ModelValidator (1_Source/llm/)
    participant Ret as RetrievalAgent
    participant DB as PostgreSQL + pgvector (127.0.0.1:5432)
    participant Ol as Local Ollama (127.0.0.1:11434)
    participant Mat as MatchingAgent

    User->>Runner: Start Experiment (profile, experiment_id)
    Runner->>Val: validate_chat_model() & validate_embedding_model()
    Val->>Ol: POST /api/show & POST /api/embed (probe)
    Ol-->>Val: general.parameter_count <= 4.0B & vector_dim verified
    Runner->>Ret: load_ontology(source.xml, target.xml) & extract_entities()
    Ret->>Ol: Generate Lexical & Semantic Verbalizations (/api/chat)
    Ret->>Ol: Embed 500-char Chunks (/api/embed)
    Ret->>DB: Insert ontology_matching + 3 vector(N) tables
    Runner->>Mat: run_pipeline(validate=True, reciprocal_merger=True)
    Mat->>DB: Query Top-k Cosine Candidates (S2T & T2S) + RRF (k=0)
    Mat->>Ol: Score-Group Validation Prompts (with Exact-Name Bypass)
    Mat->>Mat: ReciprocalMerger.merge_alignments(S2T, T2S)
    Mat-->>Runner: Final Predictions, 6-Variant Metrics & Stage Attrition
    Runner-->>User: Write immutable artifacts to output/replication_runs/<id>/
```
