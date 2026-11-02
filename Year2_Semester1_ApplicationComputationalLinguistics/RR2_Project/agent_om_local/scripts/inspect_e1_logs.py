"""
Script to inspect E1 validation decisions and directional comparisons.
"""

from pathlib import Path
import pandas as pd

df = pd.read_csv("agent_om_local/output/step6_validation_logs.csv")
e1 = df[df["experiment_id"] == "E1"]

print(f"Total E1 validation entries: {len(e1)}")
print(f"  Bypassed entries: {len(e1[e1['bypassed'] == True])}")
print(f"  LLM calls:        {len(e1[e1['bypassed'] == False])}")
print(f"  Decisions:        {dict(e1['decision'].value_counts())}")

print("\n--- ALL E1 VALIDATION RECORDS ---")
for idx, r in e1.iterrows():
    b_flag = "BYPASS" if r["bypassed"] else f"LLM ({r['duration_ms']:.0f}ms)"
    print(f"[{r['direction']}] {r['source_name']} -> {r['target_name']} | {b_flag} | Decision: {r['decision']}")
    if not r["bypassed"]:
        print(f"    Prompt:   {repr(r['prompt'])}")
        print(f"    Response: {repr(r['raw_response'])}")

