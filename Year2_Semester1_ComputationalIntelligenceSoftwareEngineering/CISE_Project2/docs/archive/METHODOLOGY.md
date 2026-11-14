# Methodology Document: Machine Learning-Based Software Bug Detection for C#

## 1. Problem Statement

Software bugs cause system instability, security vulnerabilities, and significant economic overhead. Traditional quality assurance relies on manual code reviews and static analysis rule sets, which often generate high false positive rates or fail to capture complex structural interactions.

Machine learning, specifically Supervised Random Forest Classification, provides an empirical, data-driven approach by learning non-linear structural patterns from historical defect distributions across real-world software repositories.

## 2. Research Questions (RQs)

- **RQ1 (Feasibility)**: Can method-level static code metrics derived via Roslyn AST accurately distinguish buggy from non-buggy C# methods?
- **RQ2 (Generalizability)**: Does the Random Forest classifier maintain predictive performance when tested on repositories unseen during training (Repository-Level GroupKFold)?
- **RQ3 (Feature Relevance)**: Which structural and complexity metrics contribute most significantly to defect proneness in C#?

---

## 3. Bug-Fixing Commit Detection Methodology

Bug-fixing commits are detected using a multi-source heuristic classifier (`src/mining/bug_fix_detector.py`):

1. **Issue and PR Reference Linkage**:
   - Matches action patterns: `fixes #123`, `resolves gh-45`, `closes issue #789`.
   - Explicit issue closures provide high base confidence ($\ge 0.55$).
2. **Defect Keyword Heuristics**:
   - Matches core defect indicators: `bug`, `fix`, `defect`, `regression`, `crash`, `exception`, `nullreference`, `deadlock`, `race condition`.
3. **False-Positive Penalties**:
   - Filters out cosmetic and documentation modifications (`typo`, `formatting`, `stylecop`, `readme`, `docs`).
   - Penalizes commits that do not modify any `.cs` files ($-0.35$).
   - Penalizes massive bulk refactorings (>30 files changed, $-0.25$).
4. **Confidence Thresholding & Manual Review**:
   - Default classification threshold is set to $\ge 0.50$.
   - Commits can be manually audited, confirmed, or rejected via the Streamlit UI, persisting review statuses (`confirmed`, `rejected`, `unreviewed`).

---

## 4. Ground Truth Generation: The SZZ Algorithm

Ground truth defect labels are extracted from Git commit histories using an enhanced SZZ (Śliwerski–Zimmermann–Zeller) approach implemented in `src/mining/szz_analyzer.py`:

```
[Bug-Fixing Commit (BFC)]
         │
         ▼ (Diff against mainline parent; filter comments & whitespace)
[Deleted / Modified Lines in C# Methods]
         │
         ▼ (git blame -w -M -C --porcelain)
[Candidate Bug-Inducing Commit (BIC)]
         │
         ▼ (Roslyn AST Enclosing Method Locator)
[Pre-Fix Method State: Label 1] <---> [Corrected Method State]
```

### SZZ Pipeline Steps:
1. **Parent-Selection Strategy**: For merge commits with multiple parents, SZZ diffs against `parents[0]` (the mainline parent). This isolates the defect modifications integrated into the target branch.
2. **Line-Level Diff Extraction**: Unified diff hunks are parsed. Deleted lines (`-`) represent pre-fix defective statements.
3. **Noise & Cosmetic Filtering**:
   - Empty lines and pure whitespace changes are ignored.
   - Comment lines (`//`, `/*`, `*`) are stripped.
   - Isolated structural tokens (`{`, `}`, `;`) are omitted.
4. **Git Blame with Move & Copy Detection**:
   - Executes `git blame -w -M -C --porcelain` on the pre-fix parent commit.
   - Traces each deleted statement back to the exact revision that introduced it.
   - Prevents self-referencing links (`inducing_commit != fixing_commit`).
5. **Method Enclosing Boundary Resolution**:
   - Using Microsoft Roslyn AST (`CSharpSyntaxTree`), locates the exact C# method enclosing the blamed line.
   - Extracts the complete pre-fix method body and matches it with the post-fix corrected method.

---

## 5. Labeling Taxonomy & Semantics

The atomic unit of observation in this system is an individual **C# method**:

| Label | Meaning | Evidence Source & Criteria |
| :---: | :--- | :--- |
| **`1`** | **Confirmed / Candidate Buggy** | Method enclosing lines modified in a bug fix, traced via SZZ to a Bug-Inducing Commit. Pre-fix buggy code is extracted. |
| **`0`** | **Candidate Non-Buggy** | Sampled from stable repository tags/HEAD where the method was untouched by any bug-fixing commit throughout its history. |
| **`-1`** | **Uncertain / Ambiguous** | Ambiguous commit messages, massive refactoring revisions, or unblamable line traces. Excluded from supervised training. |

---

## 6. Threats to Validity & Academic Limitations

1. **Construct Validity (SZZ as Candidate, Not Ground Truth)**:
   - SZZ identifies *candidate* bug-inducing commits based on line modification history. In empirical literature, lines changed during bug fixes sometimes include incidental refactorings or cosmetic cleanup. SZZ results are treated as risk indicators and candidate defect labels rather than absolute proof.
2. **Negative Label Validity (Candidate Clean vs Bug-Free)**:
   - Absence of defect reports does not prove that code is bug-free (unknown or latent bugs may remain). We explicitly document Label `0` as *Candidate Non-Buggy* rather than definitively defect-free.
3. **Internal Validity (Data Leakage)**:
   - Random method splitting allows code from the same repository to appear in both training and test sets. We enforce **`GroupKFold`** grouped strictly by repository identity.
4. **External Validity**:
   - Language idioms (LINQ, async/await, nullable reference types) are specific to C#. Results generalize across enterprise and open-source C# projects but may not directly transfer to dynamically typed languages.
