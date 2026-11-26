using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

namespace RoslynPreprocessor.Extractors;

public static class StructuralExtractor
{
    public static Dictionary<string, double> Extract(
        BaseMethodDeclarationSyntax methodNode,
        Dictionary<string, double> astMetrics,
        Dictionary<string, double> cfgMetrics)
    {
        var span = methodNode.GetLocation().GetLineSpan();
        int methodLoc = span.EndLinePosition.Line - span.StartLinePosition.Line + 1;
        string raw = methodNode.ToFullString();
        int logicalLoc = raw.Split('\n')
            .Select(l => l.Trim())
            .Count(l => l.Length > 0 && !l.StartsWith("//", StringComparison.Ordinal) && !l.StartsWith("/*", StringComparison.Ordinal) && !l.StartsWith("*", StringComparison.Ordinal));

        int parameterCount = methodNode.ParameterList.Parameters.Count;
        int localVars = methodNode.DescendantNodes().OfType<VariableDeclaratorSyntax>().Count();
        double branches = cfgMetrics.GetValueOrDefault("cfg_branch_nodes", 0.0);
        double loops = cfgMetrics.GetValueOrDefault("cfg_loop_nodes", 0.0);
        double complexity = cfgMetrics.GetValueOrDefault("cfg_conditional_complexity", 1.0);
        double maxNesting = cfgMetrics.GetValueOrDefault("cfg_max_nesting_depth", 0.0);
        double invocations = astMetrics.GetValueOrDefault("ast_invocation_count", 0.0);
        double exceptionHandlers = astMetrics.GetValueOrDefault("ast_catch_clause_count", 0.0);
        double statements = astMetrics.GetValueOrDefault("ast_statement_count", 0.0);

        bool isStatic = methodNode.Modifiers.Any(m => m.IsKind(SyntaxKind.StaticKeyword));
        bool isAsync = methodNode.Modifiers.Any(m => m.IsKind(SyntaxKind.AsyncKeyword));
        bool isGeneric = methodNode is MethodDeclarationSyntax md && md.TypeParameterList != null;
        bool isExprBodied = methodNode.ExpressionBody != null && methodNode.Body == null;
        bool isConstructor = methodNode is ConstructorDeclarationSyntax;

        return new Dictionary<string, double>
        {
            ["struct_cyclomatic_complexity"] = complexity,
            ["struct_method_loc"] = Math.Max(methodLoc, 1),
            ["struct_logical_loc"] = Math.Max(logicalLoc, 1),
            ["struct_parameter_count"] = parameterCount,
            ["struct_max_nesting_depth"] = maxNesting,
            ["struct_local_variable_count"] = localVars,
            ["struct_branch_count"] = branches,
            ["struct_loop_count"] = loops,
            ["struct_invocation_count"] = invocations,
            ["struct_exception_handler_count"] = exceptionHandlers,
            ["struct_statement_count"] = statements,
            ["struct_is_static"] = isStatic ? 1.0 : 0.0,
            ["struct_is_async"] = isAsync ? 1.0 : 0.0,
            ["struct_is_generic"] = isGeneric ? 1.0 : 0.0,
            ["struct_is_expression_bodied"] = isExprBodied ? 1.0 : 0.0,
            ["struct_is_constructor"] = isConstructor ? 1.0 : 0.0
        };
    }
}
