# Knowledge Graph 04 — MCP Tool Discovery and Execution Flow

## 1. MCP Discovery, Registration, and Schema Propagation Graph

```mermaid
flowchart TB
    subgraph ServerProc["Child Process: FastMCP Server (mcp_layer/server.py)"]
        FastMCP["FastMCP('local-report-sql-agent')"]
        T1["@mcp.tool() inspect_database_schema<br/>(database_tools.py)"]
        T2["@mcp.tool() get_table_sample<br/>(database_tools.py)"]
        T3["@mcp.tool() prepare_sql_query<br/>(sql_tools.py)"]
        T4["@mcp.tool() execute_readonly_sql<br/>(sql_tools.py)"]
        T5["@mcp.tool() generate_pdf_report<br/>(reporting_tools.py)"]
        T6["@mcp.tool() generate_csv_report<br/>(reporting_tools.py)"]
        FastMCP --> T1 & T2 & T3 & T4 & T5 & T6
    end

    subgraph ClientLayer["Parent Process: MCP Client & Registry"]
        MCPC["MCPClientManager (mcp_layer/client.py)<br/>• Persistent AsyncExitStack + ClientSession<br/>• JSON-RPC 2.0 over stdin/stdout"]
        Specs["list[MCPToolSpec]<br/>(name, description, input_schema)"]
        Reg["ToolRegistry (agent/tool_handler.py)<br/>• _normalize_input_schema()<br/>• DiscoveredTool instances<br/>• EXPECTED_MCP_TOOLS Completeness Gate"]
    end

    subgraph Consumers["Runtime Consumers of ToolRegistry"]
        OllamaPayload["ToolHandler.get_ollama_tools_payload()<br/>-> payload['tools'] in POST /api/chat"]
        SysPrompt["ToolRegistry.format_for_system_prompt()<br/>-> ContextBuilder 'discovered_mcp_tools' section"]
        Planner["TaskPlanner (permitted_tools validation)<br/>-> validate_plan_dag()"]
        PreExec["ToolHandler.execute_tool()<br/>-> Pre-execution tool & required_params check"]
    end

    FastMCP <-->|"stdio_client<br/>initialize & tools/list"| MCPC
    MCPC --> Specs --> Reg
    Reg --> OllamaPayload
    Reg --> SysPrompt
    Reg --> Planner
    Reg --> PreExec
```

The graph above illustrates how the 6 `@mcp.tool()` definitions in the child `FastMCP` server subprocess are discovered once via `MCPClientManager.list_tools()`, validated in `ToolRegistry`, and distributed to four consumers: `OllamaClient` (`payload["tools"]`), `ContextBuilder` (`discovered_mcp_tools` prompt section), `TaskPlanner` (`permitted_tools`), and `ToolHandler.execute_tool()`.

---

## 2. MCP Tool Invocation State Machine

```mermaid
stateDiagram-v2
    [*] --> ToolCallReceived : Ollama emits ToolCall(name, arguments)
    ToolCallReceived --> RegistryLookup : ToolHandler.execute_tool()

    RegistryLookup --> UnknownToolError : tool_name not in ToolRegistry
    RegistryLookup --> ParamNormalization : tool_name found in ToolRegistry

    ParamNormalization --> MissingParamsError : required_params missing after alias normalization
    ParamNormalization --> ApprovalGate : All required_params present

    ApprovalGate --> DispatchMCP : tool != execute_readonly_sql OR require_sql_approval == False
    ApprovalGate --> PromptUser : tool == execute_readonly_sql AND require_sql_approval == True

    PromptUser --> ApprovalDenied : User clicks "Reject Execution"
    PromptUser --> DispatchMCP : User clicks "Approve & Execute"

    DispatchMCP --> ParseMCPResult : MCPClientManager.call_tool(name, args)
    DispatchMCP --> ResetAndRetry : Transient BrokenPipe / OSError (attempt <= 2)
    ResetAndRetry --> DispatchMCP : _reset_session() & reconnect()

    ParseMCPResult --> CacheFullRows : status == "ok" / "completed"
    ParseMCPResult --> ToolExecError : status == "error" / "invalid"

    CacheFullRows --> [*] : Return ToolExecutionResult(status="success")
    UnknownToolError --> [*] : Return ToolExecutionResult(status="error")
    MissingParamsError --> [*] : Return ToolExecutionResult(status="error")
    ApprovalDenied --> [*] : Return ToolExecutionResult(status="approval_denied")
    ToolExecError --> [*] : Return ToolExecutionResult(status="error")
```

The state machine diagram above traces every validation gate, retry path, and return status inside `ToolHandler.execute_tool()` and `MCPClientManager.call_tool()`.
