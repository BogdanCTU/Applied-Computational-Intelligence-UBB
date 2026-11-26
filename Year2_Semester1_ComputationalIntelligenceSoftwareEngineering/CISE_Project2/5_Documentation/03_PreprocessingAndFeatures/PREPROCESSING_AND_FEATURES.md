# C# Preprocessing and Feature Engineering

## 1. Roslyn Preprocessing (`2_SourceCode/RoslynPreprocessor/`)

Built on `Microsoft.CodeAnalysis.CSharp 4.12.0` (`.NET 9.0`), `RoslynPreprocessor.dll` accepts full `.cs` files (`mode="file"`) or isolated method snippets (`mode="method_snippet"`) over a persistent streaming JSONL `batch` bridge (`2_SourceCode/bug_detector/preprocessing/roslyn_bridge.py`).

### Supported C# Constructs
- Type containers: `class`, `struct`, `record`, and arbitrarily nested types (`Outer.Inner`).
- Method declarations: ordinary methods, constructors, `static` methods, generic methods, `async` methods, expression-bodied (`=>`) methods, and overloaded methods (distinguished by full Roslyn `method_signature`).
- Syntax error safety: `tree.GetDiagnostics()` records every `DiagnosticSeverity.Error`. Any syntax error sets `has_syntax_errors = true` and forces inference to return `ANALYSIS_ERROR` rather than `CLEAN`.

### Controlled Normalization & Tokenization (`NormalizerAndTokenizer.cs`)
- Strips comments and collapses whitespace while preserving operators, keywords, control-flow structure, identifiers/APIs, and type names.
- Abstracts arbitrary string/numeric literals (`<STR>`, `<NUM>`) while preserving defect-critical special literals (`null`, `0`, `1`, `true`, `false`, `""`).
- Emits `tokens_normalized` and `api_calls` (member invocations and `new:Type` object creations).

## 2. Five Feature Groups (`2_SourceCode/bug_detector/features/`)

| Group | Extractor Class | Features | Representation |
| --- | --- | --- | --- |
| `lexical` | `LexicalFeatureExtractor` | 20 dense token/operator/null-literal/API ratios + up to 300 token 1–2 gram TF-IDF + up to 100 API call TF-IDF (fitted strictly on training splits) | Sparse + Dense (`<= 420`) |
| `ast` | `AstFeatureExtractor` | 49 syntax-node counts & densities (expressions, statements, null-conditional `?.`, `??`, `is null`, casts, `as`/`is`, LINQ, `try`/`catch`/`using`/`lock`) | Dense (`49`) |
| `control_flow` | `ControlFlowFeatureExtractor` | 21 metrics combining branch/loop/nesting/early-return/empty-catch/broad-catch/missing-default-switch/unreachable-post-jump counts + `SemanticModel.AnalyzeControlFlow` | Dense (`21`) |
| `data_flow` | `DataFlowFeatureExtractor` | 30 metrics combining `SemanticModel.AnalyzeDataFlow` (declared, always-assigned, flows in/out, unassigned read proxy) + parameter null-check coverage, unchecked nullable dereferences, undisposed `IDisposable` allocations + explicit `semantic_model_available` / `dfg_available` / `dfg_unresolved_symbol_ratio` | Dense (`30`) |
| `structural` | `StructuralFeatureExtractor` | 16 supplementary traditional metrics (cyclomatic complexity, method LOC, logical LOC, parameter count, nesting depth, local variables, flags) | Dense (`16`) |

> **Honesty Guarantee:** When compilation references are incomplete for an isolated snippet, `semantic_model_available`, `dfg_available`, and `dfg_unresolved_symbol_ratio` record availability explicitly — semantic values are never fabricated.
