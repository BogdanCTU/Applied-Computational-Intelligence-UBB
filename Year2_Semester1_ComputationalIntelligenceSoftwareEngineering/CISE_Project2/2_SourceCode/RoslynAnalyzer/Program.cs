using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

namespace RoslynAnalyzer
{
    /// <summary>
    /// Represents the 26 static code metrics extracted from a C# method syntax tree via Microsoft Roslyn.
    /// </summary>
    public class MethodMetrics
    {
        [JsonPropertyName("loc")]
        public int Loc { get; set; }

        [JsonPropertyName("logical_loc")]
        public int LogicalLoc { get; set; }

        [JsonPropertyName("method_length")]
        public int MethodLength { get; set; }

        [JsonPropertyName("parameter_count")]
        public int ParameterCount { get; set; }

        [JsonPropertyName("local_variable_count")]
        public int LocalVariableCount { get; set; }

        [JsonPropertyName("statement_count")]
        public int StatementCount { get; set; }

        [JsonPropertyName("return_count")]
        public int ReturnCount { get; set; }

        [JsonPropertyName("cyclomatic_complexity")]
        public int CyclomaticComplexity { get; set; }

        [JsonPropertyName("max_nesting_depth")]
        public int MaxNestingDepth { get; set; }

        [JsonPropertyName("boolean_operator_count")]
        public int BooleanOperatorCount { get; set; }

        [JsonPropertyName("logical_operator_count")]
        public int LogicalOperatorCount { get; set; }

        [JsonPropertyName("conditional_expression_count")]
        public int ConditionalExpressionCount { get; set; }

        [JsonPropertyName("if_count")]
        public int IfCount { get; set; }

        [JsonPropertyName("switch_count")]
        public int SwitchCount { get; set; }

        [JsonPropertyName("loop_count")]
        public int LoopCount { get; set; }

        [JsonPropertyName("try_catch_count")]
        public int TryCatchCount { get; set; }

        [JsonPropertyName("throw_count")]
        public int ThrowCount { get; set; }

        [JsonPropertyName("break_continue_count")]
        public int BreakContinueCount { get; set; }

        [JsonPropertyName("method_call_count")]
        public int MethodCallCount { get; set; }

        [JsonPropertyName("field_access_count")]
        public int FieldAccessCount { get; set; }

        [JsonPropertyName("property_access_count")]
        public int PropertyAccessCount { get; set; }

        [JsonPropertyName("assignment_count")]
        public int AssignmentCount { get; set; }

        [JsonPropertyName("object_creation_count")]
        public int ObjectCreationCount { get; set; }

        [JsonPropertyName("is_static")]
        public bool IsStatic { get; set; }

        [JsonPropertyName("is_async")]
        public bool IsAsync { get; set; }

        [JsonPropertyName("is_generic")]
        public bool IsGeneric { get; set; }
    }

    /// <summary>
    /// Represents the 40 static code metrics extracted from a C# class, struct, or record syntax tree.
    /// Feature Schema Version: 3.0.0.
    /// </summary>
    public class ClassMetrics
    {
        // Size and member composition (7)
        [JsonPropertyName("class_loc")]
        public int ClassLoc { get; set; }

        [JsonPropertyName("class_logical_loc")]
        public int ClassLogicalLoc { get; set; }

        [JsonPropertyName("method_count")]
        public int MethodCount { get; set; }

        [JsonPropertyName("constructor_count")]
        public int ConstructorCount { get; set; }

        [JsonPropertyName("property_count")]
        public int PropertyCount { get; set; }

        [JsonPropertyName("field_count")]
        public int FieldCount { get; set; }

        [JsonPropertyName("nested_type_count")]
        public int NestedTypeCount { get; set; }

        // Parameter, local, and statement totals (5)
        [JsonPropertyName("total_parameter_count")]
        public int TotalParameterCount { get; set; }

        [JsonPropertyName("max_parameter_count")]
        public int MaxParameterCount { get; set; }

        [JsonPropertyName("total_local_variable_count")]
        public int TotalLocalVariableCount { get; set; }

        [JsonPropertyName("total_statement_count")]
        public int TotalStatementCount { get; set; }

        [JsonPropertyName("total_return_count")]
        public int TotalReturnCount { get; set; }

        // Complexity and nesting distributions (6)
        [JsonPropertyName("total_cyclomatic_complexity")]
        public int TotalCyclomaticComplexity { get; set; }

        [JsonPropertyName("mean_method_complexity")]
        public double MeanMethodComplexity { get; set; }

        [JsonPropertyName("max_method_complexity")]
        public int MaxMethodComplexity { get; set; }

        [JsonPropertyName("std_method_complexity")]
        public double StdMethodComplexity { get; set; }

        [JsonPropertyName("max_nesting_depth")]
        public int MaxNestingDepth { get; set; }

        [JsonPropertyName("mean_nesting_depth")]
        public double MeanNestingDepth { get; set; }

        // Control-flow and operator totals (9)
        [JsonPropertyName("total_boolean_operator_count")]
        public int TotalBooleanOperatorCount { get; set; }

        [JsonPropertyName("total_logical_operator_count")]
        public int TotalLogicalOperatorCount { get; set; }

        [JsonPropertyName("total_conditional_expression_count")]
        public int TotalConditionalExpressionCount { get; set; }

        [JsonPropertyName("total_if_count")]
        public int TotalIfCount { get; set; }

        [JsonPropertyName("total_switch_count")]
        public int TotalSwitchCount { get; set; }

        [JsonPropertyName("total_loop_count")]
        public int TotalLoopCount { get; set; }

        [JsonPropertyName("total_try_catch_count")]
        public int TotalTryCatchCount { get; set; }

        [JsonPropertyName("total_throw_count")]
        public int TotalThrowCount { get; set; }

        [JsonPropertyName("total_break_continue_count")]
        public int TotalBreakContinueCount { get; set; }

        // Coupling and usage totals (5)
        [JsonPropertyName("total_method_call_count")]
        public int TotalMethodCallCount { get; set; }

