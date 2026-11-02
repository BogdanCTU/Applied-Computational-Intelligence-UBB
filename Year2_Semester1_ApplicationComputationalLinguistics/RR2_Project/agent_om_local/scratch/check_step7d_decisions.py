import pandas as pd

df = pd.read_csv('agent_om_local/output/step7d_validation_decisions.csv')
print("Total records:", len(df))
print("Variants:", df['variant'].unique())

print("\n" + "=" * 70)
print("PROGRAM COMMITTEE CHAIR <-> CHAIR_PC ACROSS VARIANTS")
print("=" * 70)
chair = df[df['source_name'].str.contains('Chair') | df['target_name'].str.contains('Chair')]
for idx, r in chair.iterrows():
    print(f"Variant: {r['variant']} | Dir: {r['direction']} | {r['source_name']} -> {r['target_name']}")
    print(f"Bypassed: {r['bypassed']} | Decision: {r['decision']}")
    print(f"Prompt:\n{r['prompt']}")
    print(f"Response:\n{r['raw_response']}")
    print("-" * 50)

print("\n" + "=" * 70)
print("CANDIDATES WITH DIFFERING DECISIONS ACROSS VARIANTS")
print("=" * 70)
# Pivot on (direction, source_name, target_name) with values=decision
piv = df[~df['bypassed']].pivot_table(
    index=['direction', 'source_name', 'target_name'],
    columns='variant',
    values='decision',
    aggfunc='first'
)
diffs = piv[piv.nunique(axis=1) > 1]
print(diffs.to_string())

