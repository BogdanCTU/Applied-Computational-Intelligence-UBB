import pandas as pd

df = pd.read_csv('agent_om_local/output/step7d1_validation_decisions.csv')
print(f"Total decision records: {len(df)}")

for base_var in ['A2.1_Original', 'A2.3_Canonical']:
    sub = df[df['base_variant'] == base_var]
    runs = sub['run_index'].unique()
    print(f"\nChecking stability for {base_var} across runs {runs}...")
    pivot = sub.pivot_table(
        index=['direction', 'source_name', 'target_name'],
        columns='run_index',
        values='decision',
        aggfunc='first'
    )
    mismatches = 0
    for idx, row in pivot.iterrows():
        vals = set(row.dropna().values)
        if len(vals) > 1:
            print(f"Mismatch at {idx}: {dict(row)}")
            mismatches += 1
    if mismatches == 0:
        print(f"SUCCESS: 100% identical decisions across all 3 runs for {base_var} ({len(pivot)} candidate pairs evaluated).")

