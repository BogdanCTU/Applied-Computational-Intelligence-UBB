using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

namespace RoslynPreprocessor.Extractors;

public static class CfgExtractor
{
    public static Dictionary<string, double> Extract(
        BaseMethodDeclarationSyntax methodNode,
        SemanticModel? semanticModel)
    {
        var body = methodNode.Body;
        var exprBody = methodNode.ExpressionBody;

        int branchNodes = 0;
        int loopNodes = 0;
        int switchArmCount = 0;
        int switchWithoutDefault = 0;
        int returnCount = exprBody != null ? 1 : 0;
        int earlyReturnCount = 0;
        int throwExitCount = 0;
        int breakContinueCount = 0;
        int gotoCount = 0;
        int tryCount = 0;
        int catchCount = 0;
        int emptyCatchCount = 0;
        int broadCatchCount = 0;
        int conditionalComplexity = 1;
        int maxBranchDepth = 0;
        int unreachablePostJumpCount = 0;

        if (body != null)
        {
            maxBranchDepth = ComputeMaxDepth(body, 0);

            foreach (var node in body.DescendantNodes())
            {
                switch (node)
                {
                    case IfStatementSyntax:
                        branchNodes++;
                        conditionalComplexity++;
                        break;
                    case ConditionalExpressionSyntax:
                        branchNodes++;
                        conditionalComplexity++;
                        break;
                    case SwitchStatementSyntax sw:
                        branchNodes++;
                        bool hasDefault = false;
                        foreach (var sec in sw.Sections)
                        {
                            switchArmCount++;
                            conditionalComplexity++;
                            if (sec.Labels.OfType<DefaultSwitchLabelSyntax>().Any() ||
                                sec.Labels.OfType<CasePatternSwitchLabelSyntax>().Any(l => l.Pattern is DiscardPatternSyntax))
                            {
                                hasDefault = true;
                            }
                        }
                        if (!hasDefault) switchWithoutDefault++;
                        break;
                    case SwitchExpressionSyntax swe:
                        branchNodes++;
                        bool hasDiscard = false;
                        foreach (var arm in swe.Arms)
                        {
                            switchArmCount++;
                            conditionalComplexity++;
                            if (arm.Pattern is DiscardPatternSyntax) hasDiscard = true;
                        }
                        if (!hasDiscard) switchWithoutDefault++;
                        break;
                    case ForStatementSyntax:
                    case ForEachStatementSyntax:
                    case WhileStatementSyntax:
                    case DoStatementSyntax:
                        loopNodes++;
                        conditionalComplexity++;
                        break;
                    case BinaryExpressionSyntax bin when bin.IsKind(SyntaxKind.LogicalAndExpression) || bin.IsKind(SyntaxKind.LogicalOrExpression) || bin.IsKind(SyntaxKind.CoalesceExpression):
                        conditionalComplexity++;
                        break;
                    case ReturnStatementSyntax ret:
                        returnCount++;
                        if (ret.Parent != body || !ReferenceEquals(ret, body.Statements.LastOrDefault()))
                        {
                            earlyReturnCount++;
                        }
                        break;
                    case ThrowStatementSyntax:
                    case ThrowExpressionSyntax:
                        throwExitCount++;
                        break;
                    case BreakStatementSyntax:
                    case ContinueStatementSyntax:
                        breakContinueCount++;
                        break;
                    case GotoStatementSyntax:
                        gotoCount++;
                        break;
                    case TryStatementSyntax:
                        tryCount++;
                        break;
                    case CatchClauseSyntax cc:
                        catchCount++;
                        conditionalComplexity++;
                        if (cc.Block.Statements.Count == 0)
                        {
                            emptyCatchCount++;
                        }
                        if (cc.Declaration == null ||
                            cc.Declaration.Type.ToString().EndsWith("Exception", StringComparison.Ordinal) &&
                            cc.Declaration.Type.ToString().Trim() is "Exception" or "System.Exception")
                        {
                            broadCatchCount++;
                        }
                        break;
                }
            }

            // Detect syntactically unreachable statements immediately after unconditional jumps in any block
            foreach (var block in body.DescendantNodesAndSelf().OfType<BlockSyntax>())
            {
                bool terminated = false;
                foreach (var stmt in block.Statements)
                {
                    if (terminated && stmt is not LabeledStatementSyntax)
                    {
                        unreachablePostJumpCount++;
                    }
                    if (stmt is ReturnStatementSyntax or ThrowStatementSyntax or BreakStatementSyntax or ContinueStatementSyntax or GotoStatementSyntax)
                    {
                        terminated = true;
                    }
                }
            }
        }
        else if (exprBody != null)
        {
            foreach (var node in exprBody.DescendantNodes())
            {
                if (node is ConditionalExpressionSyntax)
                {
                    branchNodes++;
                    conditionalComplexity++;
                }
                else if (node is SwitchExpressionSyntax swe)
                {
                    branchNodes++;
                    switchArmCount += swe.Arms.Count;
                    conditionalComplexity += swe.Arms.Count;
                }
                else if (node is ThrowExpressionSyntax)
                {
                    throwExitCount++;
                }
                else if (node is BinaryExpressionSyntax bin && (bin.IsKind(SyntaxKind.LogicalAndExpression) || bin.IsKind(SyntaxKind.LogicalOrExpression) || bin.IsKind(SyntaxKind.CoalesceExpression)))
                {
                    conditionalComplexity++;
                }
            }
        }

        double cfgAvailable = 0.0;
        double cfgSucceeded = 0.0;
        double cfgEndpointReachable = 0.0;
        double cfgReturnStmtCount = 0.0;
        double cfgExitPointsCount = 0.0;

        if (semanticModel != null && body != null)
        {
            try
            {
                var cfg = semanticModel.AnalyzeControlFlow(body);
                cfgAvailable = 1.0;
                if (cfg != null && cfg.Succeeded)
                {
                    cfgSucceeded = 1.0;
                    cfgEndpointReachable = cfg.EndPointIsReachable ? 1.0 : 0.0;
                    cfgReturnStmtCount = cfg.ReturnStatements.Length;
                    cfgExitPointsCount = cfg.ExitPoints.Length;
                }
            }
            catch
            {
                cfgAvailable = 0.0;
                cfgSucceeded = 0.0;
            }
        }

        return new Dictionary<string, double>
        {
            ["cfg_available"] = cfgAvailable,
            ["cfg_succeeded"] = cfgSucceeded,
            ["cfg_endpoint_reachable"] = cfgEndpointReachable,
            ["cfg_return_stmt_count"] = cfgReturnStmtCount,
            ["cfg_exit_points_count"] = cfgExitPointsCount,
            ["cfg_branch_nodes"] = branchNodes,
            ["cfg_loop_nodes"] = loopNodes,
            ["cfg_switch_arms"] = switchArmCount,
            ["cfg_switch_without_default"] = switchWithoutDefault,
            ["cfg_return_paths"] = returnCount,
            ["cfg_early_return_count"] = earlyReturnCount,
            ["cfg_throw_exit_count"] = throwExitCount,
            ["cfg_break_continue_count"] = breakContinueCount,
            ["cfg_goto_count"] = gotoCount,
            ["cfg_try_count"] = tryCount,
            ["cfg_catch_count"] = catchCount,
            ["cfg_empty_catch_count"] = emptyCatchCount,
            ["cfg_broad_catch_count"] = broadCatchCount,
            ["cfg_conditional_complexity"] = conditionalComplexity,
            ["cfg_max_nesting_depth"] = maxBranchDepth,
            ["cfg_unreachable_post_jump_count"] = unreachablePostJumpCount
        };
    }

    private static int ComputeMaxDepth(SyntaxNode node, int currentDepth)
    {
        int maxDepth = currentDepth;
        foreach (var child in node.ChildNodes())
        {
            int nextDepth = child is IfStatementSyntax or ForStatementSyntax or ForEachStatementSyntax
                or WhileStatementSyntax or DoStatementSyntax or SwitchStatementSyntax
                or TryStatementSyntax or UsingStatementSyntax or LockStatementSyntax
                ? currentDepth + 1
                : currentDepth;
            int childMax = ComputeMaxDepth(child, nextDepth);
            if (childMax > maxDepth)
            {
                maxDepth = childMax;
            }
        }
        return maxDepth;
    }
}
