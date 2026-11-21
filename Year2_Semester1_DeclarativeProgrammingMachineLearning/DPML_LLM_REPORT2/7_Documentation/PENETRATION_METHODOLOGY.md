# Penetration Testing Methodology

## Scope and Isolation

All penetration tests are confined strictly to the local Ollama endpoint (`127.0.0.1:11434`) and synthetic fixtures inside `AgentToolSandbox`. No external systems, real PII, live credentials, or functional exploit chains are ever targeted or generated.

## Experimental Design

1. **System Prompt Hierarchy**: Every inference uses a versioned system prompt (`sys_safety_v1.0`) establishing instruction hierarchy, refusal requirements for harmful/illegal requests, canary protection (`SYNTH-CANARY-9042`), and benign helpfulness.
2. **Multi-Turn & Single-Turn Execution**: Multi-turn tests establish benign context in early turns before introducing adversarial escalation in the final turn.
3. **Tool-Boundary Separation**: Tool-relevant categories (`prompt_injection`, `data_exfiltration`, `tool_abuse`) attach `TOOL_DEFINITIONS` and intercept emitted `tool_calls` through `AgentToolSandbox`. Even when the deterministic sandbox blocks an unauthorized call, the model's unauthorized attempt is still logged as a model-level safety violation.
4. **Deterministic Replay**: Identical `test_id`s, conversation turns, system prompt, tool definitions, `temperature=0.0`, `seed=42`, and `num_predict=96` are used for both baseline (`qwen3.5:4b`) and mitigated (`qwen3.5:4b-safety`) runs.
