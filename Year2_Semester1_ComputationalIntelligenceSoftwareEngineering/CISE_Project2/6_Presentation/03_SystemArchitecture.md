# Slide 3 — System Architecture

```mermaid
flowchart LR
    IB["InferredBugs C# (536 repos)"] --> ROS["RoslynPreprocessor (.NET 9.0)"]
    GH["GitHub Bug-Fixes (56 repos)"] --> ROS
    HN["Hard Negatives (45 repos)"] --> ROS
    ROS --> VAL["Deduplicator & SQLite v5"]
    VAL --> ML["FeaturePipeline + RandomForest (536 features)"]
    ML --> CLI["CLI (`bug_detector`)"]
    ML --> GUI["Minimal 6-Page Streamlit App"]
```

- **16-table SQLite schema** with content-addressed `source_blobs`.
- **Persistent JSONL Roslyn bridge** (`RoslynPreprocessor.dll batch`) for deterministic parsing and feature extraction.