        [JsonPropertyName("total_field_access_count")]
        public int TotalFieldAccessCount { get; set; }

        [JsonPropertyName("total_property_access_count")]
        public int TotalPropertyAccessCount { get; set; }

        [JsonPropertyName("total_assignment_count")]
        public int TotalAssignmentCount { get; set; }

        [JsonPropertyName("total_object_creation_count")]
        public int TotalObjectCreationCount { get; set; }

        // Modifier counts and concentration/density ratios (8)
        [JsonPropertyName("static_method_count")]
        public int StaticMethodCount { get; set; }

        [JsonPropertyName("async_method_count")]
        public int AsyncMethodCount { get; set; }

        [JsonPropertyName("generic_method_count")]
        public int GenericMethodCount { get; set; }

        [JsonPropertyName("high_complexity_method_count")]
        public int HighComplexityMethodCount { get; set; }

        [JsonPropertyName("large_method_count")]
        public int LargeMethodCount { get; set; }

        [JsonPropertyName("complexity_concentration")]
        public double ComplexityConcentration { get; set; }

        [JsonPropertyName("structural_density")]
        public double StructuralDensity { get; set; }

        [JsonPropertyName("wmc_density")]
        public double WmcDensity { get; set; }
    }

    /// <summary>
    /// Represents the location, signature, and extracted metrics of a declared method in a syntax tree.
    /// </summary>
    public class MethodLocation
    {
        [JsonPropertyName("class_name")]
        public string ClassName { get; set; } = "";

        [JsonPropertyName("method_name")]
        public string MethodName { get; set; } = "";

        [JsonPropertyName("method_signature")]
        public string MethodSignature { get; set; } = "";

        [JsonPropertyName("start_line")]
        public int StartLine { get; set; }

        [JsonPropertyName("end_line")]
        public int EndLine { get; set; }

        [JsonPropertyName("is_static")]
        public bool IsStatic { get; set; }

        [JsonPropertyName("is_async")]
        public bool IsAsync { get; set; }

        [JsonPropertyName("is_generic")]
        public bool IsGeneric { get; set; }

        [JsonPropertyName("source_code")]
        public string SourceCode { get; set; } = "";

        [JsonPropertyName("metrics")]
        public MethodMetrics? Metrics { get; set; }
    }

    /// <summary>
    /// Represents a C# class, struct, or record declaration with isolated class-level metrics and owned methods.
    /// </summary>
    public class ClassLocation
    {
        [JsonPropertyName("class_name")]
        public string ClassName { get; set; } = "";

        [JsonPropertyName("qualified_class_name")]
        public string QualifiedClassName { get; set; } = "";

        [JsonPropertyName("namespace_name")]
        public string NamespaceName { get; set; } = "";

        [JsonPropertyName("type_kind")]
        public string TypeKind { get; set; } = "class";

        [JsonPropertyName("start_line")]
        public int StartLine { get; set; }

        [JsonPropertyName("end_line")]
        public int EndLine { get; set; }

        [JsonPropertyName("is_static")]
        public bool IsStatic { get; set; }

        [JsonPropertyName("is_generic")]
        public bool IsGeneric { get; set; }

        [JsonPropertyName("is_abstract")]
        public bool IsAbstract { get; set; }

        [JsonPropertyName("is_sealed")]
        public bool IsSealed { get; set; }

        [JsonPropertyName("is_partial")]
        public bool IsPartial { get; set; }

        [JsonPropertyName("is_nested")]
        public bool IsNested { get; set; }

        [JsonPropertyName("enclosing_type_name")]
        public string? EnclosingTypeName { get; set; }

        [JsonPropertyName("source_code")]
        public string SourceCode { get; set; } = "";

        [JsonPropertyName("metrics")]
        public ClassMetrics? Metrics { get; set; }

        [JsonPropertyName("methods")]
        public List<MethodLocation> Methods { get; set; } = new();
    }

    /// <summary>
    /// File-level metadata for analyzed C# source input.
    /// </summary>
    public class FileMetadata
    {
        [JsonPropertyName("file_path")]
        public string? FilePath { get; set; }

        [JsonPropertyName("total_lines")]
        public int TotalLines { get; set; }

        [JsonPropertyName("namespace_count")]
        public int NamespaceCount { get; set; }

        [JsonPropertyName("namespaces")]
        public List<string> Namespaces { get; set; } = new();

        [JsonPropertyName("class_count")]
        public int ClassCount { get; set; }

        [JsonPropertyName("method_count")]
        public int MethodCount { get; set; }

        [JsonPropertyName("is_wrapped_snippet")]
        public bool IsWrappedSnippet { get; set; }
    }

    /// <summary>
    /// Roslyn compiler syntax diagnostic record.
    /// </summary>
    public class DiagnosticInfo
    {
        [JsonPropertyName("id")]
        public string Id { get; set; } = "";

        [JsonPropertyName("severity")]
        public string Severity { get; set; } = "";

        [JsonPropertyName("message")]
        public string Message { get; set; } = "";

        [JsonPropertyName("line")]
        public int Line { get; set; }
    }

    /// <summary>
    /// Represents the structured JSON response payload produced by the Roslyn analyzer CLI.
    /// </summary>
    public class MethodLocatorResponse
    {
        [JsonPropertyName("analyzer_version")]
        public string AnalyzerVersion { get; set; } = "2.0.0";

        [JsonPropertyName("feature_schema_version")]
        public string FeatureSchemaVersion { get; set; } = "3.0.0";

        [JsonPropertyName("success")]
        public bool Success { get; set; } = true;

        [JsonPropertyName("file_metadata")]
        public FileMetadata FileMetadata { get; set; } = new();

        [JsonPropertyName("classes")]
        public List<ClassLocation> Classes { get; set; } = new();

        [JsonPropertyName("methods")]
        public List<MethodLocation> Methods { get; set; } = new();

        [JsonPropertyName("extraction_warnings")]
        public List<string> ExtractionWarnings { get; set; } = new();

        [JsonPropertyName("parsing_diagnostics")]
        public List<DiagnosticInfo> ParsingDiagnostics { get; set; } = new();

