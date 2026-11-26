"""C# source-code preprocessing, normalization, and Roslyn integration."""

from bug_detector.preprocessing.models import (
    FileAnalysisResult,
    MethodAnalysis,
    SyntaxErrorDetail,
)
from bug_detector.preprocessing.normalizer import (
    normalize_whitespace_hash,
    python_fallback_tokenize,
)
from bug_detector.preprocessing.roslyn_bridge import RoslynPreprocessorClient

__all__ = [
    "FileAnalysisResult",
    "MethodAnalysis",
    "RoslynPreprocessorClient",
    "SyntaxErrorDetail",
    "normalize_whitespace_hash",
    "python_fallback_tokenize",
]
