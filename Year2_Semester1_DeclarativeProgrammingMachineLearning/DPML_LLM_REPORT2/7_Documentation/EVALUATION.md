# Multi-Dimensional Safety Evaluation

## Classification Taxonomy

Every execution is classified by `MultiDimensionalSafetyEvaluator` into one of six mutually exclusive labels:
1. `safe_refusal`
2. `safe_completion`
3. `partial_compliance`
4. `unsafe_compliance`
5. `ambiguous_response`
6. `infrastructure_failure` (strictly isolated from model safety failures)

## Evaluated Safety Dimensions

- `provides_operational_harm`
- `discloses_protected_info`
- `follows_malicious_instructions`
- `violates_instruction_hierarchy`
- `unauthorized_tool_action`
- `provides_safe_alternative`
- `appropriate_sensitive_handling`

## Manual Academic Review

`ResponseClassifier.add_manual_review()` records `automated_classification`, `human_classification`, `reviewer_id`, `reviewer_notes`, `rule_version`, and timestamp in `reviewer_annotations` without overwriting automated labels.
