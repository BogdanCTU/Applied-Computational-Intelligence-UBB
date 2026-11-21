# Historical Research Archive & Audit Provenance

This directory contains historical research reports, interim development audits, baseline specifications, and pilot assessments produced during the progression of CISE Project 2 (*Machine Learning-Based Software Defect Prediction for C# Source Code*).

These documents are preserved for full research reproducibility, experimental chronology, and audit provenance. They are superseded by the active canonical documentation suite in `docs/`:

- 📄 **[FINAL_REPORT.md](../07_AcademicReport/FINAL_REPORT.md)** — The Authoritative Academic Research Report
- 🛠️ **[PROJECT_METHODOLOGY.md](../04_MachineLearning/PROJECT_METHODOLOGY.md)** — Canonical Technical Methodology & Data Engineering Reference
- 📊 **[EXPERIMENTAL_RESULTS.md](../04_MachineLearning/EXPERIMENTAL_RESULTS.md)** — Consolidated Empirical Multi-Model Results
- ⚖️ **[VALIDATION_AND_LIMITATIONS.md](../05_Validation/VALIDATION_AND_LIMITATIONS.md)** — Software Verification, Empirical Validation & Limitations
- 📋 **[DEVELOPER_STUDY_TEMPLATE.md](../07_AcademicReport/DEVELOPER_STUDY_TEMPLATE.md)** — Formal 24-Method Double-Blind Research Protocol Instrument

---

## Catalog of Archived Documents

### 1. Final Submission & Completion Audits
- **`FINAL_SUBMISSION_READINESS_AUDIT.md`**: Comprehensive read-only audit verifying all six university requirements, dataset integrity, cross-validation metrics, frozen models, and holdout performance.
- **`PROJECT_COMPLETION_AUDIT.md`**: Architectural and requirement completion audit across phases.
- **`PROJECT_COMPLETION_BASELINE.md`**: Baseline inventory prior to final project completion.

### 2. Experimental & Dataset Integrity Audits
- **`FINAL_DATASET_INTEGRITY_AUDIT.md`**: In-depth reconciliation of database records, commit histories, SZZ traces, and observation counts.
- **`FINAL_EXPERIMENTAL_AUDIT.md`**: Historical audit of Phase 3 model training, GroupKFold cross-validation, and leakage prevention.
- **`FINAL_EXPERIMENTAL_RESULTS.md`**: Interim report on the 5-fold cross-validation benchmark (superseded by `EXPERIMENTAL_RESULTS.md`).
- **`INDEPENDENT_VALIDATION_REPORT.md`**: Interim report on the `Newtonsoft.Json` holdout evaluation (superseded by `EXPERIMENTAL_RESULTS.md` and `VALIDATION_AND_LIMITATIONS.md`).

### 3. Pilot Studies & Dataset Expansion Assessments
- **`FLUENTVALIDATION_PILOT_REPORT.md`**: Initial exploratory pilot collection on `FluentValidation/FluentValidation`.
- **`FLUENTVALIDATION_PILOT_CORRECTION_REPORT.md`**: Methodological correction resolving test-file contamination and implementing production filtering.
- **`DATASET_EXPANSION_ASSESSMENT.md`**: Feasibility and repository candidate assessment for multi-repository expansion.
- **`DATASET_EXPANSION_FINAL_REPORT.md`**: Execution summary of expanding the dataset to 5 training repositories ($N=578$).
- **`ACADEMIC_METHODOLOGY_REVIEW.md`**: Methodological audit establishing rigorous SZZ terminology and leakage controls.
- **`DEVELOPER_FEEDBACK_REPORT.md`**: Qualitative analysis of prediction cases and disclosure of study status.

### 4. Superseded Early Architecture & Specifications
The following early design specifications have been consolidated into `PROJECT_METHODOLOGY.md`:
- **`ARCHITECTURE.md`**: Initial high-level system architecture and component flowcharts.
- **`DATA_COLLECTION.md`**: Initial GitHub discovery and commit collection guide.
- **`DATASET_SCHEMA.md`**: SQLite relational schema and export formats.
- **`FEATURES.md`**: Initial Roslyn static code metric definitions.
- **`METHODOLOGY.md`**: Initial problem statement, SZZ pipeline, and labeling taxonomy.
- **`MODEL.md`**: Initial Random Forest specification, hyperparameters, and MDI importance.
- **`VALIDATION.md`**: Initial validation guide and smoke testing checklist.


---

## v3.0.0 Migration Archives & Preserved Method-Level Artifacts

Before executing the v3.0.0 SQLite schema migration and 106-repository class-level data collection, all historical method-level artifacts were preserved intact:

- **`1_Database/SQLite/bug_detection_method_v2_archive.db`**: Pre-migration SQLite snapshot preserving the original 5-repository method-level schema, `877` `observations`/`features` rows, and Datasets #1 (`483` methods) and #2 (`578` methods).
- **`1_Database/Datasets/Original/csharp_empirical_v1_v1.0.0.csv`**: Untouched historical Dataset #1 (`SHA-256: 32398813679af7715398ab50b15d15741b9aa28426aa581284855b05cb9ab527`).
- **`1_Database/Datasets/Processed/csharp_empirical_v2_v2.0.0.csv`**: Untouched historical Dataset #2 (`SHA-256: 30b63239417ff2aa0900de6c1566a6919a703d512b48652062fddc05a8b15a56`).
- **Preserved Method-Level `.joblib` Bundles (`4_AppBuild/Assets/Models/`)**:
  - `rf_csharp_empirical_model.joblib` (`e316287b942b1cae1cadc62e0637cd4e617e634618fc255ea1a528d38e5e952f`)
  - `exp_final_5fold_v2_best_rf_compact_regularized.joblib` (`625992350a78d28277c3521a3ff97f5e28cda4d4f6996c1dc90374512c19cb1e`)
  - `et_nested_opt_v3_depth6_leaf6_log2.joblib` (`9f99ba6419e75962e2b01bfa5ef0f7fe2d7acafc2e2281326e6d4e58f3868bd3`)
  - `rf_nested_opt_v3_depth6_leaf8_log2.joblib` (`48f6cb91124d09a2b2e3cb0f062ff74272499d6659e4e47eb6cadab567a966ab`)
