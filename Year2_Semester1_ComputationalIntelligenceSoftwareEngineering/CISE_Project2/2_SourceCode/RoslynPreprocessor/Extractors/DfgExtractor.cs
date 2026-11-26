using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

namespace RoslynPreprocessor.Extractors;

public static class DfgExtractor
{
    private static readonly HashSet<string> NullableReturnMethods = new(StringComparer.Ordinal)
    {
        "FirstOrDefault", "SingleOrDefault", "LastOrDefault", "ElementAtOrDefault",
        "GetValueOrDefault", "ReadLine", "GetAttribute", "SelectSingleNode"
    };

    private static readonly HashSet<string> DisposableTypes = new(StringComparer.Ordinal)
    {
        "FileStream", "StreamReader", "StreamWriter", "BinaryReader", "BinaryWriter",
        "MemoryStream", "NetworkStream", "SqlConnection", "SqlCommand", "SqlDataReader",
        "DbConnection", "DbCommand", "DbDataReader", "HttpClient", "HttpResponseMessage",
        "HttpRequestMessage", "CancellationTokenSource", "SemaphoreSlim", "Mutex",
        "Timer", "GZipStream", "DeflateStream", "CryptoStream", "ZipArchive", "DataSet", "DataTable"
    };

    public static Dictionary<string, double> Extract(
        BaseMethodDeclarationSyntax methodNode,
        SemanticModel? semanticModel)
    {
        var bodyOrExpr = (SyntaxNode?)methodNode.Body ?? methodNode.ExpressionBody;

        var parameterNames = methodNode.ParameterList.Parameters
            .Select(p => p.Identifier.Text)
            .Where(n => !string.IsNullOrEmpty(n))
            .ToHashSet(StringComparer.Ordinal);

        var localDecls = new Dictionary<string, int>(StringComparer.Ordinal);
        var varReads = new Dictionary<string, int>(StringComparer.Ordinal);
        var varWrites = new Dictionary<string, int>(StringComparer.Ordinal);
        var nullCheckedVars = new HashSet<string>(StringComparer.Ordinal);
        var dereferencedVars = new HashSet<string>(StringComparer.Ordinal);
        var nullableAssignedVars = new HashSet<string>(StringComparer.Ordinal);
        var conditionalAssignedVars = new HashSet<string>(StringComparer.Ordinal);

        int disposableAllocations = 0;
        int usingWrappedAllocations = 0;
        int explicitDisposeCalls = 0;
        int fieldWriteCount = 0;
        int fieldReadCount = 0;
        int uncheckedNullableCallDeref = 0;
        int totalIdentifierRefs = 0;
        int unresolvedIdentifierRefs = 0;

        if (bodyOrExpr != null)
        {
            // Local variable declarations & nullable/disposable initialization tracking
            foreach (var vdec in bodyOrExpr.DescendantNodes().OfType<VariableDeclaratorSyntax>())
            {
                string varName = vdec.Identifier.Text;
                if (string.IsNullOrEmpty(varName)) continue;
                localDecls[varName] = localDecls.GetValueOrDefault(varName) + 1;
                if (vdec.Initializer != null)
                {
                    varWrites[varName] = varWrites.GetValueOrDefault(varName) + 1;
                    if (IsInsideUsing(vdec))
                    {
                        usingWrappedAllocations++;
                    }
                    if (LooksNullableExpr(vdec.Initializer.Value))
                    {
                        nullableAssignedVars.Add(varName);
                    }
                }
            }

            // Using statements / using declarations
            foreach (var objCreate in bodyOrExpr.DescendantNodes().OfType<ObjectCreationExpressionSyntax>())
            {
                string typeShort = ShortType(objCreate.Type.ToString());
                if (DisposableTypes.Contains(typeShort) || typeShort.EndsWith("Stream", StringComparison.Ordinal) || typeShort.EndsWith("Reader", StringComparison.Ordinal) || typeShort.EndsWith("Writer", StringComparison.Ordinal))
                {
                    disposableAllocations++;
                    if (IsInsideUsing(objCreate))
                    {
                        usingWrappedAllocations++;
                    }
                }
            }

            foreach (var inv in bodyOrExpr.DescendantNodes().OfType<InvocationExpressionSyntax>())
            {
                if (inv.Expression is MemberAccessExpressionSyntax ma)
                {
                    string memberName = ma.Name.Identifier.Text;
                    if (memberName is "Dispose" or "DisposeAsync" or "Close")
                    {
                        explicitDisposeCalls++;
                    }
                    if (ma.Expression is InvocationExpressionSyntax innerInv &&
                        innerInv.Expression is MemberAccessExpressionSyntax innerMa &&
                        NullableReturnMethods.Contains(innerMa.Name.Identifier.Text))
                    {
                        uncheckedNullableCallDeref++;
                    }
                }
            }

            // Assignments
            foreach (var assign in bodyOrExpr.DescendantNodes().OfType<AssignmentExpressionSyntax>())
            {
                if (assign.Left is IdentifierNameSyntax id)
                {
                    string name = id.Identifier.Text;
                    varWrites[name] = varWrites.GetValueOrDefault(name) + 1;
                    if (LooksNullableExpr(assign.Right))
                    {
                        nullableAssignedVars.Add(name);
                    }
                    if (IsInsideBranch(assign))
                    {
                        conditionalAssignedVars.Add(name);
                    }
                }
                else if (assign.Left is MemberAccessExpressionSyntax ma && ma.Expression is ThisExpressionSyntax)
                {
                    fieldWriteCount++;
                }
            }

            // Null checks (x == null, x != null, x is null, x is not null, ArgumentNullException.ThrowIfNull(x), string.IsNullOrEmpty(x))
            foreach (var bin in bodyOrExpr.DescendantNodes().OfType<BinaryExpressionSyntax>())
            {
                if (bin.IsKind(SyntaxKind.EqualsExpression) || bin.IsKind(SyntaxKind.NotEqualsExpression))
                {
                    if (bin.Right.IsKind(SyntaxKind.NullLiteralExpression) && bin.Left is IdentifierNameSyntax lId)
                        nullCheckedVars.Add(lId.Identifier.Text);
                    if (bin.Left.IsKind(SyntaxKind.NullLiteralExpression) && bin.Right is IdentifierNameSyntax rId)
                        nullCheckedVars.Add(rId.Identifier.Text);
                }
            }
            foreach (var isPat in bodyOrExpr.DescendantNodes().OfType<IsPatternExpressionSyntax>())
            {
                if (isPat.Expression is IdentifierNameSyntax id)
                {
                    var pat = isPat.Pattern.ToString();
                    if (pat.Contains("null", StringComparison.Ordinal))
                    {
                        nullCheckedVars.Add(id.Identifier.Text);
                    }
                }
            }
            foreach (var cond in bodyOrExpr.DescendantNodes().OfType<ConditionalAccessExpressionSyntax>())
            {
                if (cond.Expression is IdentifierNameSyntax id)
                {
                    nullCheckedVars.Add(id.Identifier.Text);
                }
            }
            foreach (var inv in bodyOrExpr.DescendantNodes().OfType<InvocationExpressionSyntax>())
            {
                var invName = inv.Expression.ToString();
                if (invName.Contains("ThrowIfNull", StringComparison.Ordinal) ||
                    invName.Contains("IsNullOrEmpty", StringComparison.Ordinal) ||
                    invName.Contains("IsNullOrWhiteSpace", StringComparison.Ordinal))
                {
                    foreach (var arg in inv.ArgumentList.Arguments)
                    {
                        if (arg.Expression is IdentifierNameSyntax id)
                        {
                            nullCheckedVars.Add(id.Identifier.Text);
                        }
                    }
                }
            }

            // Direct dereferences x.Member or x[idx]
            foreach (var ma in bodyOrExpr.DescendantNodes().OfType<MemberAccessExpressionSyntax>())
            {
                if (ma.Expression is IdentifierNameSyntax id)
                {
                    dereferencedVars.Add(id.Identifier.Text);
                }
                else if (ma.Expression is ThisExpressionSyntax)
                {
                    fieldReadCount++;
                }
            }
            foreach (var elem in bodyOrExpr.DescendantNodes().OfType<ElementAccessExpressionSyntax>())
            {
                if (elem.Expression is IdentifierNameSyntax id)
                {
                    dereferencedVars.Add(id.Identifier.Text);
                }
            }

            // Variable reads and semantic symbol resolution ratio
            foreach (var id in bodyOrExpr.DescendantNodes().OfType<IdentifierNameSyntax>())
            {
                string name = id.Identifier.Text;
                if (id.Parent is MemberAccessExpressionSyntax pma && pma.Name == id) continue;
                if (id.Parent is AssignmentExpressionSyntax passign && passign.Left == id) continue;

                varReads[name] = varReads.GetValueOrDefault(name) + 1;
                if (semanticModel != null)
                {
                    totalIdentifierRefs++;
                    var sym = semanticModel.GetSymbolInfo(id).Symbol;
                    if (sym == null)
                    {
                        unresolvedIdentifierRefs++;
                    }
                    else if (sym.Kind == SymbolKind.Field)
                    {
                        fieldReadCount++;
                    }
                }
            }
        }

        int checkedParamNullCount = parameterNames.Count(p => nullCheckedVars.Contains(p));
        int uncheckedParamDerefCount = parameterNames.Count(p => dereferencedVars.Contains(p) && !nullCheckedVars.Contains(p));
        int uncheckedNullableVarDerefCount = nullableAssignedVars.Count(v => dereferencedVars.Contains(v) && !nullCheckedVars.Contains(v));
        int unusedLocalCount = localDecls.Keys.Count(v => varReads.GetValueOrDefault(v) == 0);
        int multiAssignedLocalCount = localDecls.Keys.Count(v => varWrites.GetValueOrDefault(v) > 1);
        int undisposedResourceCount = Math.Max(0, disposableAllocations - usingWrappedAllocations - explicitDisposeCalls);

        // Roslyn Semantic DataFlow analysis
        double semanticAvailable = semanticModel != null ? 1.0 : 0.0;
        double dfgAvailable = 0.0;
        double dfgSucceeded = 0.0;
        double dfgVariablesDeclared = 0.0;
        double dfgAlwaysAssigned = 0.0;
        double dfgFlowsIn = 0.0;
        double dfgFlowsOut = 0.0;
        double dfgReadInside = 0.0;
        double dfgWrittenInside = 0.0;
        double dfgCaptured = 0.0;
        double dfgUnsafeAddressTaken = 0.0;
        double dfgUnassignedReadProxy = 0.0;

        if (semanticModel != null && methodNode.Body != null)
        {
            try
            {
                var dfa = semanticModel.AnalyzeDataFlow(methodNode.Body);
                dfgAvailable = 1.0;
                if (dfa != null && dfa.Succeeded)
                {
                    dfgSucceeded = 1.0;
                    dfgVariablesDeclared = dfa.VariablesDeclared.Length;
                    dfgAlwaysAssigned = dfa.AlwaysAssigned.Length;
                    dfgFlowsIn = dfa.DataFlowsIn.Length;
                    dfgFlowsOut = dfa.DataFlowsOut.Length;
                    dfgReadInside = dfa.ReadInside.Length;
                    dfgWrittenInside = dfa.WrittenInside.Length;
                    dfgCaptured = dfa.Captured.Length;
                    dfgUnsafeAddressTaken = dfa.UnsafeAddressTaken.Length;
                    var alwaysAssignedSet = dfa.AlwaysAssigned.ToHashSet(SymbolEqualityComparer.Default);
                    dfgUnassignedReadProxy = dfa.ReadInside.Count(sym =>
                        dfa.VariablesDeclared.Contains(sym, SymbolEqualityComparer.Default) &&
                        !alwaysAssignedSet.Contains(sym));
                }
            }
            catch
            {
                dfgAvailable = 0.0;
                dfgSucceeded = 0.0;
            }
        }

        double unresolvedRatio = totalIdentifierRefs > 0
            ? (double)unresolvedIdentifierRefs / totalIdentifierRefs
            : (semanticAvailable > 0.5 ? 0.0 : 1.0);

        return new Dictionary<string, double>
        {
            ["semantic_model_available"] = semanticAvailable,
            ["dfg_available"] = dfgAvailable,
            ["dfg_succeeded"] = dfgSucceeded,
            ["dfg_unresolved_symbol_ratio"] = unresolvedRatio,
            ["dfg_variables_declared"] = dfgVariablesDeclared,
            ["dfg_always_assigned"] = dfgAlwaysAssigned,
            ["dfg_data_flows_in"] = dfgFlowsIn,
            ["dfg_data_flows_out"] = dfgFlowsOut,
            ["dfg_read_inside"] = dfgReadInside,
            ["dfg_written_inside"] = dfgWrittenInside,
            ["dfg_captured"] = dfgCaptured,
            ["dfg_unsafe_address_taken"] = dfgUnsafeAddressTaken,
            ["dfg_unassigned_read_proxy"] = dfgUnassignedReadProxy,
            ["dfg_local_decls_count"] = localDecls.Count,
            ["dfg_unused_local_count"] = unusedLocalCount,
            ["dfg_multi_assigned_local_count"] = multiAssignedLocalCount,
            ["dfg_conditional_assigned_var_count"] = conditionalAssignedVars.Count,
            ["dfg_checked_param_null_count"] = checkedParamNullCount,
            ["dfg_unchecked_param_deref_count"] = uncheckedParamDerefCount,
            ["dfg_nullable_assigned_var_count"] = nullableAssignedVars.Count,
            ["dfg_unchecked_nullable_var_deref_count"] = uncheckedNullableVarDerefCount,
            ["dfg_unchecked_nullable_call_deref_count"] = uncheckedNullableCallDeref,
            ["dfg_disposable_allocations"] = disposableAllocations,
            ["dfg_using_wrapped_allocations"] = usingWrappedAllocations,
            ["dfg_explicit_dispose_calls"] = explicitDisposeCalls,
            ["dfg_undisposed_resource_allocations"] = undisposedResourceCount,
            ["dfg_field_read_count"] = fieldReadCount,
            ["dfg_field_write_count"] = fieldWriteCount,
            ["dfg_total_var_reads"] = varReads.Values.Sum(),
            ["dfg_total_var_writes"] = varWrites.Values.Sum()
        };
    }

