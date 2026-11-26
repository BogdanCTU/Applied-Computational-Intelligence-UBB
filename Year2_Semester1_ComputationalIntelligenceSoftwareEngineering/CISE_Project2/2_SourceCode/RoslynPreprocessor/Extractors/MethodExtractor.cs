using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using RoslynPreprocessor.Models;

namespace RoslynPreprocessor.Extractors;

public static class MethodExtractor
{
    private const string DummyContainerName = "__MethodContainer__";
    private static readonly Lazy<List<MetadataReference>> PlatformReferences = new(LoadPlatformReferences);

    public static FileAnalysisResponse Analyze(FileAnalysisRequest request)
    {
        var normOptions = request.Normalization ?? new NormalizationOptions();
        bool snippetMode = string.Equals(request.Mode, "method_snippet", StringComparison.OrdinalIgnoreCase);

        string sourceToParse = request.SourceCode ?? string.Empty;
        if (string.IsNullOrWhiteSpace(sourceToParse))
        {
            return new FileAnalysisResponse
            {
                RequestId = request.RequestId,
                Success = false,
                FilePath = request.FilePath,
                HasSyntaxErrors = true,
                SyntaxErrorCount = 1,
                SyntaxErrors = new List<SyntaxErrorInfo>
                {
                    new() { Id = "EMPTY", Line = 1, Column = 1, Message = "Source code is empty." }
                },
                ErrorMessage = "Source code is empty."
            };
        }

        int lineOffset = 0;
        if (snippetMode)
        {
            sourceToParse = $"class {DummyContainerName}\n{{\n{sourceToParse}\n}}";
            lineOffset = 2;
        }

        SyntaxTree tree;
        try
        {
            tree = CSharpSyntaxTree.ParseText(
                sourceToParse,
                new CSharpParseOptions(LanguageVersion.Preview),
                path: request.FilePath);
        }
        catch (Exception ex)
        {
            return new FileAnalysisResponse
            {
                RequestId = request.RequestId,
                Success = false,
                FilePath = request.FilePath,
                HasSyntaxErrors = true,
                SyntaxErrorCount = 1,
                ErrorMessage = $"Roslyn parse exception: {ex.Message}"
            };
        }

        var root = tree.GetRoot();
        var syntaxDiagnostics = tree.GetDiagnostics()
            .Where(d => d.Severity == DiagnosticSeverity.Error)
            .ToList();

        var syntaxErrors = syntaxDiagnostics.Select(d =>
        {
            var ls = d.Location.GetLineSpan();
            return new SyntaxErrorInfo
            {
                Id = d.Id,
                Line = Math.Max(1, ls.StartLinePosition.Line + 1 - lineOffset),
                Column = ls.StartLinePosition.Character + 1,
                Message = d.GetMessage()
            };
        }).ToList();

        SemanticModel? semanticModel = null;
        bool semanticAvailable = false;
        try
        {
            var compilation = CSharpCompilation.Create(
                "RoslynPreprocessorAnalysis",
                new[] { tree },
                PlatformReferences.Value,
                new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary));
            semanticModel = compilation.GetSemanticModel(tree, ignoreAccessibility: true);
            semanticAvailable = semanticModel != null;
        }
        catch
        {
            semanticModel = null;
            semanticAvailable = false;
        }

