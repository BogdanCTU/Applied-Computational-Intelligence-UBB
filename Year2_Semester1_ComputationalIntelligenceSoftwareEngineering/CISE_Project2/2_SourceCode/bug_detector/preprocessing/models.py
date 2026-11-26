"""Typed preprocessing data contracts between RoslynPreprocessor and Python."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SyntaxErrorDetail(BaseModel):
    """Single C# compiler syntax diagnostic."""

    id: str = ""
    line: int = 1
    column: int = 1
    message: str = ""


class MethodAnalysis(BaseModel):
    """Roslyn-extracted C# method representation and feature dictionaries."""

    class_name: str
    type_kind: str = "class"
    method_name: str
    method_signature: str
    start_line: int = 1
    end_line: int = 1
    is_constructor: bool = False
    is_static: bool = False
    is_async: bool = False
    is_generic: bool = False
    is_expression_bodied: bool = False
    has_syntax_errors: bool = False
    raw_source: str = ""
    normalized_source: str = ""
    structural_hash: str = ""
    tokens_normalized: list[str] = Field(default_factory=list)
    api_calls: list[str] = Field(default_factory=list)
    lexical_metrics: dict[str, float] = Field(default_factory=dict)
    ast_metrics: dict[str, float] = Field(default_factory=dict)
    cfg_metrics: dict[str, float] = Field(default_factory=dict)
    dfg_metrics: dict[str, float] = Field(default_factory=dict)
    structural_metrics: dict[str, float] = Field(default_factory=dict)
    extraction_warnings: list[str] = Field(default_factory=list)


class FileAnalysisResult(BaseModel):
    """Complete Roslyn analysis response for a C# file or method snippet."""

    request_id: str | None = None
    success: bool
    file_path: str = "Input.cs"
    has_syntax_errors: bool = False
    syntax_error_count: int = 0
    syntax_errors: list[SyntaxErrorDetail] = Field(default_factory=list)
    semantic_model_available: bool = False
    methods: list[MethodAnalysis] = Field(default_factory=list)
    error_message: str | None = None
