import pandas as pd

df = pd.read_csv('agent_om_local/output/step7d_validation_decisions.csv')

# Group by normalized pair and direction, or see all pairs evaluated
# Let's see what unique pairs exist across the variants
# A candidate pair is identified by (source_uri, target_uri, direction)
# Let's inspect decisions per pair across variants

pivot = df.pivot_table(index=['source_name', 'target_name', 'direction'], columns='variant', values='decision', aggfunc='first')
print("Pivot table of decisions:")
diff_pairs = []
for idx, row in pivot.iterrows():
    # check if decisions differ across available variants or if not all identical
    vals = set(row.dropna().values)
    if len(vals) > 1 or row.isna().any():
        diff_pairs.append((idx, dict(row)))

print(f"Total evaluated pair-direction combinations: {len(pivot)}")
print(f"Combinations with differing decisions or missingness: {len(diff_pairs)}")
for pair, decisions in diff_pairs:
    print(f"\nPair: {pair[0]} <-> {pair[1]} [{pair[2]}]")
    print(f"Decisions: {decisions}")


