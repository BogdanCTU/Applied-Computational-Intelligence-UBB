using System.Text.Json;
using RoslynPreprocessor.Extractors;
using RoslynPreprocessor.Models;

namespace RoslynPreprocessor;

public static class Program
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = false,
        PropertyNameCaseInsensitive = true
    };

    public static int Main(string[] args)
    {
        if (args.Length == 0)
        {
            Console.Error.WriteLine("Usage: RoslynPreprocessor <analyze-file <path> | analyze-stdin | batch>");
            return 2;
        }

        string command = args[0].ToLowerInvariant();
        return command switch
        {
            "analyze-file" => RunAnalyzeFile(args),
            "analyze-stdin" => RunAnalyzeStdin(),
            "batch" => RunBatch(),
            _ => UnknownCommand(command)
        };
    }

    private static int UnknownCommand(string command)
    {
        Console.Error.WriteLine($"Unknown command: {command}");
        return 2;
    }

    private static int RunAnalyzeFile(string[] args)
    {
        if (args.Length < 2)
        {
            Console.Error.WriteLine("Missing file path.");
            return 2;
        }
        string path = args[1];
        if (!File.Exists(path))
        {
            var err = new FileAnalysisResponse
            {
                Success = false,
                FilePath = path,
                ErrorMessage = $"File not found: {path}"
            };
            Console.WriteLine(JsonSerializer.Serialize(err, JsonOptions));
            return 1;
        }

        var req = new FileAnalysisRequest
        {
            Mode = "file",
            FilePath = path,
            SourceCode = File.ReadAllText(path)
        };
        var resp = MethodExtractor.Analyze(req);
        Console.WriteLine(JsonSerializer.Serialize(resp, JsonOptions));
        return 0;
    }

    private static int RunAnalyzeStdin()
    {
        string raw = Console.In.ReadToEnd();
        var req = JsonSerializer.Deserialize<FileAnalysisRequest>(raw, JsonOptions);
        if (req == null)
        {
            Console.Error.WriteLine("Invalid JSON request.");
            return 1;
        }
        var resp = MethodExtractor.Analyze(req);
        Console.WriteLine(JsonSerializer.Serialize(resp, JsonOptions));
        return 0;
    }

    private static int RunBatch()
    {
        string? line;
        while ((line = Console.In.ReadLine()) != null)
        {
            if (string.IsNullOrWhiteSpace(line))
            {
                continue;
            }
            FileAnalysisResponse resp;
            try
            {
                var req = JsonSerializer.Deserialize<FileAnalysisRequest>(line, JsonOptions);
                if (req == null)
                {
                    resp = new FileAnalysisResponse
                    {
                        Success = false,
                        ErrorMessage = "Deserialized null request."
                    };
                }
                else
                {
                    resp = MethodExtractor.Analyze(req);
                }
            }
            catch (Exception ex)
            {
                resp = new FileAnalysisResponse
                {
                    Success = false,
                    ErrorMessage = $"Batch item error: {ex.Message}"
                };
            }
            Console.WriteLine(JsonSerializer.Serialize(resp, JsonOptions));
            Console.Out.Flush();
        }
        return 0;
    }
}
