"""Tests for centralized source path classification and production-code filtering."""
from __future__ import annotations

import pytest

from src.utils.source_classifier import (
    classify_source_path,
    is_production_csharp_file,
    is_test_source_path,
    normalize_source_path,
)


class TestSourcePathClassifier:
    """Validate that test code and non-production files are accurately identified and filtered."""

    # 1. Directory conventions
    @pytest.mark.parametrize(
        "path",
        [
            "Tests/ValidatorTests.cs",
            "tests/ValidatorTest.cs",
            "Test/ValidatorTest.cs",
            "test/ValidatorTest.cs",
            "Specs/ValidatorSpecs.cs",
            "specs/ValidatorSpecs.cs",
            "Testing/ValidatorTest.cs",
            "testing/ValidatorTest.cs",
            "tests/Foo.Bar/Baz.cs",
            "tests/Unit/CalculatorTest.cs",
            "test-utils/MockDb.cs",
            "tests_common/TestBase.cs",
        ],
    )
    def test_standard_test_directories_classified_as_test(self, path: str) -> None:
        assert is_test_source_path(path) is True
        assert is_production_csharp_file(path) is False

    # 2. Nested project directory conventions
    @pytest.mark.parametrize(
        "path",
        [
            "src/FluentValidation.Tests/ChainedValidationTester.cs",
            "src/FluentValidation.Tests/TestExtensions.cs",
            "src/FluentValidation.Tests/ValidatorTests.cs",
            "src/FluentValidation.Tests.Benchmarks/BenchmarkTest.cs",
            "src/MediatR.Tests/SendTests.cs",
            "src/MyProject.UnitTests/CoreTest.cs",
            "src/MyProject.IntegrationTests/ApiTest.cs",
            "src/MyProject.Specs/OrderSpecs.cs",
        ],
    )
    def test_nested_project_directories_classified_as_test(self, path: str) -> None:
        assert is_test_source_path(path) is True
        assert is_production_csharp_file(path) is False

    # 3. Filename conventions
    @pytest.mark.parametrize(
        "path",
        [
            "src/Domain/FooTests.cs",
            "src/Domain/FooTest.cs",
            "src/Domain/FooTester.cs",
            "src/Domain/BarSpecs.cs",
            "src/Domain/BarSpec.cs",
            "src/Domain/UserFixture.cs",
            "src/Domain/UserFixtures.cs",
            "src/Domain/foo_test.cs",
            "src/Domain/test_helper.cs",
        ],
    )
    def test_test_filename_conventions_classified_as_test(self, path: str) -> None:
        assert is_test_source_path(path) is True
        assert is_production_csharp_file(path) is False

    # 4. Mixed path separators and case insensitivity
    @pytest.mark.parametrize(
        "path",
        [
            r"src\FluentValidation.Tests\ChainedValidationTester.cs",
            r"TESTS\ValidatorTest.cs",
            r"specs\ValidatorSpecs.CS",
            "SRC/FLUENTVALIDATION.TESTS/FOO.CS",
            r"src\Domain\FooTests.CS",
        ],
    )
    def test_mixed_separators_and_casing(self, path: str) -> None:
        assert is_test_source_path(path) is True
        assert is_production_csharp_file(path) is False

    # 5. Legitimate non-test paths that must NOT be excluded
    @pytest.mark.parametrize(
        "path",
        [
            "src/Contest/ContestManager.cs",
            "src/Contests/ContestEngine.cs",
            "src/Domain/ProgrammingContest.cs",
            "src/TestingInfrastructure/ProductionTestConfiguration.cs",
            "src/Utilities/Tester.cs",
            "src/Utilities/Tester.CS",
            "src/FluentValidation/Validator.cs",
            "src/FluentValidation/DefaultValidatorExtensions.cs",
            "src/FluentValidation/TestHelper/ValidatorTestExtensions.cs",
            "src/FluentValidation/TestHelper/TestValidationResult.cs",
            "src/App/Models/Order.cs",
            "src/Infrastructure/Logging/Logger.cs",
            "src/Security/ProtestHandler.cs",
            "src/Performance/FastestSorter.cs",
        ],
    )
    def test_legitimate_production_paths_are_not_excluded(self, path: str) -> None:
        assert is_test_source_path(path) is False, f"Erroneously flagged as test: {path}"
        assert is_production_csharp_file(path) is True, f"Erroneously rejected as production: {path}"

    # 6. Build and generated files rejection
    @pytest.mark.parametrize(
        "path",
        [
            "obj/Debug/net8.0/Class1.cs",
            r"bin\Release\Class1.cs",
            "src/App/.vs/temp.cs",
            "packages/Newtonsoft.Json/Json.cs",
            "src/App/Form1.Designer.cs",
            "src/App/Component.g.cs",
            "src/App/Temporary.i.cs",
            "src/App/Model.generated.cs",
        ],
    )
    def test_build_and_generated_files_rejected_from_production(self, path: str) -> None:
        assert is_production_csharp_file(path) is False

    # 7. Non-C# files rejection
    @pytest.mark.parametrize(
        "path",
        [
            "README.md",
            "src/App/App.csproj",
            "src/App/Program.py",
            "docs/specification.txt",
        ],
    )
    def test_non_csharp_files_rejected(self, path: str) -> None:
        assert is_production_csharp_file(path) is False

    # 8. Diagnostic classify_source_path output
    def test_classify_source_path_structure(self) -> None:
        res = classify_source_path("src/FluentValidation.Tests/ChainedValidationTester.cs")
        assert res["is_csharp"] is True
        assert res["is_test"] is True
        assert res["is_production"] is False
        assert "test_path_or_filename" in res["reasons"]

        prod_res = classify_source_path("src/FluentValidation/Validator.cs")
        assert prod_res["is_csharp"] is True
        assert prod_res["is_test"] is False
        assert prod_res["is_production"] is True
        assert "valid_production_csharp" in prod_res["reasons"]

