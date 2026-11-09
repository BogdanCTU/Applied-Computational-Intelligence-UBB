# Knowledge Graph 06 — Report Generation and Canonical Data Flow

## 1. Authoritative Data Transformation & Rendering Pipeline

```mermaid
flowchart TB
    subgraph Source["1. Authoritative SQL Result Cache"]
        ExecSQL["execute_readonly_sql<br/>(mcp_layer/tools/sql_tools.py)"]
        FullCache["ToolHandler._latest_sql_result & _sql_datasets<br/>(Untruncated columns + full_rows)"]
        LLMArgs["LLM Tool Call Arguments<br/>(title, summary, charts, kpis, findings)"]
    end

    subgraph Canonical["2. CanonicalSQLDataset & Consistency Engine (reporting/canonical_data.py)"]
        DS["CanonicalSQLDataset(columns, rows)<br/>• dict_rows & table_rows<br/>• column_types: numeric | date | text"]
        KPIEngine["compute_deterministic_kpis()<br/>• Total Orders / Records<br/>• Sales Volume ($)<br/>• Total Revenue ($)<br/>• Transactions<br/>• Average Order Value ($)"]
        ChartTrans["extract_and_transform_chart(ChartSpecification)<br/>• Resolve X/Y axes<br/>• Long-to-wide group pivot<br/>• Duplicate category aggregation<br/>• Top-7 + 'Other' pie slice normalization (100%)"]
        Validator["ReportConsistencyValidator.validate_report_components()<br/>• Reconcile LLM KPIs with SQL KPIs<br/>• Verify chart series sum == table column sum"]
    end

    subgraph Render["3. Vector PDF & CSV Composition (reporting/)"]
        Spec["ReportSpecification<br/>(Title, Subtitle, Executive Summary, KPIs, Findings, Sections)"]
        ChartReg["ChartRegistry.render() (25 Renderers)<br/>ReportLab Vector Drawing (Comparison, Trend, Distribution, Relationship, Hierarchical, Matrix)"]
        Platypus["compose_dynamic_pdf() / generate_pdf_file()<br/>• Vera TrueType Fonts<br/>• Portrait (<=6 cols) / Landscape (>6 cols)<br/>• LongTable(repeatRows=1) + TOTAL row<br/>• _NumberedCanvas ('Page X of Y')"]
        CSVOut["generate_csv_file()<br/>UTF-8 CSV (Single or Multi-Dataset)"]
    end

    subgraph Persist["4. Atomic Persistence & GUI Presentation"]
        TmpWrite["Write *.pdf.tmp / *.csv.tmp<br/>-> Atomic rename to reports/<stem>_<ts>_<id>.pdf|.csv"]
        Hist["ReportHistoryManager.record()<br/>-> reports/report_history.json"]
        Workspace["ReportPreviewWidget.load_report()<br/>-> Native QPdfView / CsvTableModel"]
    end

    ExecSQL --> FullCache
    FullCache --> DS
    LLMArgs --> DS
    DS --> KPIEngine
    DS --> ChartTrans
    KPIEngine --> Validator
    ChartTrans --> Validator
    Validator --> Spec
    Spec --> ChartReg --> Platypus
    Spec --> CSVOut
    Platypus --> TmpWrite
    CSVOut --> TmpWrite
    TmpWrite --> Hist --> Workspace
```

The data-flow graph above illustrates how `ToolHandler`, `CanonicalSQLDataset`, `ReportConsistencyValidator`, `ChartRegistry`, and `compose_dynamic_pdf()` collaborate to guarantee zero numerical hallucination between SQLite rows and the rendered PDF/CSV report.

---

## 2. Class Hierarchy of the Reporting Engine (`classDiagram`)

```mermaid
classDiagram
    class CanonicalSQLDataset {
        +str name
        +str sql_query
        +list~str~ columns
        +dict~str, str~ column_types
        +int row_count
        +compute_deterministic_kpis() list~dict~
        +extract_and_transform_chart(spec: ChartSpecification) TransformedChartData
    }

    class ChartSpecification {
        +str title
        +str chart_type
        +str x_axis
        +str|list~str~ y_axis
        +AggregationMethod aggregation_method
        +SortingOrder sorting
        +str grouping
    }

    class TransformedChartData {
        +str title
        +str chart_type
        +list~str~ categories
        +list~list~float~~ data_series
        +list~str~ series_names
        +list~float~ percentages
        +bool is_valid
        +str error_message
    }

    class ReportSpecification {
        +str title
        +str subtitle
        +str executive_summary
        +list~dict~ kpis
        +list~str~ findings
        +list~ReportSection~ sections
        +dict~str, dict~ datasets
        +str page_size
    }

    class ChartRegistry {
        -_renderers: dict~str, Callable~
        +register(chart_type: str, renderer: Callable)$
        +get_supported_chart_types() list~str~$
        +validate(config: ChartConfiguration, columns, rows) tuple~bool, str~$
        +render(config: ChartConfiguration, columns, rows) Drawing$
    }

    class ReportMetadata {
        +str report_id
        +str title
        +str output_format
        +str output_path
        +int record_count
        +int page_count
        +int charts_rendered
        +int tables_rendered
        +str completion_status
    }

    CanonicalSQLDataset ..> ChartSpecification : validates
    CanonicalSQLDataset --> TransformedChartData : produces
    ReportSpecification --> ChartRegistry : renders charts via
    ChartRegistry ..> CanonicalSQLDataset : extracts series via
```

The class diagram above shows the structural contracts connecting `CanonicalSQLDataset`, `ChartSpecification`, `TransformedChartData`, `ReportSpecification`, `ChartRegistry`, and `ReportMetadata`.
