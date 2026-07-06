import pandas as pd

# ==========================================
# Configuration
# ==========================================

INPUT_FILE = "Final_Processed_Steel_Data_Clean_V2.csv"
OUTPUT_FILE = "Final_Processed_Steel_Data_Clean_V2_AE_Binarized.csv"

# ==========================================
# Load dataset
# ==========================================

df = pd.read_csv(INPUT_FILE)

print(f"Original shape: {df.shape}")

# ==========================================
# Keep only *_BIN columns
# ==========================================

bin_columns = [c for c in df.columns if c.endswith("_BIN")]

context = df[bin_columns].copy()

print(f"Keeping {len(bin_columns)} BIN columns.")

# ==========================================
# Remove constant attributes
# ==========================================

constant_cols = [c for c in context.columns if context[c].nunique() <= 1]

if constant_cols:
    print("\nRemoving constant columns:")
    for c in constant_cols:
        print("  ", c)

context.drop(columns=constant_cols, inplace=True)

# ==========================================
# Remove duplicate objects
# ==========================================

before = len(context)

context.drop_duplicates(inplace=True)

after = len(context)

print(f"\nRemoved {before-after} duplicate rows.")

# ==========================================
# Nominal conceptual scaling
# ==========================================

binary_context = pd.get_dummies(
    context,
    prefix=context.columns,
    prefix_sep="="
)

binary_context = binary_context.astype(int)

# ==========================================
# Save
# ==========================================

binary_context.to_csv(OUTPUT_FILE, index=False)

print("\n==============================")
print("Binary FCA context created.")
print(f"Objects   : {len(binary_context)}")
print(f"Attributes: {len(binary_context.columns)}")
print(f"Saved as  : {OUTPUT_FILE}")
print("==============================")

print("\nFirst five rows:")
print(binary_context.head())