        [JsonPropertyName("error")]
        public string? Error { get; set; }
    }

    /// <summary>
    /// Input request item for --batch-stdin streaming mode.
    /// </summary>
    public class BatchAnalysisRequest
    {
        [JsonPropertyName("id")]
        public string Id { get; set; } = "";

        [JsonPropertyName("code")]
        public string? Code { get; set; }

        [JsonPropertyName("file_path")]
        public string? FilePath { get; set; }

        [JsonPropertyName("line")]
        public int? Line { get; set; }

        [JsonPropertyName("no_metrics")]
        public bool NoMetrics { get; set; }
    }

    /// <summary>
    /// Output envelope item for --batch-stdin streaming mode.
    /// </summary>
    public class BatchAnalysisResult
    {
        [JsonPropertyName("id")]
        public string Id { get; set; } = "";

        [JsonPropertyName("response")]
        public MethodLocatorResponse Response { get; set; } = new();
    }

    class Program
    {
        private static readonly CSharpParseOptions ParseOptions =
            CSharpParseOptions.Default.WithLanguageVersion(LanguageVersion.Latest);

        private static readonly JsonSerializerOptions JsonOptions = new()
        {
            WriteIndented = false
        };

        static int Main(string[] args)
        {
            try
            {
                string? filePath = null;
                string? code = null;
                int? targetLine = null;
                bool includeMetrics = true;
                bool batchStdin = false;

                for (int i = 0; i < args.Length; i++)
                {
                    if (args[i] == "--file" && i + 1 < args.Length)
                        filePath = args[++i];
                    else if (args[i] == "--line" && i + 1 < args.Length && int.TryParse(args[++i], out int l))
                        targetLine = l;
                    else if (args[i] == "--code" && i + 1 < args.Length)
                        code = args[++i];
                    else if (args[i] == "--no-metrics")
                        includeMetrics = false;
                    else if (args[i] == "--batch-stdin")
                        batchStdin = true;
                }

                if (batchStdin)
                {
                    return RunBatchMode(includeMetrics);
                }

                if (string.IsNullOrEmpty(code))
                {
                    if (!string.IsNullOrEmpty(filePath) && File.Exists(filePath))
                    {
                        code = File.ReadAllText(filePath);
                    }
                    else
                    {
                        using var reader = new StreamReader(Console.OpenStandardInput());
                        code = reader.ReadToEnd();
                    }
                }

                var response = AnalyzeCode(code, filePath, targetLine, includeMetrics);
                Console.WriteLine(JsonSerializer.Serialize(response, JsonOptions));
                return response.Success ? 0 : 1;
            }
            catch (Exception ex)
            {
                var errResp = new MethodLocatorResponse
                {
                    Success = false,
                    Error = ex.Message
                };
                Console.WriteLine(JsonSerializer.Serialize(errResp, JsonOptions));
                return 1;
            }
        }

        private static int RunBatchMode(bool defaultIncludeMetrics)
        {
            using var reader = new StreamReader(Console.OpenStandardInput());
            string? line;
            while ((line = reader.ReadLine()) != null)
            {
                if (string.IsNullOrWhiteSpace(line))
                    continue;

                string itemId = "";
                try
                {
                    var req = JsonSerializer.Deserialize<BatchAnalysisRequest>(line, JsonOptions);
                    if (req == null)
                        continue;

                    itemId = req.Id ?? "";
                    string? src = req.Code;
                    if (string.IsNullOrEmpty(src) && !string.IsNullOrEmpty(req.FilePath) && File.Exists(req.FilePath))
                    {
                        src = File.ReadAllText(req.FilePath);
                    }

                    var resp = AnalyzeCode(src ?? "", req.FilePath, req.Line, defaultIncludeMetrics && !req.NoMetrics);
                    var envelope = new BatchAnalysisResult { Id = itemId, Response = resp };
                    Console.WriteLine(JsonSerializer.Serialize(envelope, JsonOptions));
                }
                catch (Exception ex)
                {
                    var envelope = new BatchAnalysisResult
                    {
                        Id = itemId,
                        Response = new MethodLocatorResponse { Success = false, Error = ex.Message }
                    };
                    Console.WriteLine(JsonSerializer.Serialize(envelope, JsonOptions));
                }
            }
            Console.Out.Flush();
            return 0;
        }

