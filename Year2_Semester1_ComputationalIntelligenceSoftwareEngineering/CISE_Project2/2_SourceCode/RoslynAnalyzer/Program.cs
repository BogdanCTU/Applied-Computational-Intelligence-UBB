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
    public class MethodMetrics
    {
        // Basic metrics
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

        // Complexity metrics
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

        // Control-flow metrics
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

        // Code structure metrics
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

        // Additional OOP / signature properties
        [JsonPropertyName("is_static")]
        public bool IsStatic { get; set; }

        [JsonPropertyName("is_async")]
        public bool IsAsync { get; set; }

        [JsonPropertyName("is_generic")]
        public bool IsGeneric { get; set; }
    }

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

    public class MethodLocatorResponse
    {
        [JsonPropertyName("analyzer_version")]
        public string AnalyzerVersion { get; set; } = "1.0.0";

        [JsonPropertyName("success")]
        public bool Success { get; set; } = true;

        [JsonPropertyName("methods")]
        public List<MethodLocation> Methods { get; set; } = new();

        [JsonPropertyName("error")]
        public string? Error { get; set; }
    }

    class Program
    {
        static int Main(string[] args)
        {
            try
            {
                string? filePath = null;
                string? code = null;
                int? targetLine = null;
                bool includeMetrics = true;

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

                if (string.IsNullOrWhiteSpace(code))
                {
                    var emptyResp = new MethodLocatorResponse { Success = true, Methods = new List<MethodLocation>() };
                    Console.WriteLine(JsonSerializer.Serialize(emptyResp));
                    return 0;
                }

                // Normalize all newlines to single \n to guarantee consistent 1-based line positions across OSes
                code = code.Replace("\r\n", "\n").Replace("\r", "\n");

                // If input code is an isolated method without class wrapping, wrap it in a dummy class for valid parsing
                string parseCode = code;
                bool wrapped = false;
                if (!code.Contains("class ") && !code.Contains("struct ") && !code.Contains("interface ") && !code.Contains("record "))
                {
                    parseCode = "class __DummyContainer__ {\n" + code + "\n}";
                    wrapped = true;
                }

                var tree = CSharpSyntaxTree.ParseText(parseCode);
                var root = tree.GetRoot();
                var text = tree.GetText();

                var methodDeclarations = root.DescendantNodes().OfType<MethodDeclarationSyntax>();
                var results = new List<MethodLocation>();

                foreach (var method in methodDeclarations)
                {
                    var span = method.Span;
                    var lineSpan = text.Lines.GetLinePositionSpan(span);
                    // Adjust 1-based start/end line if code was wrapped
                    int lineOffset = wrapped ? 1 : 0;
                    int startLine = Math.Max(1, lineSpan.Start.Line + 1 - lineOffset);
                    int endLine = Math.Max(1, lineSpan.End.Line + 1 - lineOffset);

                    if (targetLine.HasValue && (targetLine.Value < startLine || targetLine.Value > endLine))
                        continue;

                    var parentType = method.Ancestors().OfType<TypeDeclarationSyntax>().FirstOrDefault();
                    string className = (wrapped || parentType == null) ? "Global" : parentType.Identifier.Text;

                    var paramList = string.Join(", ", method.ParameterList.Parameters.Select(p => $"{p.Type} {p.Identifier.Text}".Trim()));
                    string signature = $"{method.ReturnType} {method.Identifier.Text}({paramList})";

                    bool isStatic = method.Modifiers.Any(SyntaxKind.StaticKeyword);
                    bool isAsync = method.Modifiers.Any(SyntaxKind.AsyncKeyword);
                    bool isGeneric = method.TypeParameterList != null && method.TypeParameterList.Parameters.Count > 0;

                    MethodMetrics? metrics = null;
                    if (includeMetrics)
                    {
                        metrics = CalculateMetrics(method, isStatic, isAsync, isGeneric);
                    }

                    results.Add(new MethodLocation
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
                    });
                }

                var response = new MethodLocatorResponse
                {
                    AnalyzerVersion = "1.0.0",
                    Success = true,
                    Methods = results
                };

                Console.WriteLine(JsonSerializer.Serialize(response, new JsonSerializerOptions { WriteIndented = false }));
                return 0;
            }
            catch (Exception ex)
            {
                var errResp = new MethodLocatorResponse
                {
                    Success = false,
                    Error = ex.Message
                };
                Console.WriteLine(JsonSerializer.Serialize(errResp));
                return 1;
            }
        }

        /// <summary>
        /// Filters descendant nodes so that nodes belonging to nested local functions or lambdas are excluded.
        /// </summary>
        private static IEnumerable<T> GetMethodOwnedDescendants<T>(MethodDeclarationSyntax method) where T : SyntaxNode
        {
            return method.DescendantNodes(descendant =>
                // Do not descend into nested local functions or lambdas
                descendant == method || (
                    !(descendant is LocalFunctionStatementSyntax) &&
                    !(descendant is SimpleLambdaExpressionSyntax) &&
                    !(descendant is ParenthesizedLambdaExpressionSyntax) &&
                    !(descendant is AnonymousMethodExpressionSyntax)
                )
            ).OfType<T>();
        }

        public static MethodMetrics CalculateMetrics(MethodDeclarationSyntax method, bool isStatic, bool isAsync, bool isGeneric)
        {
            var rawText = method.ToFullString();
            var physicalLines = rawText.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
            int loc = physicalLines.Length;
            int methodLength = rawText.Length;

            int parameterCount = method.ParameterList.Parameters.Count;

            // Method-owned statements and variables (excluding the outer method.Body block itself)
            var ownedStatements = GetMethodOwnedDescendants<StatementSyntax>(method)
                .Where(s => s != method.Body && !(s is BlockSyntax b && b.Parent == method))
                .ToList();
            int statementCount = ownedStatements.Count;

            var ownedVars = GetMethodOwnedDescendants<VariableDeclaratorSyntax>(method).ToList();
            int localVariableCount = ownedVars.Count;

            int returnCount = 0;
            if (method.ExpressionBody != null)
            {
                returnCount = 1;
            }
            else
            {
                returnCount = GetMethodOwnedDescendants<ReturnStatementSyntax>(method).Count();
            }

            int logicalLoc = statementCount + (method.ExpressionBody != null ? 1 : 0);

            // Control flow
            var ifStatements = GetMethodOwnedDescendants<IfStatementSyntax>(method).ToList();
            int ifCount = ifStatements.Count;

            int switchCount = GetMethodOwnedDescendants<SwitchStatementSyntax>(method).Count()
                            + GetMethodOwnedDescendants<SwitchExpressionSyntax>(method).Count();

            int forCount = GetMethodOwnedDescendants<ForStatementSyntax>(method).Count();
            int forEachCount = GetMethodOwnedDescendants<ForEachStatementSyntax>(method).Count();
            int whileCount = GetMethodOwnedDescendants<WhileStatementSyntax>(method).Count();
            int doWhileCount = GetMethodOwnedDescendants<DoStatementSyntax>(method).Count();
            int loopCount = forCount + forEachCount + whileCount + doWhileCount;

            int tryCatchCount = GetMethodOwnedDescendants<TryStatementSyntax>(method).Count();
            int throwCount = GetMethodOwnedDescendants<ThrowStatementSyntax>(method).Count()
                           + GetMethodOwnedDescendants<ThrowExpressionSyntax>(method).Count();

            int breakContinueCount = GetMethodOwnedDescendants<BreakStatementSyntax>(method).Count()
                                   + GetMethodOwnedDescendants<ContinueStatementSyntax>(method).Count();

            // Conditionals & Operators
            var condExpressions = GetMethodOwnedDescendants<ConditionalExpressionSyntax>(method).ToList();
            int conditionalExpressionCount = condExpressions.Count;

            var binaryExpressions = GetMethodOwnedDescendants<BinaryExpressionSyntax>(method).ToList();
            int logicalAndOr = binaryExpressions.Count(b =>
                b.IsKind(SyntaxKind.LogicalAndExpression) ||
                b.IsKind(SyntaxKind.LogicalOrExpression) ||
                b.IsKind(SyntaxKind.CoalesceExpression));

            int booleanOps = binaryExpressions.Count(b =>
                b.IsKind(SyntaxKind.BitwiseAndExpression) ||
                b.IsKind(SyntaxKind.BitwiseOrExpression) ||
                b.IsKind(SyntaxKind.ExclusiveOrExpression))
                + GetMethodOwnedDescendants<PrefixUnaryExpressionSyntax>(method).Count(u => u.IsKind(SyntaxKind.LogicalNotExpression));

            // Cyclomatic Complexity (McCabe):
            // Base = 1
            // +1 for each if
            // +1 for each ternary (? :)
            // +1 for each loop (for, foreach, while, do)
            // +1 for each switch section (case) with label
            // +1 for each catch clause
            // +1 for each logical &&, ||, ??
            int switchCases = GetMethodOwnedDescendants<CaseSwitchLabelSyntax>(method).Count()
                            + GetMethodOwnedDescendants<SwitchExpressionArmSyntax>(method).Count();
            int catchCount = GetMethodOwnedDescendants<CatchClauseSyntax>(method).Count();

            int cyclomaticComplexity = 1 + ifCount + conditionalExpressionCount + loopCount + switchCases + catchCount + logicalAndOr;

            // Maximum Nesting Depth
            int maxNestingDepth = CalculateMaxNestingDepth(method);

            // Structure metrics
            int methodCallCount = GetMethodOwnedDescendants<InvocationExpressionSyntax>(method).Count();
            int assignmentCount = GetMethodOwnedDescendants<AssignmentExpressionSyntax>(method).Count();
            int objectCreationCount = GetMethodOwnedDescendants<ObjectCreationExpressionSyntax>(method).Count();

            // Field and Property accesses via MemberAccessExpression
            var memberAccesses = GetMethodOwnedDescendants<MemberAccessExpressionSyntax>(method).ToList();
            int propertyAccessCount = 0;
            int fieldAccessCount = 0;

            foreach (var ma in memberAccesses)
            {
                // Heuristic: uppercase identifier is conventional for Property in C#, lowercase or _ for field
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

        private static int CalculateMaxNestingDepth(MethodDeclarationSyntax method)
        {
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
                    // Do not descend into local functions or lambdas
                    if (child is LocalFunctionStatementSyntax ||
                        child is SimpleLambdaExpressionSyntax ||
                        child is ParenthesizedLambdaExpressionSyntax ||
                        child is AnonymousMethodExpressionSyntax)
                    {
                        continue;
                    }
                    Traverse(child, nextDepth);
                }
            }

            if (method.Body != null)
            {
                Traverse(method.Body, 0);
            }
            return maxDepth;
        }
    }
}
