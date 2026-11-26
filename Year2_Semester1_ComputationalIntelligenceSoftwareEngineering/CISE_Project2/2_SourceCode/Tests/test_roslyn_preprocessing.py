"""Tests for Roslyn C# preprocessing, method extraction, normalization, and syntax error guards."""

from __future__ import annotations

from pathlib import Path

from bug_detector.config import NormalizationConfig
from bug_detector.preprocessing import RoslynPreprocessorClient


def test_roslyn_extracts_diverse_csharp_constructs(fixtures_dir: Path) -> None:
    with RoslynPreprocessorClient() as client:
        res = client.analyze_file_path(fixtures_dir / "diverse_constructs.cs")

    assert res.success is True
    assert res.has_syntax_errors is False
    names = {(m.class_name, m.method_name) for m in res.methods}
    assert ("Point2D", "Point2D") in names  # struct constructor
    assert ("Point2D", "Magnitude") in names  # struct expression-bodied method
    assert ("AuditEntry", "Format") in names  # record method
    assert ("OuterService", "Identity") in names  # static generic method
    assert ("OuterService", "ComputeAsync") in names  # async method
    assert ("OuterService.NestedHelper", "IsPositive") in names  # nested class method
    overloads = [m for m in res.methods if m.method_name == "Overload"]
    assert len(overloads) == 2
    assert overloads[0].method_signature != overloads[1].method_signature
    for m in res.methods:
        assert m.start_line >= 1
        assert m.end_line >= m.start_line


def test_roslyn_flags_malformed_syntax(fixtures_dir: Path) -> None:
    with RoslynPreprocessorClient() as client:
        res = client.analyze_file_path(fixtures_dir / "malformed_syntax.cs")
    assert res.success is False
    assert res.has_syntax_errors is True
    assert res.syntax_error_count >= 1


def test_roslyn_normalization_preserves_special_literals_and_apis() -> None:
    src = """
    public class Calc {
        public int Run(string input) {
            // Comment that should be stripped
            if (input == null) return 0;
            int count = 42;
            string tag = "secret_literal";
            return input.Trim().Length + count;
        }
    }
    """
    with RoslynPreprocessorClient() as client:
        res_abs = client.analyze_source(src, "Calc.cs", normalization=NormalizationConfig(abstract_string_literals=True, abstract_numeric_literals=True))
        res_raw = client.analyze_source(src, "Calc.cs", normalization=NormalizationConfig(abstract_string_literals=False, abstract_numeric_literals=False))

    m_abs = res_abs.methods[0]
    m_raw = res_raw.methods[0]
    assert "null" in m_abs.tokens_normalized
    assert "0" in m_abs.tokens_normalized
    assert "<NUM>" in m_abs.tokens_normalized
    assert "<STR>" in m_abs.tokens_normalized
    assert "42" in m_raw.tokens_normalized
    assert any("Trim" in api for api in m_abs.api_calls)