        public static MethodLocatorResponse AnalyzeCode(
            string? rawCode,
            string? filePath,
            int? targetLine,
            bool includeMetrics)
        {
            if (string.IsNullOrWhiteSpace(rawCode))
            {
                return new MethodLocatorResponse
                {
                    Success = true,
                    FileMetadata = new FileMetadata { FilePath = filePath, TotalLines = 0 },
                    Classes = new List<ClassLocation>(),
                    Methods = new List<MethodLocation>()
                };
            }

            // Normalize all newlines to single \n to guarantee consistent 1-based line positions across OSes
            string code = rawCode.Replace("\r\n", "\n").Replace("\r", "\n");
            int totalInputLines = code.Split('\n').Length;

            var initialTree = CSharpSyntaxTree.ParseText(code, ParseOptions);
            var initialRoot = initialTree.GetRoot();
            bool hasDeclaredTypeOrNs =
                initialRoot.DescendantNodes().OfType<TypeDeclarationSyntax>().Any() ||
                initialRoot.DescendantNodes().OfType<BaseNamespaceDeclarationSyntax>().Any();

            string parseCode = code;
            bool wrapped = false;
            SyntaxTree tree = initialTree;
            SyntaxNode root = initialRoot;

            if (!hasDeclaredTypeOrNs)
            {
                parseCode = "class __DummyContainer__ {\n" + code + "\n}";
                wrapped = true;
                tree = CSharpSyntaxTree.ParseText(parseCode, ParseOptions);
                root = tree.GetRoot();
            }

            var text = tree.GetText();
            int lineOffset = wrapped ? 1 : 0;

            var warnings = new List<string>();
            var diagnostics = new List<DiagnosticInfo>();
            foreach (var diag in tree.GetDiagnostics().Where(d => d.Severity == DiagnosticSeverity.Error).Take(25))
            {
                var dSpan = diag.Location.GetLineSpan();
                diagnostics.Add(new DiagnosticInfo
                {
                    Id = diag.Id,
                    Severity = diag.Severity.ToString(),
                    Message = diag.GetMessage(),
                    Line = Math.Max(1, dSpan.StartLinePosition.Line + 1 - lineOffset)
                });
            }
            if (diagnostics.Count > 0)
            {
                warnings.Add($"Parsed with {diagnostics.Count} syntax error diagnostic(s); partial AST metrics may apply.");
            }

            var namespaces = root.DescendantNodes()
                .OfType<BaseNamespaceDeclarationSyntax>()
                .Select(ns => ns.Name.ToString())
                .Distinct()
                .ToList();

            // 1. Extract all methods (preserving full backward compatibility)
            var methodDeclarations = root.DescendantNodes().OfType<MethodDeclarationSyntax>().ToList();
            var allMethods = new List<MethodLocation>();
            var methodsByOwnerType = new Dictionary<TypeDeclarationSyntax, List<MethodLocation>>();

            foreach (var method in methodDeclarations)
            {
                var loc = BuildMethodLocation(method, text, lineOffset, wrapped, includeMetrics);
                var parentType = method.Ancestors().OfType<TypeDeclarationSyntax>().FirstOrDefault();

                if (parentType != null)
                {
                    if (!methodsByOwnerType.TryGetValue(parentType, out var ownerList))
                    {
                        ownerList = new List<MethodLocation>();
                        methodsByOwnerType[parentType] = ownerList;
                    }
                    ownerList.Add(loc);
                }

                if (!targetLine.HasValue || (targetLine.Value >= loc.StartLine && targetLine.Value <= loc.EndLine))
                {
                    allMethods.Add(loc);
                }
            }

            // 2. Extract class, struct, and record declarations (exclude __DummyContainer__ and interfaces)
            var classResults = new List<ClassLocation>();
            if (!wrapped)
            {
                var targetTypes = root.DescendantNodes()
                    .OfType<TypeDeclarationSyntax>()
                    .Where(IsTargetTypeDeclaration)
                    .ToList();

                foreach (var typeNode in targetTypes)
                {
                    var span = typeNode.Span;
                    var lineSpan = text.Lines.GetLinePositionSpan(span);
                    int startLine = Math.Max(1, lineSpan.Start.Line + 1);
                    int endLine = Math.Max(1, lineSpan.End.Line + 1);

                    if (targetLine.HasValue && (targetLine.Value < startLine || targetLine.Value > endLine))
                        continue;

                    string typeKind = ResolveTypeKind(typeNode);
                    string nsName = ResolveNamespaceName(typeNode);
                    var enclosingTypes = typeNode.Ancestors().OfType<TypeDeclarationSyntax>().Reverse().ToList();
                    bool isNested = enclosingTypes.Count > 0;
                    string? enclosingTypeName = isNested ? string.Join(".", enclosingTypes.Select(t => t.Identifier.Text)) : null;
                    string typeChain = isNested
                        ? $"{enclosingTypeName}.{typeNode.Identifier.Text}"
                        : typeNode.Identifier.Text;
                    string qualifiedName = string.IsNullOrEmpty(nsName) ? typeChain : $"{nsName}.{typeChain}";

                    bool isStatic = typeNode.Modifiers.Any(SyntaxKind.StaticKeyword);
                    bool isGeneric = typeNode.TypeParameterList != null && typeNode.TypeParameterList.Parameters.Count > 0;
                    bool isAbstract = typeNode.Modifiers.Any(SyntaxKind.AbstractKeyword);
                    bool isSealed = typeNode.Modifiers.Any(SyntaxKind.SealedKeyword);
                    bool isPartial = typeNode.Modifiers.Any(SyntaxKind.PartialKeyword);

                    var ownedMethods = methodsByOwnerType.TryGetValue(typeNode, out var ml)
                        ? ml
                        : new List<MethodLocation>();

                    ClassMetrics? classMetrics = includeMetrics
                        ? CalculateClassMetrics(typeNode, text, ownedMethods)
                        : null;

                    classResults.Add(new ClassLocation
                    {
                        ClassName = typeNode.Identifier.Text,
                        QualifiedClassName = qualifiedName,
                        NamespaceName = string.IsNullOrEmpty(nsName) ? "Global" : nsName,
                        TypeKind = typeKind,
                        StartLine = startLine,
                        EndLine = endLine,
                        IsStatic = isStatic,
                        IsGeneric = isGeneric,
                        IsAbstract = isAbstract,
                        IsSealed = isSealed,
                        IsPartial = isPartial,
                        IsNested = isNested,
                        EnclosingTypeName = enclosingTypeName,
                        SourceCode = typeNode.ToFullString().Trim(),
                        Metrics = classMetrics,
                        Methods = ownedMethods
                    });
                }

                // Order so targetLine queries return innermost enclosing class first
                if (targetLine.HasValue && classResults.Count > 1)
                {
                    classResults = classResults
                        .OrderBy(c => c.EndLine - c.StartLine)
                        .ThenBy(c => c.StartLine)
                        .ToList();
                }

                if (classResults.Count == 0 && !targetLine.HasValue)
                {
                    warnings.Add("No class, struct, or record declarations found in source.");
                }
            }

            return new MethodLocatorResponse
            {
                AnalyzerVersion = "2.0.0",
                FeatureSchemaVersion = "3.0.0",
                Success = true,
                FileMetadata = new FileMetadata
                {
                    FilePath = filePath,
                    TotalLines = totalInputLines,
                    NamespaceCount = namespaces.Count,
                    Namespaces = namespaces,
                    ClassCount = classResults.Count,
                    MethodCount = allMethods.Count,
                    IsWrappedSnippet = wrapped
                },
                Classes = classResults,
                Methods = allMethods,
                ExtractionWarnings = warnings,
                ParsingDiagnostics = diagnostics
            };
        }

