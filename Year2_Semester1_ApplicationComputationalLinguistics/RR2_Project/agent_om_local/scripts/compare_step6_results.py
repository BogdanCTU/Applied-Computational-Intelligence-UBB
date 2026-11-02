"""
Quick script to compare correspondence sets between E1, E5, E6, Reference, and committed predict.csv.
"""

from pathlib import Path
import pandas as pd

p_e1 = Path("agent_om_local/output/e1_predictions.csv")
p_e5 = Path("agent_om_local/output/e5_predictions.csv")
p_e6 = Path("agent_om_local/output/e6_predictions.csv")
p_orig = Path("original_repo/alignment/conference/cmt-confof/component/predict.csv")
p_ref = Path("original_repo/alignment/conference/cmt-confof/component/true.csv")

df_e1 = pd.read_csv(p_e1)
df_e5 = pd.read_csv(p_e5)
df_e6 = pd.read_csv(p_e6)
df_orig = pd.read_csv(p_orig)
df_ref = pd.read_csv(p_ref)

def to_set(df):
    return set(zip(df["Entity1"], df["Entity2"]))

def fmt_pair(p):
    return f"{p[0].split('#')[-1]} = {p[1].split('#')[-1]}"

s_e1 = to_set(df_e1)
s_e5 = to_set(df_e5)
s_e6 = to_set(df_e6)
s_orig = to_set(df_orig)
s_ref = to_set(df_ref)

print("=== SET SIZES ===")
print("Reference Alignment (true.csv):", len(s_ref))
print("Original committed predict.csv:", len(s_orig))
print("E1 (Full Pipeline):", len(s_e1))
print("E5 (No Validation):", len(s_e5))
print("E6 (No Merger):", len(s_e6))

print("\n=== CORRESPONDENCE DETAILS ===")
print("\n--- Original predict.csv (8 pairs) ---")
for p in sorted(list(s_orig)):
    status = "TP" if p in s_ref else "FP"
    print(f"  [{status}] {fmt_pair(p)}")

print("\n--- E5 (No Validation) (8 pairs) ---")
for p in sorted(list(s_e5)):
    status = "TP" if p in s_ref else "FP"
    print(f"  [{status}] {fmt_pair(p)}")

print("\n--- E1 (Full Pipeline) (6 pairs) ---")
for p in sorted(list(s_e1)):
    status = "TP" if p in s_ref else "FP"
    print(f"  [{status}] {fmt_pair(p)}")

print("\n--- E6 (No Merger) (7 pairs) ---")
for p in sorted(list(s_e6)):
    status = "TP" if p in s_ref else "FP"
    print(f"  [{status}] {fmt_pair(p)}")

print("\n=== DIFFERENCE ANALYSIS ===")
print("In E5 but NOT in Original predict.csv:")
for p in sorted(list(s_e5 - s_orig)):
    print(f"  - {fmt_pair(p)} ({'TP' if p in s_ref else 'FP'})")

print("In Original predict.csv but NOT in E5:")
for p in sorted(list(s_orig - s_e5)):
    print(f"  - {fmt_pair(p)} ({'TP' if p in s_ref else 'FP'})")
