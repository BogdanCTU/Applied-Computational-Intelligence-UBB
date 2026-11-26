# Slide 7 — Limitations and Future Work

1. **Near-Twin Method Ceiling:** Distinguishing 1-line-buggy methods from their patched post-fix versions via aggregate token/AST/DFG counts limits ROC-AUC (`0.5848` RF, `0.5969` ExtraTrees) and produces `77.92%` FPR on `inferredbugs_post_fix` twins.
2. **Isolated-File Semantic Context:** Without full `.csproj`/NuGet assemblies, external API types remain unresolved in Roslyn's `SemanticModel`.
3. **Next Steps:** Sequence/graph code representations (AST-path or transformer embeddings), full solution MSBuild compilation context, and `.Tests.` substring exclusion refinement.