    private static bool IsInsideUsing(SyntaxNode node)
    {
        foreach (var anc in node.Ancestors())
        {
            if (anc is UsingStatementSyntax) return true;
            if (anc is LocalDeclarationStatementSyntax lds && lds.UsingKeyword.IsKind(SyntaxKind.UsingKeyword)) return true;
            if (anc is BaseMethodDeclarationSyntax) break;
        }
        return false;
    }

    private static bool IsInsideBranch(SyntaxNode node)
    {
        foreach (var anc in node.Ancestors())
        {
            if (anc is IfStatementSyntax or ElseClauseSyntax or SwitchSectionSyntax or CatchClauseSyntax) return true;
            if (anc is BaseMethodDeclarationSyntax) break;
        }
        return false;
    }

    private static bool LooksNullableExpr(ExpressionSyntax expr)
    {
        if (expr.IsKind(SyntaxKind.NullLiteralExpression) || expr.IsKind(SyntaxKind.AsExpression)) return true;
        if (expr is InvocationExpressionSyntax inv && inv.Expression is MemberAccessExpressionSyntax ma)
        {
            return NullableReturnMethods.Contains(ma.Name.Identifier.Text);
        }
        return false;
    }

    private static string ShortType(string typeStr)
    {
        var clean = typeStr.Trim();
        int gen = clean.IndexOf('<');
        if (gen >= 0) clean = clean[..gen];
        int dot = clean.LastIndexOf('.');
        return dot >= 0 && dot < clean.Length - 1 ? clean[(dot + 1)..] : clean;
    }
}
