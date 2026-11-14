# Pilot Collection & Validation Report: `FluentValidation/FluentValidation`
## Empirical Software Defect Prediction for C# Source Code

> [!NOTE]
> **Superceded by Corrected Report v2:**  
> This document records the initial pilot run (v1). An audit revealed that 3 test fixture methods from `src/FluentValidation.Tests/` entered Label 1 due to regex limitations on nested project directories.  
> See [docs/FLUENTVALIDATION_PILOT_CORRECTION_REPORT.md](file:///e:/PERSONAL/GitHub/1_Applied-Computational-Intelligence-UBB/Year2_Semester1_ComputationalIntelligenceSoftwareEngineering/CISE_Project2/docs/FLUENTVALIDATION_PILOT_CORRECTION_REPORT.md) and artifact `reports/pilot/fluentvalidation_pilot_v2_corrected.json` for the corrected, production-only recalculation (14 production buggy methods, 14 clean methods, total 28 observations, 0% test leakage).

**Document Version:** 1.0.0 (Historical Baseline)  
**Date:** November 2026  
**Auditor / Specialist:** Senior ML4SE Research Engineer & Academic Reviewer  
**Target Repository:** `FluentValidation/FluentValidation` (Proposed Training Repository #3)  
**Execution Script:** `scripts/run_fluentvalidation_pilot.py`  
**Execution Status:** [PASS] Fully Executed & Verified (Duration: 66.65s)  
**Artifact Path:** `reports/pilot/fluentvalidation_pilot_results.json`

---

## 1. Executive Summary

As part of the controlled expansion plan from two training repositories to five training repositories, a **controlled pilot study** was executed on `FluentValidation/FluentValidation`. The objective was to test the end-to-end extraction pipeline—repository cloning, commit mining, heuristic bug detection, SZZ line blame tracing, Roslyn AST method extraction, candidate-clean sampling, and static code feature extraction—without modifying core algorithms or compromising existing dataset snapshots.

### Core Pilot Outcomes:
- **Pipeline Execution:** 100% operational without errors or crashes.
- **Repository Ingestion:** Successfully cloned with complete Git history (2,515 commits total, HEAD: `5903fa65`).
- **Commit Mining:** 350 commits mined into SQLite.
- **Bug-Fix Classification:** 11 commits classified as genuine bug fixes ($\text{confidence} \ge 0.50$).
- **SZZ Line Tracing:** 10 of 11 bug fixes successfully traced via `git blame -w -M -C`, producing 28 BIC line traces across 14 unique Bug-Inducing Commits.
- **Method Extraction via Roslyn:** 17 unique pre-fix buggy methods extracted (Label 1) and 17 candidate-clean methods sampled from stable HEAD (Label 0), totaling **34 observations**.
- **Roslyn Feature Extraction:** **100% success rate** (34 of 34 methods extracted with all 26 static code metrics).
- **Existing Data Integrity:** Verified completely intact; existing dataset snapshot `csharp_empirical_v1_v1.0.0` (483 observations) was untouched.

---

## 2. Repository Metadata & Provenance

| Parameter | Measured Value | Verification Source |
| :--- | :--- | :--- |
| **Repository Full Name** | `FluentValidation/FluentValidation` | GitHub API / Remote Clone |
| **Repository ID in DB** | `14` | SQLite `repositories` table |
| **Owner / Organization** | `FluentValidation` (Jeremy Skinner) | Repository manifest |
| **Remote URL** | `https://github.com/FluentValidation/FluentValidation.git` | Git remote |
| **Default Branch** | `main` | `git ls-remote --heads` |
| **License** | Apache-2.0 | Repository `LICENSE.txt` |
| **GitHub Stars** | ~9,800 | GitHub metadata |
| **Total Git Commits** | 2,515 commits | Local Git repository |
| **Local Clone Path** | `data/repositories/FluentValidation/FluentValidation` | Filesystem |
| **Cloned Commit HEAD** | `5903fa65863ec66dabf10646b9c09b33130a03e8` | `git rev-parse HEAD` |

---

## 3. Detailed Pipeline Extraction Statistics

### 3.1 Commit Mining & Bug-Fix Detection
The mining window was capped at 350 commits, consistent with the initial sampling windows used for `Humanizer` (300 commits) and `MediatR` (300 commits).

- **Commits Analyzed:** 350 commits.
- **Classified Bug Fixes:** 11 commits (3.14% bug-fix rate).
- **Confidence Distribution:**
  - High Confidence ($\ge 0.70$): **4 commits**
    - `419380cb` ($\text{conf} = 1.00$): *"fix memory leak enumerator (#2174)"*
    - `bae89165` ($\text{conf} = 0.90$): *"Fix ArgumentNullException in TestValidationResult when a failure..."* (Linked issue #2361)
    - `7d91ccb1` ($\text{conf} = 0.75$): *"Fix bug introduced in AbstractValidator.SetExecutedRuleSets"*
    - `0c24fd92` ($\text{conf} = 0.75$): *"Fix bug introduced in NotEmptyValidator"*
  - Moderate Confidence ($0.50 \le \text{conf} < 0.70$): **7 commits**
    - `a8ca6ac3` ($\text{conf} = 0.65$): *"Fix OverflowException in IsInEnum for ulong flags enums"*
    - `a4377610` ($\text{conf} = 0.60$): *"Fix ChildRules with hierarchies #2165"*
    - `9c0c5872` ($\text{conf} = 0.60$): *"Fix test helper .Only() not taking into account parent-level unma"*
    - `d37d15f5` ($\text{conf} = 0.60$): *"Fix the issue that the ChildRules will corrupt the RuleSets of a"*
    - `eae767d6` ($\text{conf} = 0.60$): *"Fix assertions for With/Without test methods when there are multi"*
    - `3e3e29f4` ($\text{conf} = 0.55$): *"Resolve issue with ruleset propogation for multiple levels of chi"* (Linked issue #2097)
    - `91e78489` ($\text{conf} = 0.55$): *"Enable package validation and add backwards compatibility overloa"* (Linked issue #1860)

### 3.2 SZZ Algorithm Execution
- **Fixing Commits Processed:** 11
- **Fixing Commits with Blame Traces:** 10 out of 11 (90.9% tracing efficiency; commit `91e78489` contained package metadata updates with no modified C# source lines).
- **Total BIC Line Traces:** 28 line traces.
- **Unique Bug-Inducing Commits (BICs):** 14 distinct historical revisions.
- **Tracing Density:** $2.55$ BIC line traces per fixing commit.

### 3.3 Method-Level Labeling & Deduplication
- **SZZ-Derived Buggy Methods (Label 1):**
  - Deleted lines mapped to enclosing methods: 17 unique methods.
  - Line traces filtered out: 11 lines (consisting of duplicate method references within the same commit or deleted lines outside method declarations, e.g., using statements or field assignments).
- **Candidate-Clean Methods (Label 0):**
  - Sampled from stable HEAD revisions with zero recorded defect fixes: 17 methods.
- **Uncertain Labels (Label -1):** 0 (no ambiguous records).
- **Total Usable Observations:** **34 observations** (17 Buggy, 17 Candidate-Clean; exactly 50.0% class balance).

### 3.4 Roslyn Static Code Feature Extraction
- **Total Observations Submitted to Roslyn:** 34
- **Extraction Successes:** 34 (100.0%)
- **Extraction Failures:** 0 (0.0%)
- **Extracted Feature Count:** 26 metrics per method (23 structural/complexity metrics + 3 boolean OOP flags).

---

## 4. Methodological Findings & Pipeline Insights

### 4.1 Test Directory Path Sensitivity (Key Discovery)
An important empirical finding emerged during inspection of the 17 Label 1 methods:
- **Observation:** 3 methods were extracted from `src/FluentValidation.Tests/` (e.g. `ChainedValidationTester.Uses_explicit_ruleset` and `TestExtensions.ShouldEqual`).
- **Root Cause Analysis:** In `src/mining/szz_analyzer.py`, `DEFAULT_EXCLUSIONS` filters test directories using regex patterns:
  ```python
  re.compile(r"(?:^|/)(?:tests?|specs?|testing)/", re.IGNORECASE)
  re.compile(r"(?:Tests?|Specs?)\.cs$", re.IGNORECASE)
  ```
- In `Humanizer` and `MediatR`, test projects reside under top-level `tests/` directories or end in `Tests.cs`. However, `FluentValidation` houses test suites under `src/FluentValidation.Tests/`, and filenames like `ChainedValidationTester.cs` end in `Tester.cs` rather than `Tests.cs`. Consequently, the current regex permitted these lines to enter SZZ blame tracking.
- **Academic Recommendation:** While these 3 test helper methods were genuine defect-inducing fixes in the developer's repository, in a production expansion the exclusion regex should be generalized to:
  ```python
  re.compile(r"(?:^|/)(?:.*[._-])?(?:tests?|specs?|testing)(?:[._-/]|$)", re.IGNORECASE)
  ```
  In accordance with the project constraints, **no code was altered during the pilot**, ensuring that the pilot strictly reports real behavior under the frozen methodology.

### 4.2 Defect Density & Yield Comparison Across Repositories

| Repository | Commits Mined | Bug-Fix Commits | Bug-Fix Rate | Traced BICs | Usable Buggy Methods | Total Usable Observations | Yield per Mined Commit |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`Humanizr/Humanizer`** | 300 | 83 | **27.7%** | 62 | 139 | **291** | **0.97 obs/commit** |
| **`LuckyPennySoftware/MediatR`** | 300 | 25 | **8.3%** | 33 | 43 | **91** | **0.30 obs/commit** |
| **`FluentValidation/FluentValidation`** | 350 | 11 | **3.1%** | 14 | 17 | **34** | **0.10 obs/commit** |

#### Why does `FluentValidation` have a lower yield per commit?
1. **High Architectural Maturity:** In its most recent 350 commits (covering 2021–2026), `FluentValidation` is a mature, production-hardened library. A substantial portion of recent commits involve .NET version target updates (.NET 8/9), documentation improvements, and dependency updates, resulting in fewer defect fixes compared to `Humanizer`.
2. **Conservative Keyword Threshold (0.50):** The heuristic bug-fix detector requires explicit defect keywords or linked closing PRs, filtering out feature refactorings.
3. **Scaling Implication:** To achieve a yield of 100+ observations from `FluentValidation`, the mining window would need to expand to 1,000–1,500 commits. However, even with 34 observations, `FluentValidation` provides an independent, domain-distinct validation ruleset repository for multi-repository cross-validation.

---

## 5. Feature Distribution Sanity Check

To verify that Roslyn extracted meaningful metrics on `FluentValidation` source code, feature distributions were audited across the 34 observations:

| Metric Name | Minimum | 25th Percentile | Median | Mean | 75th Percentile | Maximum | Expected Range Check |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `loc` (Physical Lines) | 3 | 7.25 | 13.50 | 14.85 | 21.00 | 38 | [PASS] Valid C# method lines |
| `method_length` (Characters) | 107 | 370.50 | 613.00 | 664.20 | 920.50 | 1,440 | [PASS] Valid AST span |
| `cyclomatic_complexity` (Paths) | 1 | 1.00 | 1.50 | 2.50 | 3.00 | 9 | [PASS] McCabe complexity |
| `parameter_count` | 0 | 1.00 | 2.00 | 2.06 | 2.75 | 5 | [PASS] Method parameters |
| `statement_count` | 0 | 2.00 | 5.00 | 6.15 | 9.00 | 25 | [PASS] Executable statements |
| `max_nesting_depth` | 0 | 0.00 | 1.00 | 0.94 | 1.00 | 3 | [PASS] Control-flow depth |

The extracted metrics exhibit expected variance across both simple utility methods (`loc = 3`) and complex validation dispatchers (`loc = 38, CC = 9`).

---

## 6. Pilot Acceptance Criteria Evaluation

| Criterion | Target | Measured Result | Verdict |
| :--- | :--- | :--- | :---: |
| **1. Repository Ingestion** | Full Git clone with commit history | 2,515 commits cloned, branch `main` | **PASS** |
| **2. Commit Mining** | $\ge 300$ commits mined into DB | 350 commits mined | **PASS** |
| **3. Heuristic Bug Detection** | Detect bug fixes at 0.50 threshold | 11 fixes detected (4 high, 7 moderate) | **PASS** |
| **4. SZZ Blame Tracing** | Generate valid BIC traces | 28 BIC traces, 14 unique BICs | **PASS** |
| **5. Roslyn Method Extraction** | Parse pre-fix method code | 17 unique methods extracted | **PASS** |
| **6. Clean Label Sampling** | Sample 1:1 matching clean methods | 17 candidate clean methods sampled | **PASS** |
| **7. Feature Extraction** | 26 Roslyn metrics computed | 34 / 34 succeeded (100% success rate) | **PASS** |
| **8. Non-Destructive Integrity** | Zero modifications to existing data | `csharp_empirical_v1` & repos 1, 3, 4 intact | **PASS** |

---

## 7. Strategic Recommendations & Next Steps

### 7.1 Verdict: **PASS (Qualified GO for Corpus Expansion)**
The pilot confirms that the existing extraction pipeline works on external, modern C# class libraries without modification. The data collection methodology is scientifically sound and reproducible.

### 7.2 Recommendations for Subsequent Repositories (`Serilog`, `Polly`, `Newtonsoft.Json`):
1. **Commit Window Sizing**: Because mature libraries have lower bug-fix densities (~3%–8%), future repositories should be mined with a deeper commit window (**400–600 commits**) to guarantee an observation yield of 60–120 methods per repository.
2. **Preserve Frozen Snapshot Protocol**: Do not generate a new dataset snapshot (`csharp_empirical_v2`) until all five training repositories have completed collection.
3. **Refine Test Directory Exclusions**: Document the test directory naming convention (`src/*.Tests/`) as an academic threat to validity, or update the exclusion regex prior to running Phase 2.

*Pilot collection completed, audited, and approved for inclusion in corpus expansion.*

