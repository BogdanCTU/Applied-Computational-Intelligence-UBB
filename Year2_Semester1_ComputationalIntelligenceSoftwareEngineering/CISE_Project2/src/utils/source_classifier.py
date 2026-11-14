"""Centralized source code path classification and production filtering.

Distinguishes production C# source files from test-related files, test fixtures,
specifications, and build/generated artifacts with high precision.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

# Exact directory names that signify test code
EXACT_TEST_DIR_NAMES: Set[str] = {
    "test",
    "tests",
    "spec",
    "specs",
    "testing",
    "testfixture",
    "testfixtures",
    "unittest",
    "unittests",
    "integrationtest",
    "integrationtests",
    "functionaltest",
    "functionaltests",
    "e2etest",
    "e2etests",
}

# Directory suffixes that signify test projects (e.g., FluentValidation.Tests)
TEST_PROJECT_DIR_SUFFIXES = (
    ".tests",
    ".test",
    ".specs",
    ".spec",
    ".unittests",
    ".unittest",
    ".integrationtests",
    ".integrationtest",
    ".functionaltests",
    ".functionaltest",
)

# Build and IDE directory names that are never production source
BUILD_OR_TOOLING_DIR_NAMES: Set[str] = {
    "obj",
    "bin",
    ".vs",
    "packages",
    ".git",
    ".github",
    ".idea",
    "node_modules",
    "artifacts",
    "testresults",
}

# Suffixes for auto-generated C# files
GENERATED_FILE_SUFFIXES = (
    ".designer.cs",
    ".g.cs",
    ".i.cs",
    ".generated.cs",
    ".assemblyattributes.cs",
)

# Legitimate English words that end in 'test' / 'tests' / 'tester' but are NOT defect-test classes
KNOWN_NON_TEST_WORDS: Set[str] = {
    "tester",
    "contest",
    "contests",
    "protest",
    "protests",
    "attest",
    "attests",
    "detest",
    "detests",
    "latest",
    "fastest",
    "smartest",
    "greatest",
    "fittest",
    "neatest",
    "sweetest",
}

# Compound words ending in non-test roots
KNOWN_NON_TEST_COMPOUND_ENDINGS = (
    "contest",
    "contests",
    "protest",
    "protests",
    "attest",
    "attests",
    "detest",
    "detests",
)


def normalize_source_path(file_path: Union[str, Path]) -> str:
    """Normalize file path to use forward slashes and strip leading prefixes."""
    if not file_path:
        return ""
    p = str(file_path).replace("\\", "/").strip()
    # Strip leading ./ if present
    while p.startswith("./"):
        p = p[2:]
    return p


def is_test_source_path(file_path: Union[str, Path]) -> bool:
    """Determine whether a file path points to a test source file or test directory.

    Returns True for:
      - Directories named Tests/, Test/, Specs/, Spec/, Testing/, etc.
      - Project directories ending in .Tests, .Test, .Specs, etc. (e.g. src/FluentValidation.Tests/)
      - Test filenames such as FooTests.cs, FooTest.cs, FooTester.cs, BarSpecs.cs.
      - Case-insensitive variants and mixed forward/backward slashes.

    Returns False for legitimate non-test files and directories such as:
      - src/Contest/ContestManager.cs
      - src/TestingInfrastructure/ProductionTestConfiguration.cs
      - src/Utilities/Tester.cs (in non-test directory)
      - src/FluentValidation/TestHelper/ValidatorTestExtensions.cs (production NuGet helper)
    """
    normalized = normalize_source_path(file_path)
    if not normalized:
        return False

    parts = [part for part in normalized.split("/") if part and part != "."]
    if not parts:
        return False

    # Check directory segments
    dir_segments = parts[:-1] if "." in parts[-1] else parts
    for seg in dir_segments:
        seg_lower = seg.lower()

        # 1. Exact match on test directory name
        if seg_lower in EXACT_TEST_DIR_NAMES:
            return True

        # 2. Suffix match for C# test project directory convention (.Tests, .Specs, etc.)
        if seg_lower.endswith(TEST_PROJECT_DIR_SUFFIXES):
            return True

        # 3. Intermediate project naming (e.g., FluentValidation.Tests.Benchmarks)
        if re.search(r"\.(?:tests?|specs?|unittests?|integrationtests?)\.", seg_lower):
            return True

        # 4. Folder starting with test- or test_
        if seg_lower.startswith(("test-", "test_", "tests-", "tests_")):
            return True

    # If the path only represents a directory, we have completed checking directories
    if "." not in parts[-1]:
        return False

    # Check filename
    filename = parts[-1]
    filename_lower = filename.lower()

    if not filename_lower.endswith(".cs"):
        return False

    base = filename_lower[:-3]  # strip .cs

    # Whitelist check: Standalone legitimate words (Tester.cs, Contest.cs)
    if base in KNOWN_NON_TEST_WORDS:
        return False

    # Compound check: Non-test roots like MathContest.cs, CityProtest.cs
    if base.endswith(KNOWN_NON_TEST_COMPOUND_ENDINGS):
        return False

    # Test filename conventions:
    # 1. Exact base name: Test.cs, Tests.cs, Spec.cs, Specs.cs
    if base in {"test", "tests", "spec", "specs", "fixture", "fixtures"}:
        return True

    # 2. Suffix conventions: FooTests.cs, FooSpecs.cs, FooFixture.cs, FooFixtures.cs
    if base.endswith(("tests", "specs", "fixture", "fixtures")):
        return True

    # 3. FooTest.cs or FooSpec.cs
    if base.endswith("test") or base.endswith("spec"):
        return True

    # 4. FooTester.cs (where base is longer than 'tester', e.g. ChainedValidationTester.cs)
    if base.endswith("tester") and len(base) > 6:
        return True

    # 5. Separator conventions: foo_test.cs, foo.spec.cs, foo-test.cs
    if re.search(r"[._-](?:tests?|specs?|tester|fixtures?)$", base):
        return True

    # 6. Prefix conventions: test_validator.cs, spec_order.cs
    if base.startswith(("test_", "tests_", "spec_", "specs_")):
        return True

    return False


def is_production_csharp_file(file_path: Union[str, Path]) -> bool:
    """Determine whether a file path is a legitimate production C# source file.

    Enforces that:
      1. File extension is .cs (case-insensitive).
      2. File is not inside build/tooling/temp directories (obj/, bin/, .vs/, packages/).
      3. File is not an auto-generated C# file (.Designer.cs, .g.cs, .generated.cs).
      4. File is not a test file, test project, or test fixture.
    """
    normalized = normalize_source_path(file_path)
    if not normalized:
        return False

    if not normalized.lower().endswith(".cs"):
        return False

    parts = [part for part in normalized.split("/") if part and part != "."]
    if not parts:
        return False

    dir_segments = parts[:-1]
    filename = parts[-1].lower()

    # Check for build or tooling directories
    for seg in dir_segments:
        if seg.lower() in BUILD_OR_TOOLING_DIR_NAMES:
            return False

    # Check for auto-generated files
    if any(filename.endswith(suffix) for suffix in GENERATED_FILE_SUFFIXES):
        return False

    # Check if classified as a test file
    if is_test_source_path(normalized):
        return False

    return True


def classify_source_path(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Provide a full diagnostic classification of a source path for auditing."""
    normalized = normalize_source_path(file_path)
    is_cs = normalized.lower().endswith(".cs")
    is_test = is_test_source_path(normalized)
    is_prod = is_production_csharp_file(normalized)

    parts = [part for part in normalized.split("/") if part and part != "."]
    dir_segments = parts[:-1] if parts else []
    filename = parts[-1].lower() if parts else ""

    is_build = any(seg.lower() in BUILD_OR_TOOLING_DIR_NAMES for seg in dir_segments)
    is_gen = any(filename.endswith(s) for s in GENERATED_FILE_SUFFIXES)

    reasons: List[str] = []
    if not is_cs:
        reasons.append("non_csharp_extension")
    if is_build:
        reasons.append("build_or_tooling_directory")
    if is_gen:
        reasons.append("auto_generated_code")
    if is_test:
        reasons.append("test_path_or_filename")
    if is_prod:
        reasons.append("valid_production_csharp")

    return {
        "file_path": str(file_path),
        "normalized_path": normalized,
        "is_csharp": is_cs,
        "is_build_directory": is_build,
        "is_generated": is_gen,
        "is_test": is_test,
        "is_production": is_prod,
        "reasons": reasons,
    }