        private static bool IsTargetTypeDeclaration(TypeDeclarationSyntax typeNode)
        {
            return typeNode is ClassDeclarationSyntax ||
                   typeNode is StructDeclarationSyntax ||
                   typeNode is RecordDeclarationSyntax;
        }

        private static string ResolveTypeKind(TypeDeclarationSyntax typeNode)
        {
            if (typeNode is RecordDeclarationSyntax rec)
            {
                return rec.ClassOrStructKeyword.IsKind(SyntaxKind.StructKeyword)
                    ? "record struct"
                    : "record";
            }
            if (typeNode is StructDeclarationSyntax)
                return "struct";
            return "class";
        }

        private static string ResolveNamespaceName(SyntaxNode node)
        {
            var nsNodes = node.Ancestors()
                .OfType<BaseNamespaceDeclarationSyntax>()
                .Reverse()
                .Select(ns => ns.Name.ToString())
                .Where(n => !string.IsNullOrWhiteSpace(n));
            return string.Join(".", nsNodes);
        }

        private static MethodLocation BuildMethodLocation(
            MethodDeclarationSyntax method,
            Microsoft.CodeAnalysis.Text.SourceText text,
            int lineOffset,
            bool wrapped,
            bool includeMetrics)
        {
            var span = method.Span;
            var lineSpan = text.Lines.GetLinePositionSpan(span);
            int startLine = Math.Max(1, lineSpan.Start.Line + 1 - lineOffset);
            int endLine = Math.Max(1, lineSpan.End.Line + 1 - lineOffset);

            var parentType = method.Ancestors().OfType<TypeDeclarationSyntax>().FirstOrDefault();
            string className = (wrapped || parentType == null) ? "Global" : parentType.Identifier.Text;

            var paramList = string.Join(", ", method.ParameterList.Parameters.Select(p => $"{p.Type} {p.Identifier.Text}".Trim()));
            string signature = $"{method.ReturnType} {method.Identifier.Text}({paramList})";

            bool isStatic = method.Modifiers.Any(SyntaxKind.StaticKeyword);
            bool isAsync = method.Modifiers.Any(SyntaxKind.AsyncKeyword);
            bool isGeneric = method.TypeParameterList != null && method.TypeParameterList.Parameters.Count > 0;

            MethodMetrics? metrics = includeMetrics ? CalculateMetrics(method, isStatic, isAsync, isGeneric) : null;

            return new MethodLocation
            {
                ClassName = className,
                MethodName = method.Identifier.Text,
                MethodSignature = signature,
                StartLine = startLine,
                EndLine = endLine,
                IsStatic = isStatic,
                IsAsync = isAsync,
                IsGeneric = isGeneric,
                SourceCode = method.ToFullString().Trim(),
                Metrics = metrics
            };
        }

        /// <summary>
        /// Yields descendants of a TypeDeclarationSyntax without descending into nested type declarations.
        /// </summary>
        private static IEnumerable<T> GetTypeOwnedNodes<T>(TypeDeclarationSyntax owner) where T : SyntaxNode
        {
            return owner.DescendantNodes(descendant =>
                descendant == owner || !(descendant is TypeDeclarationSyntax)
            ).OfType<T>();
        }

        /// <summary>
        /// Filters descendant nodes so that nodes belonging to nested local functions, lambdas, or nested types are excluded.
        /// </summary>
        private static IEnumerable<T> GetMethodOwnedDescendants<T>(SyntaxNode memberRoot) where T : SyntaxNode
        {
            return memberRoot.DescendantNodes(descendant =>
                descendant == memberRoot || (
                    !(descendant is TypeDeclarationSyntax) &&
                    !(descendant is LocalFunctionStatementSyntax) &&
                    !(descendant is SimpleLambdaExpressionSyntax) &&
                    !(descendant is ParenthesizedLambdaExpressionSyntax) &&
                    !(descendant is AnonymousMethodExpressionSyntax)
                )
            ).OfType<T>();
        }

