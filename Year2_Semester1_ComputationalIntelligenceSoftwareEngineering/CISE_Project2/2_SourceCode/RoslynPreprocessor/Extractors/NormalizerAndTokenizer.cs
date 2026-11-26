using System.Security.Cryptography;
using System.Text;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using RoslynPreprocessor.Models;

namespace RoslynPreprocessor.Extractors;

public sealed class NormalizationResult
{
    public string NormalizedSource { get; init; } = string.Empty;
    public string StructuralHash { get; init; } = string.Empty;
    public List<string> TokensNormalized { get; init; } = new();
    public List<string> ApiCalls { get; init; } = new();
    public Dictionary<string, double> LexicalMetrics { get; init; } = new();
}

public static class NormalizerAndTokenizer
{
    private static readonly HashSet<SyntaxKind> OperatorKinds = new()
    {
        SyntaxKind.PlusToken, SyntaxKind.MinusToken, SyntaxKind.AsteriskToken, SyntaxKind.SlashToken,
        SyntaxKind.PercentToken, SyntaxKind.EqualsToken, SyntaxKind.EqualsEqualsToken,
        SyntaxKind.ExclamationEqualsToken, SyntaxKind.LessThanToken, SyntaxKind.LessThanEqualsToken,
        SyntaxKind.GreaterThanToken, SyntaxKind.GreaterThanEqualsToken, SyntaxKind.AmpersandAmpersandToken,
        SyntaxKind.BarBarToken, SyntaxKind.ExclamationToken, SyntaxKind.QuestionQuestionToken,
        SyntaxKind.QuestionQuestionEqualsToken, SyntaxKind.QuestionToken, SyntaxKind.PlusPlusToken,
        SyntaxKind.MinusMinusToken, SyntaxKind.PlusEqualsToken, SyntaxKind.MinusEqualsToken,
        SyntaxKind.AsteriskEqualsToken, SyntaxKind.SlashEqualsToken, SyntaxKind.EqualsGreaterThanToken,
        SyntaxKind.AmpersandToken, SyntaxKind.BarToken, SyntaxKind.CaretToken,
        SyntaxKind.LessThanLessThanToken, SyntaxKind.GreaterThanGreaterThanToken
    };

    private static readonly HashSet<SyntaxKind> PunctuationKinds = new()
    {
        SyntaxKind.OpenBraceToken, SyntaxKind.CloseBraceToken, SyntaxKind.OpenParenToken,
        SyntaxKind.CloseParenToken, SyntaxKind.OpenBracketToken, SyntaxKind.CloseBracketToken,
        SyntaxKind.SemicolonToken, SyntaxKind.CommaToken, SyntaxKind.DotToken,
        SyntaxKind.ColonToken, SyntaxKind.ColonColonToken
    };

