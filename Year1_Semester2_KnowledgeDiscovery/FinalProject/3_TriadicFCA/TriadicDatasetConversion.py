import pandas as pd
from collections import Counter

# =============================================================================
# Configuration
# =============================================================================

INPUT_CSV = "Final_Processed_Steel_Data_Clean_V2.csv"
OUTPUT_CSV = "Final_Processed_Steel_Data_Clean_V2_Triadic.csv"

# -----------------------------------------------------------------------------
# Attributes (second dimension of the triadic context)
# -----------------------------------------------------------------------------

ATTRIBUTE_COLUMNS = [
    "steel_type",
    "alloy_type",
    "workpiece_slice_geometry",
    "RUL_BIN",
    "num_stream_BIN",
    "num_crystallizer_BIN",
]

# -----------------------------------------------------------------------------
# Conditions (third dimension of the triadic context)
# -----------------------------------------------------------------------------

CONDITION_COLUMNS = [
    "steel_weighttonn_BIN",
    "steel_temperature_grab1Celsius_BIN",
    "resistance_tonn_BIN",
    "swing_frequency_amount_minute_BIN",
    "crystallizer_movementmm_BIN",
    "alloy_speed_meter_minute_BIN",
    "water_consumption_BIN",
    "water_temperature_deltaCelsius_BIN",
    "temperature_measurement1_Celsius_BIN",
    "temperature_measurement2_Celsius_BIN",
]

OBJECT_COLUMN = "sleeve"

# =============================================================================
# Helper
# =============================================================================

def majority(series):
    """
    Returns the most frequent value.
    If multiple values have the same frequency,
    pandas mode() returns all of them.
    We simply select the first.
    """
    mode = series.mode(dropna=True)

    if len(mode) == 0:
        return None

    return mode.iloc[0]


# =============================================================================
# Read dataset
# =============================================================================

df = pd.read_csv(INPUT_CSV)

# =============================================================================
# Aggregate by sleeve
# =============================================================================

aggregated = (
    df.groupby(OBJECT_COLUMN)
      .agg({col: majority for col in ATTRIBUTE_COLUMNS + CONDITION_COLUMNS})
      .reset_index()
)

# =============================================================================
# Build triadic context
# =============================================================================

rows = []

for _, row in aggregated.iterrows():

    obj = row[OBJECT_COLUMN]

    # Every attribute is paired with every majority condition
    for attribute in ATTRIBUTE_COLUMNS:

        attribute_value = f"{attribute}={row[attribute]}"

        for condition in CONDITION_COLUMNS:

            condition_value = f"{condition}={row[condition]}"

            rows.append(
                {
                    "Object": obj,
                    "Attributes": attribute_value,
                    "Condition": condition_value,
                }
            )

triadic_context = pd.DataFrame(rows)

# Remove possible duplicates
triadic_context = triadic_context.drop_duplicates()

# Sort for readability
triadic_context = triadic_context.sort_values(
    ["Object", "Attributes", "Condition"]
)

# =============================================================================
# Save
# =============================================================================

triadic_context.to_csv(OUTPUT_CSV, index=False)

print()
print("========================================")
print("Triadic context successfully generated")
print("========================================")
print(f"Objects    : {aggregated.shape[0]}")
print(f"Rows       : {len(triadic_context)}")
print(f"Saved to   : {OUTPUT_CSV}")