        /// <summary>
        /// Computes isolated class-level static metrics without double-counting nested types.
        /// </summary>
        public static ClassMetrics CalculateClassMetrics(
            TypeDeclarationSyntax typeNode,
            Microsoft.CodeAnalysis.Text.SourceText text,
            List<MethodLocation> ownedMethods)
        {
            var typeLineSpan = text.Lines.GetLinePositionSpan(typeNode.Span);
            int typeStart = typeLineSpan.Start.Line;
            int typeEnd = typeLineSpan.End.Line;

            // Collect line indices occupied exclusively by direct nested type declarations
            var directNestedTypes = GetTypeOwnedNodes<TypeDeclarationSyntax>(typeNode)
                .Where(t => t != typeNode)
                .ToList();

            var nestedLines = new HashSet<int>();
            foreach (var nt in directNestedTypes)
            {
                var nSpan = text.Lines.GetLinePositionSpan(nt.Span);
                for (int ln = nSpan.Start.Line; ln <= nSpan.End.Line; ln++)
                {
                    nestedLines.Add(ln);
                }
            }

            int classLoc = 0;
            for (int ln = typeStart; ln <= typeEnd; ln++)
            {
                if (nestedLines.Contains(ln))
                    continue;
                if (!string.IsNullOrWhiteSpace(text.Lines[ln].ToString()))
                    classLoc++;
            }
            if (classLoc == 0)
                classLoc = 1;

            // Direct members
            var directMethods = GetTypeOwnedNodes<MethodDeclarationSyntax>(typeNode).ToList();
            var directConstructors = GetTypeOwnedNodes<ConstructorDeclarationSyntax>(typeNode).ToList();
            var directProperties = GetTypeOwnedNodes<PropertyDeclarationSyntax>(typeNode).ToList();
            var directFields = GetTypeOwnedNodes<FieldDeclarationSyntax>(typeNode).ToList();
            var directOperators = GetTypeOwnedNodes<OperatorDeclarationSyntax>(typeNode).ToList();
            var directConvOperators = GetTypeOwnedNodes<ConversionOperatorDeclarationSyntax>(typeNode).ToList();
            var directIndexers = GetTypeOwnedNodes<IndexerDeclarationSyntax>(typeNode).ToList();

            int methodCount = directMethods.Count;
            bool hasPrimaryCtor = typeNode.ParameterList != null && typeNode.ParameterList.Parameters.Count > 0;
            int constructorCount = directConstructors.Count + (hasPrimaryCtor ? 1 : 0);
            int propertyCount = directProperties.Count;
            int fieldCount = directFields.Sum(f => f.Declaration.Variables.Count);
            int nestedTypeCount = directNestedTypes.Count;

            // Aggregate metrics across all direct callable members (methods, constructors, operators, property/indexer accessors)
            var callableMetrics = new List<(MethodMetrics Metrics, int ParamCount)>();

            foreach (var m in directMethods)
            {
                bool mStatic = m.Modifiers.Any(SyntaxKind.StaticKeyword);
                bool mAsync = m.Modifiers.Any(SyntaxKind.AsyncKeyword);
                bool mGeneric = m.TypeParameterList != null && m.TypeParameterList.Parameters.Count > 0;
                var mm = CalculateMetrics(m, mStatic, mAsync, mGeneric);
                callableMetrics.Add((mm, m.ParameterList.Parameters.Count));
            }

            foreach (var c in directConstructors)
            {
                bool cStatic = c.Modifiers.Any(SyntaxKind.StaticKeyword);
                var cm = CalculateCallableBodyMetrics(c, c.Body, c.ExpressionBody, c.ParameterList.Parameters.Count, cStatic, false, false);
                callableMetrics.Add((cm, c.ParameterList.Parameters.Count));
            }

            foreach (var op in directOperators)
            {
                var om = CalculateCallableBodyMetrics(op, op.Body, op.ExpressionBody, op.ParameterList.Parameters.Count, true, false, false);
                callableMetrics.Add((om, op.ParameterList.Parameters.Count));
            }

            foreach (var cop in directConvOperators)
            {
                var com = CalculateCallableBodyMetrics(cop, cop.Body, cop.ExpressionBody, cop.ParameterList.Parameters.Count, true, false, false);
                callableMetrics.Add((com, cop.ParameterList.Parameters.Count));
            }

            foreach (var prop in directProperties)
            {
                if (prop.ExpressionBody != null)
                {
                    var pm = CalculateCallableBodyMetrics(prop, null, prop.ExpressionBody, 0, prop.Modifiers.Any(SyntaxKind.StaticKeyword), false, false);
                    callableMetrics.Add((pm, 0));
                }
                else if (prop.AccessorList != null)
                {
                    foreach (var acc in prop.AccessorList.Accessors)
                    {
                        if (acc.Body != null || acc.ExpressionBody != null)
                        {
                            var am = CalculateCallableBodyMetrics(acc, acc.Body, acc.ExpressionBody, 0, prop.Modifiers.Any(SyntaxKind.StaticKeyword), false, false);
                            callableMetrics.Add((am, 0));
                        }
                    }
                }
            }

            foreach (var idxer in directIndexers)
            {
                if (idxer.ExpressionBody != null)
                {
                    var im = CalculateCallableBodyMetrics(idxer, null, idxer.ExpressionBody, idxer.ParameterList.Parameters.Count, false, false, false);
                    callableMetrics.Add((im, idxer.ParameterList.Parameters.Count));
                }
                else if (idxer.AccessorList != null)
                {
                    foreach (var acc in idxer.AccessorList.Accessors)
                    {
                        if (acc.Body != null || acc.ExpressionBody != null)
                        {
                            var am = CalculateCallableBodyMetrics(acc, acc.Body, acc.ExpressionBody, idxer.ParameterList.Parameters.Count, false, false, false);
                            callableMetrics.Add((am, idxer.ParameterList.Parameters.Count));
                        }
                    }
                }
            }

            int primaryCtorParams = typeNode.ParameterList?.Parameters.Count ?? 0;
            int totalParamCount = callableMetrics.Sum(x => x.ParamCount) + primaryCtorParams;
            int maxParamCount = callableMetrics.Count > 0
                ? Math.Max(primaryCtorParams, callableMetrics.Max(x => x.ParamCount))
                : primaryCtorParams;

            int classLogicalLoc = callableMetrics.Sum(x => x.Metrics.LogicalLoc);
            int totalLocalVars = callableMetrics.Sum(x => x.Metrics.LocalVariableCount);
            int totalStatements = callableMetrics.Sum(x => x.Metrics.StatementCount);
            int totalReturns = callableMetrics.Sum(x => x.Metrics.ReturnCount);

            var complexities = callableMetrics.Select(x => x.Metrics.CyclomaticComplexity).ToList();
            int totalCc = complexities.Count > 0 ? complexities.Sum() : 1;
            int maxMethodCc = complexities.Count > 0 ? complexities.Max() : 1;
            double meanMethodCc = complexities.Count > 0 ? complexities.Average() : 1.0;
            double stdMethodCc = 0.0;
            if (complexities.Count > 1)
            {
                double variance = complexities.Select(c => Math.Pow(c - meanMethodCc, 2)).Average();
                stdMethodCc = Math.Sqrt(variance);
            }

            var depths = callableMetrics.Select(x => x.Metrics.MaxNestingDepth).ToList();
            int maxNesting = depths.Count > 0 ? depths.Max() : 0;
            double meanNesting = depths.Count > 0 ? depths.Average() : 0.0;

            int totalBoolOps = callableMetrics.Sum(x => x.Metrics.BooleanOperatorCount);
            int totalLogOps = callableMetrics.Sum(x => x.Metrics.LogicalOperatorCount);
            int totalCondExprs = callableMetrics.Sum(x => x.Metrics.ConditionalExpressionCount);
            int totalIfs = callableMetrics.Sum(x => x.Metrics.IfCount);
            int totalSwitches = callableMetrics.Sum(x => x.Metrics.SwitchCount);
            int totalLoops = callableMetrics.Sum(x => x.Metrics.LoopCount);
            int totalTryCatch = callableMetrics.Sum(x => x.Metrics.TryCatchCount);
            int totalThrows = callableMetrics.Sum(x => x.Metrics.ThrowCount);
            int totalBreakContinue = callableMetrics.Sum(x => x.Metrics.BreakContinueCount);

            int totalMethodCalls = callableMetrics.Sum(x => x.Metrics.MethodCallCount);
            int totalFieldAccesses = callableMetrics.Sum(x => x.Metrics.FieldAccessCount);
            int totalPropAccesses = callableMetrics.Sum(x => x.Metrics.PropertyAccessCount);
            int totalAssignments = callableMetrics.Sum(x => x.Metrics.AssignmentCount);
            int totalObjectCreations = callableMetrics.Sum(x => x.Metrics.ObjectCreationCount)
                + GetTypeOwnedNodes<BaseFieldDeclarationSyntax>(typeNode)
                    .SelectMany(f => GetMethodOwnedDescendants<ObjectCreationExpressionSyntax>(f))
                    .Count()
                + GetTypeOwnedNodes<BaseFieldDeclarationSyntax>(typeNode)
                    .SelectMany(f => GetMethodOwnedDescendants<ImplicitObjectCreationExpressionSyntax>(f))
                    .Count();

            int staticMethodCount = directMethods.Count(m => m.Modifiers.Any(SyntaxKind.StaticKeyword));
            int asyncMethodCount = directMethods.Count(m => m.Modifiers.Any(SyntaxKind.AsyncKeyword));
            int genericMethodCount = directMethods.Count(m => m.TypeParameterList != null && m.TypeParameterList.Parameters.Count > 0);
            int highComplexityMethodCount = callableMetrics.Count(x => x.Metrics.CyclomaticComplexity >= 10);
            int largeMethodCount = callableMetrics.Count(x => x.Metrics.Loc >= 40 || x.Metrics.StatementCount >= 25);

            double complexityConcentration = Math.Round((double)maxMethodCc / Math.Max(1.0, totalCc), 4);
            double structuralDensity = Math.Round((double)totalStatements / Math.Max(1.0, classLoc), 4);
            double wmcDensity = Math.Round((double)totalCc / Math.Max(1.0, classLoc), 4);

            return new ClassMetrics
            {
                ClassLoc = classLoc,
                ClassLogicalLoc = classLogicalLoc,
                MethodCount = methodCount,
                ConstructorCount = constructorCount,
                PropertyCount = propertyCount,
                FieldCount = fieldCount,
                NestedTypeCount = nestedTypeCount,
                TotalParameterCount = totalParamCount,
                MaxParameterCount = maxParamCount,
                TotalLocalVariableCount = totalLocalVars,
                TotalStatementCount = totalStatements,
                TotalReturnCount = totalReturns,
                TotalCyclomaticComplexity = totalCc,
                MeanMethodComplexity = Math.Round(meanMethodCc, 4),
                MaxMethodComplexity = maxMethodCc,
                StdMethodComplexity = Math.Round(stdMethodCc, 4),
                MaxNestingDepth = maxNesting,
                MeanNestingDepth = Math.Round(meanNesting, 4),
                TotalBooleanOperatorCount = totalBoolOps,
                TotalLogicalOperatorCount = totalLogOps,
                TotalConditionalExpressionCount = totalCondExprs,
                TotalIfCount = totalIfs,
                TotalSwitchCount = totalSwitches,
                TotalLoopCount = totalLoops,
                TotalTryCatchCount = totalTryCatch,
                TotalThrowCount = totalThrows,
                TotalBreakContinueCount = totalBreakContinue,
                TotalMethodCallCount = totalMethodCalls,
                TotalFieldAccessCount = totalFieldAccesses,
                TotalPropertyAccessCount = totalPropAccesses,
                TotalAssignmentCount = totalAssignments,
                TotalObjectCreationCount = totalObjectCreations,
                StaticMethodCount = staticMethodCount,
                AsyncMethodCount = asyncMethodCount,
                GenericMethodCount = genericMethodCount,
                HighComplexityMethodCount = highComplexityMethodCount,
                LargeMethodCount = largeMethodCount,
                ComplexityConcentration = complexityConcentration,
                StructuralDensity = structuralDensity,
                WmcDensity = wmcDensity
            };
        }

