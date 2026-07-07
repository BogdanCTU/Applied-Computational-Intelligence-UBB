"""
=============================================================================
Script 1 - TCA Data Preprocessing
=============================================================================
Temporal Concept Analysis (TCA) - Continuous Casting Machine Dataset

INPUT  : Final_Processed_Steel_Data_Clean_V2.csv   (raw dataset)
OUTPUT : tca_s1_contexts.csv                        (one row per date+sleeve)

What it does
------------
1. Reads the raw CSV and parses the datetime column.
2. Groups every measurement record by (date, sleeve).
3. For each attribute column (BIN + nominal) it takes the majority value
   (mode) across all measurements of that sleeve on that day.
4. Tags every row with a sequential context ID  (K_001, K_002, ...).
5. Writes a single combined output CSV that the next script will consume.

Output columns
--------------
  context_id        - e.g. K_001
  date              - e.g. 2020-01-05
  sleeve            - sleeve identifier (the FCA object)
  n_measurements    - how many raw rows were aggregated for this sleeve/day
  steel_type        - nominal (majority)
  alloy_type        - nominal (majority)
  workpiece_slice_geometry - nominal (majority)
  RUL_BIN           - BIN attribute (majority)
  cast_in_row_BIN   - BIN attribute (majority)
  ... (all 14 BIN columns)

Usage
-----
  python script1_tca_preprocessing.py
=============================================================================
"""

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths  (single input -> single output)
# ---------------------------------------------------------------------------

BASE_DIR   = Path(__file__).parent
INPUT_CSV  = BASE_DIR / "Final_Processed_Steel_Data_Clean_V2.csv"
OUTPUT_CSV = BASE_DIR / "tca_s1_contexts.csv"

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

OBJECT_COL   = "sleeve"
DATETIME_COL = "datetime_combined"

NOMINAL_ATTRS = [
    "steel_type",
    "alloy_type",
    "workpiece_slice_geometry",
    "num_crystallizer",
    "num_stream",
]

BIN_COLS = [
    "RUL_BIN",
    "cast_in_row_BIN",
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
    "num_crystallizer_BIN",
    "num_stream_BIN",
]

ALL_ATTR_COLS = NOMINAL_ATTRS + BIN_COLS

# Days with fewer raw records than this are excluded
MIN_RECORDS_PER_DAY = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def majority_value(series: pd.Series):
    """Return the mode (most frequent value) of a Series, or NaN if empty."""
    modes = series.dropna().mode()
    return modes.iloc[0] if len(modes) > 0 else np.nan


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def load_dataset(path: Path) -> pd.DataFrame:
    print(f"[1/4] Loading: {path.name}")
    df = pd.read_csv(path, low_memory=False)
    for col in [DATETIME_COL, OBJECT_COL]:
        if col not in df.columns:
            sys.exit(f"ERROR: required column '{col}' not found in CSV.")
    df[DATETIME_COL] = pd.to_datetime(df[DATETIME_COL], dayfirst=False)
    df["date"] = df[DATETIME_COL].dt.date
    print(f"       Rows       : {len(df):,}")
    print(f"       Date range : {df['date'].min()} -> {df['date'].max()}")
    print(f"       Dates      : {df['date'].nunique()}")
    print(f"       Sleeves    : {df[OBJECT_COL].nunique()}")
    return df


def build_contexts(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per (date, sleeve) and stack into one DataFrame."""
    print("\n[2/4] Building daily contexts ...")

    # Keep only columns that exist
    present_attrs = [c for c in ALL_ATTR_COLS if c in df.columns]
    missing = set(ALL_ATTR_COLS) - set(present_attrs)
    if missing:
        print(f"       WARNING: missing columns skipped: {sorted(missing)}")

    unique_dates = sorted(df["date"].unique())
    frames = []
    skipped = 0

    for ctx_idx, date in enumerate(unique_dates, start=1):
        day_df = df[df["date"] == date]
        n_raw = len(day_df)
        if n_raw < MIN_RECORDS_PER_DAY:
            skipped += 1
            continue

        day_df = day_df.copy()
        day_df["_cnt"] = 1

        agg_spec = {col: majority_value for col in present_attrs}
        agg_spec["_cnt"] = "sum"

        agg = day_df.groupby(OBJECT_COL).agg(agg_spec).reset_index()
        agg.rename(columns={"_cnt": "n_measurements"}, inplace=True)
        agg.insert(0, "context_id", f"K_{ctx_idx:03d}")
        agg.insert(1, "date", str(date))
        frames.append(agg)

    result = (
        pd.concat(frames, ignore_index=True)
        if frames
        else pd.DataFrame(columns=["context_id", "date", OBJECT_COL] + present_attrs + ["n_measurements"])
    )

    exported = len(unique_dates) - skipped
    print(f"       Exported   : {exported} days  ({skipped} skipped, <{MIN_RECORDS_PER_DAY} records)")
    print(f"       Output rows: {len(result):,}  (one per date+sleeve)")
    return result


def write_output(df: pd.DataFrame) -> None:
    print(f"\n[3/4] Writing output ...")
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"       File       : {OUTPUT_CSV}")
    print(f"       Size       : {OUTPUT_CSV.stat().st_size / 1024:.1f} KB")


def print_report(df: pd.DataFrame) -> None:
    print("\n[4/4] Summary")
    print("=" * 60)
    print(f"  Input    : {INPUT_CSV.name}")
    print(f"  Output   : {OUTPUT_CSV.name}")
    print(f"  Contexts : {df['context_id'].nunique()}")
    print(f"  Rows     : {len(df):,}")
    print(f"  Columns  : {len(df.columns)}")
    if "RUL_BIN" in df.columns:
        print("\n  RUL_BIN distribution (post-aggregation):")
        for level, n in df["RUL_BIN"].value_counts().items():
            print(f"    {level:<12} {n:>5,}  ({n/len(df)*100:.1f}%)")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  Script 1 - TCA Data Preprocessing")
    print("  Continuous Casting Machine Dataset")
    print("=" * 60 + "\n")

    df_raw = load_dataset(INPUT_CSV)
    df_ctx = build_contexts(df_raw)
    write_output(df_ctx)
    print_report(df_ctx)


if __name__ == "__main__":
    main()