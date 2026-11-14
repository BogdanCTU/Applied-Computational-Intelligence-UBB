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