        /// <summary>
        /// Computes the 26 static code metrics for the specified method syntax node.
        /// </summary>
        public static MethodMetrics CalculateMetrics(MethodDeclarationSyntax method, bool isStatic, bool isAsync, bool isGeneric)
        {
            return CalculateCallableBodyMetrics(
                method,
                method.Body,
                method.ExpressionBody,
                method.ParameterList.Parameters.Count,
                isStatic,
                isAsync,
                isGeneric
            );
        }

        private static MethodMetrics CalculateCallableBodyMetrics(
            SyntaxNode memberNode,
            BlockSyntax? body,
            ArrowExpressionClauseSyntax? expressionBody,
            int parameterCount,
            bool isStatic,
            bool isAsync,
            bool isGeneric)
        {
            var rawText = memberNode.ToFullString();
            var physicalLines = rawText.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
            int loc = physicalLines.Length;
            int methodLength = rawText.Length;

            // Owned statements (excluding the outer body block itself)
            var ownedStatements = GetMethodOwnedDescendants<StatementSyntax>(memberNode)
                .Where(s => s != body && !(s is BlockSyntax b && b.Parent == memberNode))
                .ToList();
            int statementCount = ownedStatements.Count;

            var ownedVars = GetMethodOwnedDescendants<VariableDeclaratorSyntax>(memberNode).ToList();
            int localVariableCount = ownedVars.Count;

            int returnCount = expressionBody != null
                ? 1
                : GetMethodOwnedDescendants<ReturnStatementSyntax>(memberNode).Count();

            int logicalLoc = statementCount + (expressionBody != null ? 1 : 0);

            // Control flow
            int ifCount = GetMethodOwnedDescendants<IfStatementSyntax>(memberNode).Count();
            int switchCount = GetMethodOwnedDescendants<SwitchStatementSyntax>(memberNode).Count()
                            + GetMethodOwnedDescendants<SwitchExpressionSyntax>(memberNode).Count();

            int forCount = GetMethodOwnedDescendants<ForStatementSyntax>(memberNode).Count();
            int forEachCount = GetMethodOwnedDescendants<ForEachStatementSyntax>(memberNode).Count();
            int whileCount = GetMethodOwnedDescendants<WhileStatementSyntax>(memberNode).Count();
            int doWhileCount = GetMethodOwnedDescendants<DoStatementSyntax>(memberNode).Count();
            int loopCount = forCount + forEachCount + whileCount + doWhileCount;

            int tryCatchCount = GetMethodOwnedDescendants<TryStatementSyntax>(memberNode).Count();
            int throwCount = GetMethodOwnedDescendants<ThrowStatementSyntax>(memberNode).Count()
                           + GetMethodOwnedDescendants<ThrowExpressionSyntax>(memberNode).Count();

            int breakContinueCount = GetMethodOwnedDescendants<BreakStatementSyntax>(memberNode).Count()
                                   + GetMethodOwnedDescendants<ContinueStatementSyntax>(memberNode).Count();

            // Conditionals & Operators
            int conditionalExpressionCount = GetMethodOwnedDescendants<ConditionalExpressionSyntax>(memberNode).Count();

            var binaryExpressions = GetMethodOwnedDescendants<BinaryExpressionSyntax>(memberNode).ToList();
            int logicalAndOr = binaryExpressions.Count(b =>
                b.IsKind(SyntaxKind.LogicalAndExpression) ||
                b.IsKind(SyntaxKind.LogicalOrExpression) ||
                b.IsKind(SyntaxKind.CoalesceExpression));

            int booleanOps = binaryExpressions.Count(b =>
                b.IsKind(SyntaxKind.BitwiseAndExpression) ||
                b.IsKind(SyntaxKind.BitwiseOrExpression) ||
                b.IsKind(SyntaxKind.ExclusiveOrExpression))
                + GetMethodOwnedDescendants<PrefixUnaryExpressionSyntax>(memberNode).Count(u => u.IsKind(SyntaxKind.LogicalNotExpression));

            int switchCases = GetMethodOwnedDescendants<CaseSwitchLabelSyntax>(memberNode).Count()
                            + GetMethodOwnedDescendants<SwitchExpressionArmSyntax>(memberNode).Count();
            int catchCount = GetMethodOwnedDescendants<CatchClauseSyntax>(memberNode).Count();

            int cyclomaticComplexity = 1 + ifCount + conditionalExpressionCount + loopCount + switchCases + catchCount + logicalAndOr;

            int maxNestingDepth = CalculateMaxNestingDepth(body);

            // Structure metrics
            int methodCallCount = GetMethodOwnedDescendants<InvocationExpressionSyntax>(memberNode).Count();
            int assignmentCount = GetMethodOwnedDescendants<AssignmentExpressionSyntax>(memberNode).Count();
            int objectCreationCount = GetMethodOwnedDescendants<ObjectCreationExpressionSyntax>(memberNode).Count()
                                    + GetMethodOwnedDescendants<ImplicitObjectCreationExpressionSyntax>(memberNode).Count();

            var memberAccesses = GetMethodOwnedDescendants<MemberAccessExpressionSyntax>(memberNode).ToList();
            int propertyAccessCount = 0;
            int fieldAccessCount = 0;

            foreach (var ma in memberAccesses)
            {
                string memberName = ma.Name.Identifier.Text;
                if (!string.IsNullOrEmpty(memberName))
                {
                    if (char.IsUpper(memberName[0]))
                        propertyAccessCount++;
                    else
                        fieldAccessCount++;
                }
            }

            return new MethodMetrics
            {
                Loc = loc,
                LogicalLoc = logicalLoc,
                MethodLength = methodLength,
                ParameterCount = parameterCount,
                LocalVariableCount = localVariableCount,
                StatementCount = statementCount,
                ReturnCount = returnCount,
                CyclomaticComplexity = cyclomaticComplexity,
                MaxNestingDepth = maxNestingDepth,
                BooleanOperatorCount = booleanOps,
                LogicalOperatorCount = logicalAndOr,
                ConditionalExpressionCount = conditionalExpressionCount,
                IfCount = ifCount,
                SwitchCount = switchCount,
                LoopCount = loopCount,
                TryCatchCount = tryCatchCount,
                ThrowCount = throwCount,
                BreakContinueCount = breakContinueCount,
                MethodCallCount = methodCallCount,
                FieldAccessCount = fieldAccessCount,
                PropertyAccessCount = propertyAccessCount,
                AssignmentCount = assignmentCount,
                ObjectCreationCount = objectCreationCount,
                IsStatic = isStatic,
                IsAsync = isAsync,
                IsGeneric = isGeneric
            };
        }

