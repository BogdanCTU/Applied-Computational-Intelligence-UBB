# Features Specification: Roslyn Static Code Metrics

The .NET Roslyn Analyzer (`Microsoft.CodeAnalysis.CSharp`) extracts a deterministic vector of 26 method-level structural and complexity features:

| Category | Metric Name | Definition & Roslyn Calculation Rule | Theoretical Defect Rationale |
| :--- | :--- | :--- | :--- |
| **Basic Size** | `loc` | Non-empty physical lines spanning the method syntax node. | Larger methods correlate with higher bug probability. |
| **Basic Size** | `logical_loc` | Count of executable statements + 1 for expression body. | Measures procedural density regardless of formatting. |
| **Basic Size** | `method_length` | Total raw character count (`rawText.Length`) of the method text including whitespace and trivia. | Captures overall body breadth and character footprint; distinct from physical line count. |
| **Basic Size** | `parameter_count` | Count of formal parameters in `method.ParameterList.Parameters`. | High parameter count increases cognitive load and interface mismatch bugs. |
| **Basic Size** | `local_variable_count` | Count of `VariableDeclaratorSyntax` nodes owned by the method. | Indicates complex internal mutable state. |
| **Basic Size** | `statement_count` | Count of `StatementSyntax` descendants (excluding the outer method block). | Procedural statement complexity. |
| **Basic Size** | `return_count` | Count of `ReturnStatementSyntax` nodes (or 1 if expression-bodied). | Multiple exit points complicate control flow reasoning. |
| **Complexity** | `cyclomatic_complexity` | McCabe Cyclomatic Complexity: $1 + \text{if} + \text{ternary} + \text{loops} + \text{switch cases} + \text{catch} + \text{logical ops}$. | Measures linearly independent paths through the method. |
| **Complexity** | `max_nesting_depth` | Deepest block nesting level (`if`, `while`, `for`, `switch`, `try`, `using`, `lock`). | Deep nesting heavily correlates with developer comprehension errors. |
| **Complexity** | `boolean_operator_count` | Bitwise & unary boolean negation operators (`!`, `^`, `&`, `\|`). | Complex boolean conditions harbor edge-case bugs. |
| **Complexity** | `logical_operator_count` | Short-circuit boolean operators (`&&`, `\|\|`, null-coalescing `??`). | Compound boolean predicate density. |
| **Complexity** | `conditional_expression_count`| Ternary conditional expressions (`? :`). | Inlined branching prone to precedence bugs. |
| **Control Flow** | `if_count` | Count of `IfStatementSyntax` nodes. | Decision branching points. |
| **Control Flow** | `switch_count` | Count of `SwitchStatementSyntax` and `SwitchExpressionSyntax` nodes. | Multi-way selection branches. |
| **Control Flow** | `loop_count` | Total `for`, `foreach`, `while`, and `do-while` loops. | Iterations prone to off-by-one and boundary errors. |
| **Control Flow** | `try_catch_count` | Count of `TryStatementSyntax` blocks. | Complex exception handling and recovery logic. |
| **Control Flow** | `throw_count` | Count of explicit `throw` statements and expressions. | Failure-raising points. |
| **Control Flow** | `break_continue_count` | Count of `break` and `continue` jump statements. | Non-linear loop exits. |
| **Structure / OOP**| `method_call_count` | Count of `InvocationExpressionSyntax` nodes. | High coupling to other functions and external components. |
| **Structure / OOP**| `field_access_count` | Member access expressions targeting fields (lowercase / `_`). | High coupling to instance/class variables. |
| **Structure / OOP**| `property_access_count`| Member access expressions targeting properties (PascalCase). | Encapsulation interaction density. |
| **Structure / OOP**| `assignment_count` | Count of `AssignmentExpressionSyntax` expressions. | State mutation frequency. |
| **Structure / OOP**| `object_creation_count`| Count of `new Foo(...)` object allocations. | Coupling to concrete implementations. |
| **Structure / OOP**| `is_static` | Boolean flag (1 if method contains `static` modifier, else 0). | Stateless routines avoid instance-level mutation bugs but may indicate procedural coupling. |
| **Structure / OOP**| `is_async` | Boolean flag (1 if method contains `async` modifier, else 0). | Async state machines and task scheduling introduce concurrency/deadlock edge cases. |
| **Structure / OOP**| `is_generic` | Boolean flag (1 if method has type parameter list, else 0). | Type-parameterized methods handle arbitrary types, increasing polymorphic edge-case risks. |

---

## Inference Invariants & Processing (Phase 6)

1. **Standalone Method Parsing (`__DummyContainer__`)**:
   When users input a standalone method snippet into the prediction interface without an enclosing class or namespace, the Roslyn Analyzer detects the absence of type containers and wraps the snippet inside `class __DummyContainer__ { ... }` prior to generating the AST. This enables valid compilation and AST navigation without requiring boilerplate from the user.

2. **Local Functions & Lambdas Isolation**:
   Statements, returns, variable declarations, and loops occurring inside nested local functions (`LocalFunctionStatementSyntax`) or lambda expressions (`SimpleLambdaExpressionSyntax`, `ParenthesizedLambdaExpressionSyntax`) are not counted toward the enclosing method's metrics. This ensures helper statements do not inflate the outer method's complexity metrics.

3. **Preprocessing Alignment**:
   During inference, extracted metrics are aligned to the exact input columns (`feature_names_in_`) of the fitted `DataPreprocessor` bundled with the model. Missing columns are imputed with training medians, and constant features dropped during training are filtered out before being passed to `RandomForestClassifier.predict()` and `predict_proba()`.

4. **Cross-Platform Determinism**:
   All source code is normalized (`\r\n` $\to$ `\n`, `\r` $\to$ `\n`) before parsing to ensure that character offsets and line counts remain invariant across Windows and macOS environments.
