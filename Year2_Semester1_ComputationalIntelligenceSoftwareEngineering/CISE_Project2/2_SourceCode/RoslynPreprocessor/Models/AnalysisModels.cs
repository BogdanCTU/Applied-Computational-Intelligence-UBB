using System.Text.Json.Serialization;

namespace RoslynPreprocessor.Models;

public sealed class NormalizationOptions
{
    [JsonPropertyName("strip_comments")]
    public bool StripComments { get; set; } = true;

    [JsonPropertyName("collapse_whitespace")]
    public bool CollapseWhitespace { get; set; } = true;

    [JsonPropertyName("abstract_string_literals")]
    public bool AbstractStringLiterals { get; set; } = true;

    [JsonPropertyName("abstract_numeric_literals")]
    public bool AbstractNumericLiterals { get; set; } = true;

    [JsonPropertyName("preserve_special_literals")]
    public bool PreserveSpecialLiterals { get; set; } = true;

    [JsonPropertyName("preserve_identifiers")]
    public bool PreserveIdentifiers { get; set; } = true;

    [JsonPropertyName("preserve_api_names")]
    public bool PreserveApiNames { get; set; } = true;

    [JsonPropertyName("preserve_type_names")]
    public bool PreserveTypeNames { get; set; } = true;
}

public sealed class FileAnalysisRequest
{
    [JsonPropertyName("request_id")]
    public string? RequestId { get; set; }

    [JsonPropertyName("mode")]
    public string Mode { get; set; } = "file"; // "file" or "method_snippet"

    [JsonPropertyName("file_path")]
    public string FilePath { get; set; } = "Input.cs";

    [JsonPropertyName("source_code")]
    public string SourceCode { get; set; } = string.Empty;

    [JsonPropertyName("normalization")]
    public NormalizationOptions? Normalization { get; set; }
}

public sealed class SyntaxErrorInfo
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("line")]
    public int Line { get; set; }

    [JsonPropertyName("column")]
    public int Column { get; set; }

    [JsonPropertyName("message")]
    public string Message { get; set; } = string.Empty;
}

public sealed class MethodAnalysisRecord
{
    [JsonPropertyName("class_name")]
    public string ClassName { get; set; } = string.Empty;

    [JsonPropertyName("type_kind")]
    public string TypeKind { get; set; } = "class";

    [JsonPropertyName("method_name")]
    public string MethodName { get; set; } = string.Empty;

    [JsonPropertyName("method_signature")]
    public string MethodSignature { get; set; } = string.Empty;

    [JsonPropertyName("start_line")]
    public int StartLine { get; set; }

    [JsonPropertyName("end_line")]
    public int EndLine { get; set; }

    [JsonPropertyName("is_constructor")]
    public bool IsConstructor { get; set; }

    [JsonPropertyName("is_static")]
    public bool IsStatic { get; set; }

    [JsonPropertyName("is_async")]
    public bool IsAsync { get; set; }

    [JsonPropertyName("is_generic")]
    public bool IsGeneric { get; set; }

    [JsonPropertyName("is_expression_bodied")]
    public bool IsExpressionBodied { get; set; }

    [JsonPropertyName("has_syntax_errors")]
    public bool HasSyntaxErrors { get; set; }

    [JsonPropertyName("raw_source")]
    public string RawSource { get; set; } = string.Empty;

    [JsonPropertyName("normalized_source")]
    public string NormalizedSource { get; set; } = string.Empty;

    [JsonPropertyName("structural_hash")]
    public string StructuralHash { get; set; } = string.Empty;

    [JsonPropertyName("tokens_normalized")]
    public List<string> TokensNormalized { get; set; } = new();

    [JsonPropertyName("api_calls")]
    public List<string> ApiCalls { get; set; } = new();

    [JsonPropertyName("lexical_metrics")]
    public Dictionary<string, double> LexicalMetrics { get; set; } = new();

    [JsonPropertyName("ast_metrics")]
    public Dictionary<string, double> AstMetrics { get; set; } = new();

    [JsonPropertyName("cfg_metrics")]
    public Dictionary<string, double> CfgMetrics { get; set; } = new();

    [JsonPropertyName("dfg_metrics")]
    public Dictionary<string, double> DfgMetrics { get; set; } = new();

    [JsonPropertyName("structural_metrics")]
    public Dictionary<string, double> StructuralMetrics { get; set; } = new();

    [JsonPropertyName("extraction_warnings")]
    public List<string> ExtractionWarnings { get; set; } = new();
}

public sealed class FileAnalysisResponse
{
    [JsonPropertyName("request_id")]
    public string? RequestId { get; set; }

    [JsonPropertyName("success")]
    public bool Success { get; set; }

    [JsonPropertyName("file_path")]
    public string FilePath { get; set; } = string.Empty;

    [JsonPropertyName("has_syntax_errors")]
    public bool HasSyntaxErrors { get; set; }

    [JsonPropertyName("syntax_error_count")]
    public int SyntaxErrorCount { get; set; }

    [JsonPropertyName("syntax_errors")]
    public List<SyntaxErrorInfo> SyntaxErrors { get; set; } = new();

    [JsonPropertyName("semantic_model_available")]
    public bool SemanticModelAvailable { get; set; }

    [JsonPropertyName("methods")]
    public List<MethodAnalysisRecord> Methods { get; set; } = new();

    [JsonPropertyName("error_message")]
    public string? ErrorMessage { get; set; }
}