        /// <summary>
        /// Computes the maximum control-flow nesting depth within the body block, excluding nested functions, lambdas, and nested types.
        /// </summary>
        private static int CalculateMaxNestingDepth(BlockSyntax? body)
        {
            if (body == null)
                return 0;

            int maxDepth = 0;

            void Traverse(SyntaxNode node, int currentDepth)
            {
                bool isControlBlock = node is IfStatementSyntax ||
                                      node is WhileStatementSyntax ||
                                      node is ForStatementSyntax ||
                                      node is ForEachStatementSyntax ||
                                      node is DoStatementSyntax ||
                                      node is SwitchStatementSyntax ||
                                      node is TryStatementSyntax ||
                                      node is UsingStatementSyntax ||
                                      node is LockStatementSyntax;

                int nextDepth = isControlBlock ? currentDepth + 1 : currentDepth;
                if (nextDepth > maxDepth)
                    maxDepth = nextDepth;

                foreach (var child in node.ChildNodes())
                {
                    if (child is TypeDeclarationSyntax ||
                        child is LocalFunctionStatementSyntax ||
                        child is SimpleLambdaExpressionSyntax ||
                        child is ParenthesizedLambdaExpressionSyntax ||
                        child is AnonymousMethodExpressionSyntax)
                    {
                        continue;
                    }
                    Traverse(child, nextDepth);
                }
            }

            Traverse(body, 0);
            return maxDepth;
        }
    }
}
