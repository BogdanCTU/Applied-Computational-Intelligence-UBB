import pandas as pd

df = pd.read_csv('agent_om_local/output/step7b_validation_decisions.csv')

print("=" * 70)
print("FALSE NEGATIVES (Ground-Truth Correspondences Rejected by Validator)")
print("=" * 70)
fn_df = df[df['failure_type'].str.contains('False Negative')]
for idx, r in fn_df.iterrows():
    print(f"[{r['threshold']}] {r['direction']}: {r['source_name']} -> {r['target_name']}")
    print(f"Prompt: {repr(r['prompt'])}")
    print(f"Response: {repr(r['raw_response'])}")
    print("-" * 50)

print("\n" + "=" * 70)
print("DIRECTIONAL ASYMMETRY (Accepted in S->T but Rejected in T->S or vice versa)")
print("=" * 70)
# Group by (threshold, source_name, target_name)
grouped = df.groupby(['threshold', 'source_name', 'target_name'])
for (tau, s_name, t_name), group in grouped:
    dirs = group['direction'].tolist()
    decs = group['decision'].tolist()
    if len(dirs) > 1 and len(set(decs)) > 1:
        print(f"[{tau}] {s_name} <-> {t_name}")
        for _, r in group.iterrows():
            print(f"   {r['direction']}: bypassed={r['bypassed']}, decision={r['decision']}")
            print(f"   Prompt: {repr(r['prompt'])}")
            print(f"   Response: {repr(r['raw_response'])}")
        print("-" * 50)

print("\n" + "=" * 70)
print("FALSE POSITIVES ACCEPTED BY LLM (Excluding Bypasses)")
print("=" * 70)
fp_llm = df[(df['failure_type'].str.contains('False Positive')) & (~df['bypassed'])]
for idx, r in fp_llm.iterrows():
    print(f"[{r['threshold']}] {r['direction']}: {r['source_name']} -> {r['target_name']}")
    print(f"Decision: {r['decision']}")
    print(f"Prompt: {repr(r['prompt'])}")
    print(f"Response: {repr(r['raw_response'])}")
    print("-" * 50)

