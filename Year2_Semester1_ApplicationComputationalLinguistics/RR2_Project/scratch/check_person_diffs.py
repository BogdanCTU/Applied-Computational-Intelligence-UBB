import pandas as pd

df = pd.read_csv('agent_om_local/output/step7d_validation_decisions.csv')
p = df[(df['source_name'].isin(['ConferenceMember', 'Participant'])) & (df['target_name'] == 'Person')]
for idx, r in p.iterrows():
    print(f"Variant: {r['variant']} | Dir: {r['direction']} | {r['source_name']} -> {r['target_name']}")
    print(f"Decision: {r['decision']}")
    print(f"Prompt:\n{r['prompt']}")
    print(f"Response:\n{r['raw_response']}")
    print("=" * 60)