        var methods = new List<MethodAnalysisRecord>();
        foreach (var node in root.DescendantNodes())
        {
            if (node is not BaseMethodDeclarationSyntax methodDecl)
            {
                continue;
            }
            if (methodDecl is not MethodDeclarationSyntax && methodDecl is not ConstructorDeclarationSyntax)
            {
                continue;
            }
            if (methodDecl.Body == null && methodDecl.ExpressionBody == null)
            {
                // Abstract, extern, or interface declaration without implementation body
                continue;
            }

            var (className, typeKind) = ResolveEnclosingTypeChain(methodDecl, snippetMode);
            if (string.IsNullOrWhiteSpace(className))
            {
                continue;
            }

            string methodName = methodDecl switch
            {
                MethodDeclarationSyntax md => md.Identifier.Text,
                ConstructorDeclarationSyntax cd => cd.Identifier.Text,
                _ => string.Empty
            };
            if (string.IsNullOrWhiteSpace(methodName))
            {
                continue;
            }

            string signature = BuildSignature(methodDecl, methodName);
            var lineSpan = methodDecl.GetLocation().GetLineSpan();
            int startLine = Math.Max(1, lineSpan.StartLinePosition.Line + 1 - lineOffset);
            int endLine = Math.Max(startLine, lineSpan.EndLinePosition.Line + 1 - lineOffset);

            bool methodHasErrors = syntaxDiagnostics.Any(d => d.Location.SourceSpan.IntersectsWith(methodDecl.Span));
            string rawSource = methodDecl.ToFullString().Trim('\r', '\n');

            var normResult = NormalizerAndTokenizer.Analyze(methodDecl, normOptions);
            var astMetrics = AstExtractor.Extract(methodDecl);
            var cfgMetrics = CfgExtractor.Extract(methodDecl, semanticModel);
            var dfgMetrics = DfgExtractor.Extract(methodDecl, semanticModel);
            var structMetrics = StructuralExtractor.Extract(methodDecl, astMetrics, cfgMetrics);

            var warnings = new List<string>();
            if (!semanticAvailable) warnings.Add("semantic_model_unavailable");
            if (cfgMetrics.GetValueOrDefault("cfg_succeeded", 0.0) < 0.5) warnings.Add("cfg_analysis_unavailable");
            if (dfgMetrics.GetValueOrDefault("dfg_succeeded", 0.0) < 0.5) warnings.Add("dfg_analysis_unavailable");
            if (methodHasErrors) warnings.Add("method_contains_syntax_errors");

            methods.Add(new MethodAnalysisRecord
            {
                ClassName = className,
                TypeKind = typeKind,
                MethodName = methodName,
                MethodSignature = signature,
                StartLine = startLine,
                EndLine = endLine,
                IsConstructor = methodDecl is ConstructorDeclarationSyntax,
                IsStatic = methodDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.StaticKeyword)),
                IsAsync = methodDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.AsyncKeyword)),
                IsGeneric = methodDecl is MethodDeclarationSyntax mds && mds.TypeParameterList != null,
                IsExpressionBodied = methodDecl.ExpressionBody != null && methodDecl.Body == null,
                HasSyntaxErrors = methodHasErrors,
                RawSource = rawSource,
                NormalizedSource = normResult.NormalizedSource,
                StructuralHash = normResult.StructuralHash,
                TokensNormalized = normResult.TokensNormalized,
                ApiCalls = normResult.ApiCalls,
                LexicalMetrics = normResult.LexicalMetrics,
                AstMetrics = astMetrics,
                CfgMetrics = cfgMetrics,
                DfgMetrics = dfgMetrics,
                StructuralMetrics = structMetrics,
                ExtractionWarnings = warnings
            });
        }

        return new FileAnalysisResponse
        {
            RequestId = request.RequestId,
            Success = syntaxErrors.Count == 0,
            FilePath = request.FilePath,
            HasSyntaxErrors = syntaxErrors.Count > 0,
            SyntaxErrorCount = syntaxErrors.Count,
            SyntaxErrors = syntaxErrors,
            SemanticModelAvailable = semanticAvailable,
            Methods = methods,
            ErrorMessage = syntaxErrors.Count > 0
                ? $"Detected {syntaxErrors.Count} C# syntax error(s)."
                : null
        };
    }

    private static (string className, string typeKind) ResolveEnclosingTypeChain(SyntaxNode node, bool snippetMode)
    {
        var names = new List<string>();
        string outermostKind = "class";
        foreach (var anc in node.Ancestors())
        {
            if (anc is TypeDeclarationSyntax td)
            {
                string id = td.Identifier.Text;
                if (snippetMode && id == DummyContainerName)
                {
                    if (names.Count == 0)
                    {
                        names.Add("SnippetContainer");
                        outermostKind = "class";
                    }
                    continue;
                }
                if (!string.IsNullOrWhiteSpace(id))
                {
                    names.Add(id);
                    outermostKind = td switch
                    {
                        StructDeclarationSyntax => "struct",
                        RecordDeclarationSyntax => "record",
                        _ => "class"
                    };
                }
            }
        }
        names.Reverse();
        return (string.Join(".", names), outermostKind);
    }

    private static string BuildSignature(BaseMethodDeclarationSyntax methodDecl, string methodName)
    {
        var paramTypes = methodDecl.ParameterList.Parameters
            .Select(p => p.Type?.ToString().Trim() ?? "var");
        string typeParams = methodDecl is MethodDeclarationSyntax md && md.TypeParameterList != null
            ? md.TypeParameterList.ToString()
            : string.Empty;
        string returnType = methodDecl is MethodDeclarationSyntax mret
            ? mret.ReturnType.ToString().Trim() + " "
            : string.Empty;
        return $"{returnType}{methodName}{typeParams}({string.Join(", ", paramTypes)})";
    }

    private static List<MetadataReference> LoadPlatformReferences()
    {
        var refs = new List<MetadataReference>();
        try
        {
            if (AppContext.GetData("TRUSTED_PLATFORM_ASSEMBLIES") is string tpa)
            {
                foreach (var path in tpa.Split(Path.PathSeparator))
                {
                    if (!string.IsNullOrWhiteSpace(path) && File.Exists(path))
                    {
                        var name = Path.GetFileName(path);
                        if (name.StartsWith("System.", StringComparison.Ordinal) ||
                            name.StartsWith("Microsoft.CSharp", StringComparison.Ordinal) ||
                            name.Equals("mscorlib.dll", StringComparison.OrdinalIgnoreCase) ||
                            name.Equals("netstandard.dll", StringComparison.OrdinalIgnoreCase))
                        {
                            refs.Add(MetadataReference.CreateFromFile(path));
                        }
                    }
                }
            }
        }
        catch
        {
            // Keep partial compilation if platform references cannot be loaded
        }
        return refs;
    }
}
