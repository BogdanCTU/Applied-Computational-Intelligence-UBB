import pandas as pd

df = pd.read_csv('agent_om_local/output/step6_validation_logs.csv')
pc = df[df['source_name'].str.contains('Chair', case=False) | df['target_name'].str.contains('Chair', case=False)]
print(f"Total Chair rows: {len(pc)}")
for idx, r in pc.head(10).iterrows():
    print(f"Exp: {r['experiment_id']} | Dir: {r['direction']} | {r['source_name']} -> {r['target_name']}")
    print(f"Bypassed: {r['bypassed']} | Decision: {r['decision']}")
    print(f"Prompt:\n{r['prompt']}")
    print(f"Response:\n{r['raw_response']}")
    print("=" * 60)

