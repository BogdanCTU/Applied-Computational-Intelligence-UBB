using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

namespace RoslynPreprocessor.Extractors;

public static class AstExtractor
{
    private static readonly HashSet<string> LinqMethods = new(StringComparer.Ordinal)
    {
        "Where", "Select", "SelectMany", "First", "FirstOrDefault", "Single", "SingleOrDefault",
        "Last", "LastOrDefault", "Any", "All", "Count", "Sum", "Average", "Min", "Max",
        "OrderBy", "OrderByDescending", "GroupBy", "Join", "Distinct", "ToList", "ToArray",
        "ToDictionary", "Aggregate", "Skip", "Take", "Concat", "Union", "Except", "Intersect"
    };

    public static Dictionary<string, double> Extract(SyntaxNode methodNode)
    {
        int totalNodes = 0;
        int expressionCount = 0;
        int statementCount = 0;
        int conditionalExprCount = 0;
        int binaryExprCount = 0;
        int unaryExprCount = 0;
        int assignmentCount = 0;
        int compoundAssignmentCount = 0;
        int invocationCount = 0;
        int memberAccessCount = 0;
        int elementAccessCount = 0;
        int objectCreationCount = 0;
        int arrayCreationCount = 0;
        int castExprCount = 0;
        int asExprCount = 0;
        int isPatternCount = 0;
        int lambdaCount = 0;
        int interpolatedStringCount = 0;
        int awaitExprCount = 0;

        int ifStmtCount = 0;
        int elseClauseCount = 0;
        int switchStmtCount = 0;
        int switchExprCount = 0;
        int forStmtCount = 0;
        int foreachStmtCount = 0;
        int whileStmtCount = 0;
        int doStmtCount = 0;
        int tryStmtCount = 0;
        int catchClauseCount = 0;
        int catchFilterCount = 0;
        int finallyClauseCount = 0;
        int usingStmtCount = 0;
        int lockStmtCount = 0;
        int throwStmtOrExprCount = 0;
        int returnStmtCount = 0;
        int yieldStmtCount = 0;
        int localDeclStmtCount = 0;

        int nullConditionalCount = 0;
        int nullCoalescingCount = 0;
        int nullCoalescingAssignCount = 0;
        int nullComparisonCount = 0;
        int isNullPatternCount = 0;
        int isNotNullPatternCount = 0;
        int nullForgivingCount = 0;
        int linqInvocationCount = 0;
        int unsafeOrFixedCount = 0;

        foreach (var node in methodNode.DescendantNodes())
        {
            totalNodes++;
            switch (node)
            {
                case ExpressionSyntax:
                    expressionCount++;
                    break;
                case StatementSyntax:
                    statementCount++;
                    break;
            }

            switch (node)
            {
                case ConditionalExpressionSyntax:
                    conditionalExprCount++;
                    break;
                case BinaryExpressionSyntax bin:
                    binaryExprCount++;
                    if (bin.IsKind(SyntaxKind.CoalesceExpression))
                    {
                        nullCoalescingCount++;
                    }
                    else if (bin.IsKind(SyntaxKind.AsExpression))
                    {
                        asExprCount++;
                    }
                    else if ((bin.IsKind(SyntaxKind.EqualsExpression) || bin.IsKind(SyntaxKind.NotEqualsExpression)) &&
                             (bin.Left.IsKind(SyntaxKind.NullLiteralExpression) || bin.Right.IsKind(SyntaxKind.NullLiteralExpression)))
                    {
                        nullComparisonCount++;
                    }
                    break;
                case PrefixUnaryExpressionSyntax:
                    unaryExprCount++;
                    break;
                case PostfixUnaryExpressionSyntax post:
                    unaryExprCount++;
                    if (post.IsKind(SyntaxKind.SuppressNullableWarningExpression))
                    {
                        nullForgivingCount++;
                    }
                    break;
                case AssignmentExpressionSyntax assign:
                    assignmentCount++;
                    if (!assign.IsKind(SyntaxKind.SimpleAssignmentExpression))
                    {
                        compoundAssignmentCount++;
                    }
                    if (assign.IsKind(SyntaxKind.CoalesceAssignmentExpression))
                    {
                        nullCoalescingAssignCount++;
                    }
                    break;
                case InvocationExpressionSyntax inv:
                    invocationCount++;
                    if (inv.Expression is MemberAccessExpressionSyntax ma && LinqMethods.Contains(ma.Name.Identifier.Text))
                    {
                        linqInvocationCount++;
                    }
                    break;
                case MemberAccessExpressionSyntax:
                    memberAccessCount++;
                    break;
                case ElementAccessExpressionSyntax:
                    elementAccessCount++;
                    break;
                case BaseObjectCreationExpressionSyntax:
                    objectCreationCount++;
                    break;
                case ArrayCreationExpressionSyntax:
                case ImplicitArrayCreationExpressionSyntax:
                case CollectionExpressionSyntax:
                    arrayCreationCount++;
                    break;
                case CastExpressionSyntax:
                    castExprCount++;
                    break;
                case IsPatternExpressionSyntax isPat:
                    isPatternCount++;
                    var patText = isPat.Pattern.ToString().Trim();
                    if (patText == "null") isNullPatternCount++;
                    else if (patText == "not null") isNotNullPatternCount++;
                    break;
                case LambdaExpressionSyntax:
                    lambdaCount++;
                    break;
                case InterpolatedStringExpressionSyntax:
                    interpolatedStringCount++;
                    break;
                case AwaitExpressionSyntax:
                    awaitExprCount++;
                    break;
                case ConditionalAccessExpressionSyntax:
                    nullConditionalCount++;
                    break;
                case IfStatementSyntax:
                    ifStmtCount++;
                    break;
                case ElseClauseSyntax:
                    elseClauseCount++;
                    break;
                case SwitchStatementSyntax:
                    switchStmtCount++;
                    break;
                case SwitchExpressionSyntax:
                    switchExprCount++;
                    break;
                case ForStatementSyntax:
                    forStmtCount++;
                    break;
                case ForEachStatementSyntax:
                    foreachStmtCount++;
                    break;
                case WhileStatementSyntax:
                    whileStmtCount++;
                    break;
                case DoStatementSyntax:
                    doStmtCount++;
                    break;
                case TryStatementSyntax:
                    tryStmtCount++;
                    break;
                case CatchClauseSyntax cc:
                    catchClauseCount++;
                    if (cc.Filter != null) catchFilterCount++;
                    break;
                case FinallyClauseSyntax:
                    finallyClauseCount++;
                    break;
                case UsingStatementSyntax:
                    usingStmtCount++;
                    break;
                case LocalDeclarationStatementSyntax lds:
                    localDeclStmtCount++;
                    if (lds.UsingKeyword.IsKind(SyntaxKind.UsingKeyword))
                    {
                        usingStmtCount++;
                    }
                    break;
                case LockStatementSyntax:
                    lockStmtCount++;
                    break;
                case ThrowStatementSyntax:
                case ThrowExpressionSyntax:
                    throwStmtOrExprCount++;
                    break;
                case ReturnStatementSyntax:
                    returnStmtCount++;
                    break;
                case YieldStatementSyntax:
                    yieldStmtCount++;
                    break;
                case UnsafeStatementSyntax:
                case FixedStatementSyntax:
                    unsafeOrFixedCount++;
                    break;
            }
        }

        double denom = Math.Max(totalNodes, 1);
        return new Dictionary<string, double>
        {
            ["ast_node_count"] = totalNodes,
            ["ast_expression_count"] = expressionCount,
            ["ast_statement_count"] = statementCount,
            ["ast_conditional_expr_count"] = conditionalExprCount,
            ["ast_binary_expr_count"] = binaryExprCount,
            ["ast_unary_expr_count"] = unaryExprCount,
            ["ast_assignment_count"] = assignmentCount,
            ["ast_compound_assignment_count"] = compoundAssignmentCount,
            ["ast_invocation_count"] = invocationCount,
            ["ast_member_access_count"] = memberAccessCount,
            ["ast_element_access_count"] = elementAccessCount,
            ["ast_object_creation_count"] = objectCreationCount,
            ["ast_array_or_collection_creation_count"] = arrayCreationCount,
            ["ast_cast_expr_count"] = castExprCount,
            ["ast_as_expr_count"] = asExprCount,
            ["ast_is_pattern_count"] = isPatternCount,
            ["ast_lambda_count"] = lambdaCount,
            ["ast_interpolated_string_count"] = interpolatedStringCount,
            ["ast_await_count"] = awaitExprCount,
            ["ast_if_stmt_count"] = ifStmtCount,
            ["ast_else_clause_count"] = elseClauseCount,
            ["ast_switch_stmt_count"] = switchStmtCount,
            ["ast_switch_expr_count"] = switchExprCount,
            ["ast_for_stmt_count"] = forStmtCount,
            ["ast_foreach_stmt_count"] = foreachStmtCount,
            ["ast_while_stmt_count"] = whileStmtCount,
            ["ast_do_stmt_count"] = doStmtCount,
            ["ast_try_stmt_count"] = tryStmtCount,
            ["ast_catch_clause_count"] = catchClauseCount,
            ["ast_catch_filter_count"] = catchFilterCount,
            ["ast_finally_clause_count"] = finallyClauseCount,
            ["ast_using_stmt_count"] = usingStmtCount,
            ["ast_lock_stmt_count"] = lockStmtCount,
            ["ast_throw_count"] = throwStmtOrExprCount,
            ["ast_return_stmt_count"] = returnStmtCount,
            ["ast_yield_stmt_count"] = yieldStmtCount,
            ["ast_local_decl_stmt_count"] = localDeclStmtCount,
            ["ast_null_conditional_count"] = nullConditionalCount,
            ["ast_null_coalescing_count"] = nullCoalescingCount,
            ["ast_null_coalescing_assign_count"] = nullCoalescingAssignCount,
            ["ast_null_comparison_count"] = nullComparisonCount,
            ["ast_is_null_pattern_count"] = isNullPatternCount,
            ["ast_is_not_null_pattern_count"] = isNotNullPatternCount,
            ["ast_null_forgiving_count"] = nullForgivingCount,
            ["ast_linq_invocation_count"] = linqInvocationCount,
            ["ast_unsafe_or_fixed_count"] = unsafeOrFixedCount,
            ["ast_null_syntax_density"] = (nullConditionalCount + nullCoalescingCount + nullCoalescingAssignCount + nullComparisonCount + isNullPatternCount + isNotNullPatternCount) / denom,
            ["ast_cast_density"] = (castExprCount + asExprCount) / denom,
            ["ast_exception_density"] = (tryStmtCount + catchClauseCount + throwStmtOrExprCount) / denom
        };
    }
}