    public static NormalizationResult Analyze(SyntaxNode methodNode, NormalizationOptions options)
    {
        var tokensNormalized = new List<string>();
        var structuralTokens = new List<string>();
        var apiCalls = new List<string>();

        int keywordCount = 0;
        int operatorCount = 0;
        int identifierCount = 0;
        int literalCount = 0;
        int nullLiteralCount = 0;
        int stringLiteralCount = 0;
        int numericLiteralCount = 0;
        int boolLiteralCount = 0;
        int punctuationCount = 0;
        var distinctIdentifiers = new HashSet<string>(StringComparer.Ordinal);

        // Extract API invocation patterns (e.g., Console.WriteLine, list.Add, Dispose)
        foreach (var invocation in methodNode.DescendantNodes().OfType<InvocationExpressionSyntax>())
        {
            string? apiName = ExtractApiCallName(invocation.Expression);
            if (!string.IsNullOrWhiteSpace(apiName))
            {
                apiCalls.Add(apiName);
            }
        }
        foreach (var creation in methodNode.DescendantNodes().OfType<ObjectCreationExpressionSyntax>())
        {
            var typeName = creation.Type.ToString().Trim();
            if (!string.IsNullOrEmpty(typeName))
            {
                apiCalls.Add("new:" + ShortTypeName(typeName));
            }
        }

        foreach (var token in methodNode.DescendantTokens(descendIntoTrivia: false))
        {
            if (token.IsKind(SyntaxKind.EndOfFileToken) || token.Span.Length == 0)
            {
                continue;
            }

            var kind = token.Kind();
            string text = token.Text;

            if (kind == SyntaxKind.IdentifierToken)
            {
                identifierCount++;
                distinctIdentifiers.Add(text);
                bool isTypeOrMember = IsTypeOrApiIdentifier(token);
                if (options.PreserveIdentifiers || (isTypeOrMember && (options.PreserveApiNames || options.PreserveTypeNames)))
                {
                    tokensNormalized.Add(text);
                }
                else
                {
                    tokensNormalized.Add("ID");
                }
                structuralTokens.Add(isTypeOrMember ? text : "ID");
                continue;
            }

            if (SyntaxFacts.IsKeywordKind(kind))
            {
                keywordCount++;
                tokensNormalized.Add(text);
                structuralTokens.Add(text);
                continue;
            }

            if (kind == SyntaxKind.NullKeyword)
            {
                literalCount++;
                nullLiteralCount++;
                tokensNormalized.Add("null");
                structuralTokens.Add("null");
                continue;
            }

            if (kind == SyntaxKind.TrueKeyword || kind == SyntaxKind.FalseKeyword)
            {
                literalCount++;
                boolLiteralCount++;
                tokensNormalized.Add(text);
                structuralTokens.Add(text);
                continue;
            }

            if (kind == SyntaxKind.StringLiteralToken || kind == SyntaxKind.InterpolatedStringTextToken ||
                kind == SyntaxKind.Utf8StringLiteralToken || kind == SyntaxKind.SingleLineRawStringLiteralToken ||
                kind == SyntaxKind.MultiLineRawStringLiteralToken)
            {
                literalCount++;
                stringLiteralCount++;
                bool isEmptyStr = text == "\"\"" || text.Length == 0;
                string norm = (options.AbstractStringLiterals && !(options.PreserveSpecialLiterals && isEmptyStr))
                    ? "<STR>"
                    : (isEmptyStr ? "\"\"" : text);
                tokensNormalized.Add(norm);
                structuralTokens.Add("<STR>");
                continue;
            }

            if (kind == SyntaxKind.CharacterLiteralToken)
            {
                literalCount++;
                string norm = options.AbstractStringLiterals ? "<CHAR>" : text;
                tokensNormalized.Add(norm);
                structuralTokens.Add("<CHAR>");
                continue;
            }

            if (kind == SyntaxKind.NumericLiteralToken)
            {
                literalCount++;
                numericLiteralCount++;
                bool isSpecial = text == "0" || text == "1";
                string norm = (options.AbstractNumericLiterals && !(options.PreserveSpecialLiterals && isSpecial))
                    ? "<NUM>"
                    : text;
                tokensNormalized.Add(norm);
                structuralTokens.Add(isSpecial ? text : "<NUM>");
                continue;
            }

            if (OperatorKinds.Contains(kind))
            {
                operatorCount++;
                tokensNormalized.Add(text);
                structuralTokens.Add(text);
                continue;
            }

            if (PunctuationKinds.Contains(kind))
            {
                punctuationCount++;
                tokensNormalized.Add(text);
                structuralTokens.Add(text);
                continue;
            }

            tokensNormalized.Add(text);
            structuralTokens.Add(text);
        }

        string normalizedSource = options.CollapseWhitespace
            ? string.Join(" ", tokensNormalized)
            : methodNode.WithoutTrivia().ToFullString();

        string structuralString = string.Join(" ", structuralTokens);
        string structuralHash = ComputeSha256(structuralString);

        int totalTokens = Math.Max(tokensNormalized.Count, 1);
        double avgTokenLen = tokensNormalized.Count > 0
            ? tokensNormalized.Average(t => t.Length)
            : 0.0;

        var lexical = new Dictionary<string, double>
        {
            ["token_count"] = tokensNormalized.Count,
            ["keyword_count"] = keywordCount,
            ["operator_count"] = operatorCount,
            ["identifier_count"] = identifierCount,
            ["distinct_identifier_count"] = distinctIdentifiers.Count,
            ["literal_count"] = literalCount,
            ["null_literal_count"] = nullLiteralCount,
            ["string_literal_count"] = stringLiteralCount,
            ["numeric_literal_count"] = numericLiteralCount,
            ["bool_literal_count"] = boolLiteralCount,
            ["punctuation_count"] = punctuationCount,
            ["api_call_count"] = apiCalls.Count,
            ["distinct_api_call_count"] = apiCalls.Distinct(StringComparer.Ordinal).Count(),
            ["keyword_ratio"] = (double)keywordCount / totalTokens,
            ["operator_ratio"] = (double)operatorCount / totalTokens,
            ["identifier_ratio"] = (double)identifierCount / totalTokens,
            ["literal_ratio"] = (double)literalCount / totalTokens,
            ["null_literal_ratio"] = (double)nullLiteralCount / totalTokens,
            ["identifier_diversity"] = identifierCount > 0 ? (double)distinctIdentifiers.Count / identifierCount : 0.0,
            ["avg_token_length"] = avgTokenLen
        };

        return new NormalizationResult
        {
            NormalizedSource = normalizedSource,
            StructuralHash = structuralHash,
            TokensNormalized = tokensNormalized,
            ApiCalls = apiCalls,
            LexicalMetrics = lexical
        };
    }

    private static bool IsTypeOrApiIdentifier(SyntaxToken token)
    {
        var parent = token.Parent;
        if (parent is MemberAccessExpressionSyntax ma && ma.Name.Identifier == token)
            return true;
        if (parent is InvocationExpressionSyntax)
            return true;
        if (parent is SimpleNameSyntax sn && (sn.Parent is ObjectCreationExpressionSyntax || sn.Parent is TypeSyntax || sn.Parent is QualifiedNameSyntax))
            return true;
        return false;
    }

    private static string? ExtractApiCallName(ExpressionSyntax expr)
    {
        return expr switch
        {
            MemberAccessExpressionSyntax ma => $"{ShortQualifier(ma.Expression)}.{ma.Name.Identifier.Text}",
            IdentifierNameSyntax id => id.Identifier.Text,
            GenericNameSyntax gn => gn.Identifier.Text,
            MemberBindingExpressionSyntax mb => mb.Name.Identifier.Text,
            _ => null
        };
    }

    private static string ShortQualifier(ExpressionSyntax expr)
    {
        return expr switch
        {
            IdentifierNameSyntax id => id.Identifier.Text,
            MemberAccessExpressionSyntax ma => ma.Name.Identifier.Text,
            ThisExpressionSyntax => "this",
            BaseExpressionSyntax => "base",
            _ => "expr"
        };
    }

    private static string ShortTypeName(string full)
    {
        int idx = full.LastIndexOf('.');
        return idx >= 0 && idx < full.Length - 1 ? full[(idx + 1)..] : full;
    }

    public static string ComputeSha256(string input)
    {
        var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(input));
        return Convert.ToHexString(bytes).ToLowerInvariant();
    }
}
