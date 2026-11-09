# Knowledge Graphs, State Machines & Execution Flows

**Project**: Local Report SQL Agent  
**Format**: GitHub Flavored Markdown / Mermaid Diagrams  
**Parent Document**: [COMPLETE_SYSTEM_REFERENCE.md](file:///Users/stefanapopa/Documents/8)%20DOCUMENTE%20BOGDAN/7_Projects/Applied-Computational-Intelligence-UBB/Year2_Semester1_DeclarativeProgrammingMachineLearning/FinalProject_SQLAgent/docs/COMPLETE_SYSTEM_REFERENCE.md)

---

## 1. Global System Knowledge Graph

The following directed graph maps all primary systems, components, protocols, and data stores in the application, visualizing their interconnections and operational relationships.

```mermaid
graph TD
    classDef userLayer fill:#2c3e50,stroke:#34495e,stroke-width:2px,color:#ecf0f1;
    classDef agentLayer fill:#16a085,stroke:#1abc9c,stroke-width:2px,color:#ffffff;
    classDef mcpLayer fill:#2980b9,stroke:#3498db,stroke-width:2px,color:#ffffff;
    classDef storageLayer fill:#8e44ad,stroke:#9b59b6,stroke-width:2px,color:#ffffff;
    classDef reportLayer fill:#d35400,stroke:#e67e22,stroke-width:2px,color:#ffffff;

    User["Business User / Analyst"]:::userLayer
    GUI["PySide6 Desktop Application<br/>(MainWindow & Lateral Chat)"]:::userLayer
    Worker["AgentWorker (QThread)<br/>Non-blocking Concurrency"]:::userLayer
    ApprovalGate["SqlApprovalDialog<br/>Modal Human-in-the-Loop Gate"]:::userLayer

    Orchestrator["AgentOrchestrator<br/>Workflow Conductor"]:::agentLayer
    Planner["TaskPlanner<br/>Goal Decomposition"]:::agentLayer
    TaskManager["TaskManager<br/>Structured Task State"]:::agentLayer
    ContextBuilder["ContextBuilder<br/>128K Token Packing"]:::agentLayer
    CheckpointMgr["CheckpointManager<br/>State Snapshots & Rollback"]:::agentLayer
    SkillMgr["SkillManager<br/>Domain Skill Discovery"]:::agentLayer
    ToolHandler["ToolHandler<br/>Coercion & Compaction"]:::agentLayer
    Ollama["OllamaClient<br/>Local HTTP Daemon (11434)"]:::agentLayer

    MCPClient["MCPStdioClient<br/>Async Protocol Transport"]:::mcpLayer
    MCPServer["FastMCP Server<br/>Isolated Stdio Subprocess"]:::mcpLayer

    DB["SQLite Database (ecommerce.db)<br/>Read-Only URI + C-Authorizer"]:::storageLayer
    MemoryDB["SQLite Memory (agent_memory.db)<br/>WAL Mode Storage"]:::storageLayer
    MemRepo["SQLiteMemoryRepository<br/>Episodes, Facts & Checkpoints"]:::storageLayer

    Canonical["CanonicalSQLDataset<br/>Single Source of Truth"]:::reportLayer
    PDFComposer["DynamicPdfComposer<br/>ReportLab Platypus Engine"]:::reportLayer
    CSVGen["CsvGenerator<br/>RFC-4180 Streaming Engine"]:::reportLayer
    ChartBuilder["ChartBuilder<br/>22 Vector Graphic Types"]:::reportLayer

    User -->|Enters Query| GUI
    GUI -->|Dispatches Task| Worker
    Worker -->|Invokes Run| Orchestrator

    Orchestrator -->|Decomposes Goal| Planner
    Orchestrator -->|Updates State| TaskManager
    Orchestrator -->|Assembles Prompt| ContextBuilder
    Orchestrator -->|Snapshots State| CheckpointMgr
    Orchestrator -->|Selects Domain Rules| SkillMgr
    Orchestrator -->|Executes Tools| ToolHandler
    Orchestrator -->|Inference Query| Ollama

    ContextBuilder -->|Queries Skills| SkillMgr
    ContextBuilder -->|Queries Memory| MemRepo
    TaskManager -->|Saves State| MemRepo
    CheckpointMgr -->|Stores Checkpoints| MemRepo
    MemRepo -->|Writes Snapshots| MemoryDB

    ToolHandler -->|JSON-RPC Request| MCPClient
    MCPClient -.->|stdio stream| MCPServer

    MCPServer -->|Validates & Queries| DB
    MCPServer -->|Triggers PDF| PDFComposer
    MCPServer -->|Triggers CSV| CSVGen

    PDFComposer -->|Reads Data & KPIs| Canonical
    PDFComposer -->|Draws Visualizations| ChartBuilder
    Canonical -->|Derives Deterministically| DB

    Orchestrator -->|Prompts SQL Approval| ApprovalGate
    ApprovalGate -->|User Confirms / Denies| GUI
    GUI -->|Sends Approval to Worker| Worker
```

---

## 2. End-to-End Execution Sequence

This sequence diagram depicts the chronological message exchange for a natural language reporting request from user input to rendered report.

```mermaid
sequenceDiagram
    autonumber
    actor User as User
    participant GUI as PySide6 MainWindow
    participant Worker as AgentWorker (QThread)
    participant Orch as AgentOrchestrator
    participant Plan as TaskPlanner
    participant Ctx as ContextBuilder
    participant LLM as Ollama (qwen3.5:4b)
    participant TH as ToolHandler
    participant MCP as FastMCP Subprocess
    participant DB as SQLite (ecommerce.db)
    participant Dialog as SqlApprovalDialog

    User->>GUI: Enters prompt ("Generate monthly revenue report")
    GUI->>Worker: Starts background thread execution
    Worker->>Orch: run(prompt, approval_cb, progress_cb)
    
    Orch->>Plan: plan_task(goal)
    Plan-->>Orch: Returns TaskPlan (steps: inspect, query, generate)
    
    Orch->>Ctx: build_context(stage=PLANNING, user_prompt)
    Ctx-->>Orch: Returns AssembledContext within 128K window
    
    Orch->>LLM: /api/chat (messages, tools, num_ctx=131072)
    LLM-->>Orch: Tool call: prepare_sql_query(query)
    
    Orch->>TH: execute_tool("prepare_sql_query", args)
    TH->>MCP: JSON-RPC tools/call
    MCP-->>TH: AST Valid, 1 table, valid syntax
    TH-->>Orch: Query validated
    
    Orch->>Worker: Request SQL Approval
    Worker->>GUI: Signal: approval_requested(sql, tables)
    GUI->>Dialog: Shows modal approval dialog
    User->>Dialog: Clicks "Approve Query"
    Dialog-->>GUI: Result: APPROVED
    GUI-->>Worker: Approval confirmed
    Worker-->>Orch: Approval callback returns True
    
    Orch->>TH: execute_tool("execute_readonly_sql", args)
    TH->>MCP: JSON-RPC tools/call
    MCP->>DB: Executes with C-Authorizer + Watchdog
    DB-->>MCP: Returns 12 rows (columns: month, revenue)
    MCP-->>TH: SQL execution result
    TH-->>Orch: Formatted dataset
    
    Orch->>TH: execute_tool("generate_pdf_report", args)
    TH->>MCP: JSON-RPC tools/call
    MCP-->>TH: Report created: monthly_revenue.pdf (3 pages)
    TH-->>Orch: Report metadata
    
    Orch-->>Worker: AgentRunResult (status=success, report_path)
    Worker->>GUI: Signal: run_completed(result)
    GUI->>User: Displays message & loads PDF in QPdfView
```

---

## 3. Task & Step Lifecycle State Machines

Structured task state machines govern agent execution, guaranteeing that the agent cannot proceed blindly without explicit state validation.

### 3.1 Task State Machine

```mermaid
stateDiagram-v2
    [*] --> PENDING: Task Created
    PENDING --> IN_PROGRESS: First Step Initiated
    IN_PROGRESS --> IN_PROGRESS: Step Completed / Next Step
    IN_PROGRESS --> FAILED: Unrecoverable Error / Max Retries
    IN_PROGRESS --> CANCELLED: User Interrupted / Cancelled
    IN_PROGRESS --> COMPLETED: All Steps Succeeded
    FAILED --> [*]
    CANCELLED --> [*]
    COMPLETED --> [*]
```

### 3.2 Task Step State Machine

```mermaid
stateDiagram-v2
    [*] --> STEP_PENDING: Initialized in Plan
    STEP_PENDING --> STEP_RUNNING: Execution Dispatched
    STEP_RUNNING --> STEP_COMPLETED: Output Validated & Stored
    STEP_RUNNING --> STEP_FAILED: Tool Error / Timeout / Denied
    STEP_FAILED --> STEP_RUNNING: Self-Healing Retry
    STEP_FAILED --> STEP_SKIPPED: Non-critical Fallback
    STEP_COMPLETED --> [*]
    STEP_SKIPPED --> [*]
```

---

## 4. Context Budget Allocation Flowchart

The ContextBuilder divides the configured context window (default `131,072` tokens) into distinct segments. Optional content is included strictly by priority order until the available budget is exhausted.

```mermaid
flowchart TD
    Total["Total Configured Window (128K = 131,072 tokens)"]
    ResOut["Reserved Model Output (-1,024 tokens)"]
    Safety["Safety Buffer Margin (-256 tokens)"]
    Avail["Available Input Budget (129,792 tokens)"]

    P1["Priority 100: MANDATORY<br/>System Prompt + Stage Operating Rules + User Request"]
    CheckP1{"Does P1 Fit?"}
    Error["Raise ContextBudgetExceededError"]

    P2["Priority 75: HIGH<br/>Relevant Stage Domain Skills + Target Table Schemas"]
    CheckP2{"Does P2 Fit?"}

    P3["Priority 50: MEDIUM<br/>Structured Task State + Recent Tool Results + Recent History"]
    CheckP3{"Does P3 Fit?"}

    P4["Priority 25: LOW<br/>Semantic Domain Facts + Past Execution Traces + Older History"]
    CheckP4{"Does P4 Fit?"}

    Assemble["Assemble Final Context Payload -> Send to Ollama"]

    Total --> ResOut
    ResOut --> Safety
    Safety --> Avail

    Avail --> P1
    P1 --> CheckP1
    CheckP1 -- No --> Error
    CheckP1 -- Yes --> P2

    P2 --> CheckP2
    CheckP2 -- Yes --> IncludeP2["Include in Context"]
    CheckP2 -- No --> ExcludeP2["Safely Exclude Whole & Log"]

    IncludeP2 --> P3
    ExcludeP2 --> P3

    P3 --> CheckP3
    CheckP3 -- Yes --> IncludeP3["Include in Context"]
    CheckP3 -- No --> ExcludeP3["Safely Exclude Whole & Log"]

    IncludeP3 --> P4
    ExcludeP3 --> P4

    P4 --> CheckP4
    CheckP4 -- Yes --> IncludeP4["Include in Context"]
    CheckP4 -- No --> ExcludeP4["Safely Exclude Whole & Log"]

    IncludeP4 --> Assemble
    ExcludeP4 --> Assemble
```

---

## 5. Self-Healing SQL Recovery Loop

When a proposed SQL query fails syntax validation, table resolution, or C-authorizer security checks, the agent automatically executes a self-healing loop:

```mermaid
flowchart TD
    Generate["LLM Generates SQL Query"]
    Validate["Validation Gate: prepare_sql_query"]
    Check{"Validation Passed?"}
    
    Approve["Human Approval Gate"]
    AppCheck{"User Approved?"}
    
    Execute["Execute Query: execute_readonly_sql"]
    ExecCheck{"Execution Succeeded?"}
    
    FormulateErr["Capture Exact SQLite Error Code & Message"]
    InspectSchema["Inspect Table Schema for True Column Names"]
    Replan["Formulate Diagnostic Context Prompt"]
    RetryCount{"Retry Count < Max (3)?"}
    
    Success["Dataset Ready for Report Generation"]
    FailStop["Task Fails Gracefully with Clear Error Explanation"]
    DeniedStop["Execution Halted by User Request"]

    Generate --> Validate
    Validate --> Check
    Check -- Yes --> Approve
    Check -- No --> FormulateErr

    Approve --> AppCheck
    AppCheck -- Yes --> Execute
    AppCheck -- No --> DeniedStop

    Execute --> ExecCheck
    ExecCheck -- Yes --> Success
    ExecCheck -- No --> FormulateErr

    FormulateErr --> RetryCount
    RetryCount -- Yes --> InspectSchema
    InspectSchema --> Replan
    Replan --> Generate
    RetryCount -- No --> FailStop
```

