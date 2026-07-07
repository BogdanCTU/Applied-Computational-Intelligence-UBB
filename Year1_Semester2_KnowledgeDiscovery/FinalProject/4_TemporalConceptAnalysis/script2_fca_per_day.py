"""
=============================================================================
Script 2 - FCA Per Day (NextClosure)
=============================================================================
Temporal Concept Analysis (TCA) - Continuous Casting Machine Dataset

INPUT  : tca_s1_contexts.csv   (output of Script 1)
OUTPUT : tca_s2_concepts.csv   (all formal concepts across all days)

What it does
------------
For every time window (day) in the input:
  1. Selects the sleeve rows for that day.
  2. Expands BIN/nominal columns into binary  attribute=value  flags.
  3. Enumerates all formal concepts using the NextClosure algorithm
     (Ganter 1999) - no external FCA library required.
  4. Records the intent (pipe-separated attribute=value strings) and
     extent (pipe-separated sleeve IDs) of every concept.

All concepts from all days are concatenated into a single output CSV.

Output columns
--------------
  date          - e.g. 2020-01-05
  context_id    - e.g. K_001
  concept_id    - sequential index within each day (0-based)
  intent        - e.g. "RUL_BIN=Healthy | steel_type=Arm500 | ..."
  extent        - e.g. "30011717 | 30012345"
  intent_size   - number of attributes in the intent
  extent_size   - number of sleeves in the extent
  n_objects     - total sleeves in this day's context
  n_attributes  - total expanded attributes in this day's context

Usage
-----
  python script2_fca_per_day.py
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
INPUT_CSV  = BASE_DIR / "tca_s1_contexts.csv"
OUTPUT_CSV = BASE_DIR / "tca_s2_concepts.csv"

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

OBJECT_COL   = "sleeve"
CONTEXT_COL  = "context_id"
DATE_COL     = "date"

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

NOMINAL_COLS = ["steel_type", "alloy_type", "workpiece_slice_geometry"]

# Safety cap: stop enumeration after this many concepts per day
MAX_CONCEPTS_PER_DAY = 5000


# ---------------------------------------------------------------------------
# Formal context builder
# ---------------------------------------------------------------------------

def build_incidence(day_df: pd.DataFrame):
    """
    Expand BIN/nominal columns into binary attribute=value flags.

    Returns
    -------
    objects    : list[str]         sleeve IDs
    attributes : list[str]         "ColName=Value" labels
    incidence  : np.ndarray[bool]  shape (n_objects, n_attributes)
    """
    attr_cols = [c for c in BIN_COLS + NOMINAL_COLS if c in day_df.columns]
    objects = day_df[OBJECT_COL].astype(str).tolist()

    attribute_labels = []
    incidence_cols   = []

    for col in attr_cols:
        for val in sorted(day_df[col].dropna().unique()):
            attribute_labels.append(f"{col}={val}")
            incidence_cols.append((day_df[col] == val).values.astype(bool))

    if not incidence_cols:
        return objects, [], np.zeros((len(objects), 0), dtype=bool)

    return objects, attribute_labels, np.column_stack(incidence_cols)


# ---------------------------------------------------------------------------
# NextClosure algorithm (Ganter 1999) - pure NumPy/Python, no FCA library
# ---------------------------------------------------------------------------

def _attr_prime(inc: np.ndarray, attr_set) -> frozenset:
    """B' = objects that possess every attribute in attr_set."""
    if not attr_set:
        return frozenset(range(inc.shape[0]))
    mask = np.ones(inc.shape[0], dtype=bool)
    for j in attr_set:
        mask &= inc[:, j]
    return frozenset(np.where(mask)[0])


def _obj_prime(inc: np.ndarray, obj_set) -> frozenset:
    """A' = attributes shared by every object in obj_set."""
    if not obj_set:
        return frozenset(range(inc.shape[1]))
    mask = np.ones(inc.shape[1], dtype=bool)
    for i in obj_set:
        mask &= inc[i]
    return frozenset(np.where(mask)[0])


def _closure(inc: np.ndarray, attr_set) -> frozenset:
    """Galois closure  B -> B'' = (B')' ."""
    return _obj_prime(inc, _attr_prime(inc, attr_set))


def _next_closure(inc: np.ndarray, current: frozenset, n_attrs: int):
    """
    Compute the lectic successor of `current` in the set of all closures.
    Returns None when `current` is the last closed set.
    """
    for i in reversed(range(n_attrs)):
        if i in current:
            current = current - {i}
        else:
            candidate = current | {i}
            closed    = _closure(inc, candidate)
            # Lectic order: closed and current must agree on all j < i
            if all((j in closed) == (j in current) for j in range(i)) and i in closed:
                return closed
    return None


def enumerate_concepts(objects, attributes, incidence, max_concepts):
    """
    Yield all formal concepts as (intent_labels, extent_labels) tuples.
    Stops after max_concepts to avoid combinatorial explosion.
    """
    n_attr = len(attributes)
    if n_attr == 0 or len(objects) == 0:
        return

    current = _closure(incidence, frozenset())
    count   = 0

    while current is not None:
        if count >= max_concepts:
            print(f"        [CAP] Reached {max_concepts} concepts; stopping.")
            break
        ext_idx    = _attr_prime(incidence, current)
        intent_lbl = sorted(attributes[j] for j in current)
        extent_lbl = sorted(objects[i]    for i in ext_idx)
        yield intent_lbl, extent_lbl
        current = _next_closure(incidence, current, n_attr)
        count  += 1


# ---------------------------------------------------------------------------
# Per-day processing
# ---------------------------------------------------------------------------

def process_day(day_df: pd.DataFrame, date_str: str, ctx_id: str):
    """Compute all concepts for one day; return a list of row dicts."""
    objects, attributes, incidence = build_incidence(day_df)
    n_obj  = len(objects)
    n_attr = len(attributes)

    print(f"  {date_str} ({ctx_id})  {n_obj} sleeves x {n_attr} attrs ...", end=" ", flush=True)

    if n_attr == 0:
        print("(no attributes - skipped)")
        return []

    rows = []
    for concept_id, (intent, extent) in enumerate(
            enumerate_concepts(objects, attributes, incidence, MAX_CONCEPTS_PER_DAY)):
        rows.append({
            "date":         date_str,
            "context_id":   ctx_id,
            "concept_id":   concept_id,
            "intent":       " | ".join(intent),
            "extent":       " | ".join(extent),
            "intent_size":  len(intent),
            "extent_size":  len(extent),
            "n_objects":    n_obj,
            "n_attributes": n_attr,
        })

    print(f"{len(rows)} concepts")
    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  Script 2 - FCA Per Day (NextClosure)")
    print("  Continuous Casting Machine Dataset")
    print("=" * 60 + "\n")

    if not INPUT_CSV.exists():
        sys.exit(f"ERROR: {INPUT_CSV} not found.\n       Run script1_tca_preprocessing.py first.")

    df_ctx = pd.read_csv(INPUT_CSV, low_memory=False)
    print(f"[1/3] Loaded: {INPUT_CSV.name}  ({len(df_ctx):,} rows)\n")

    if DATE_COL not in df_ctx.columns or CONTEXT_COL not in df_ctx.columns:
        sys.exit(f"ERROR: expected columns '{DATE_COL}' and '{CONTEXT_COL}' not found.")

    all_rows = []
    dates = sorted(df_ctx[DATE_COL].unique())
    print(f"[2/3] Computing concepts for {len(dates)} days ...\n")

    for date_str in dates:
        day_df   = df_ctx[df_ctx[DATE_COL] == date_str].copy()
        ctx_id   = day_df[CONTEXT_COL].iloc[0]
        day_rows = process_day(day_df, date_str, ctx_id)
        all_rows.extend(day_rows)

    df_out = pd.DataFrame(all_rows)

    print(f"\n[3/3] Writing output ...")
    df_out.to_csv(OUTPUT_CSV, index=False)
    print(f"       File           : {OUTPUT_CSV}")
    print(f"       Size           : {OUTPUT_CSV.stat().st_size / 1024:.1f} KB")

    print("\n" + "=" * 60)
    print("  FCA SUMMARY")
    print("=" * 60)
    print(f"  Input contexts   : {len(dates)}")
    print(f"  Total concepts   : {len(df_out):,}")
    if not df_out.empty:
        print(f"  Min per day      : {df_out.groupby('date')['concept_id'].count().min()}")
        print(f"  Max per day      : {df_out.groupby('date')['concept_id'].count().max()}")
        print(f"  Mean per day     : {df_out.groupby('date')['concept_id'].count().mean():.1f}")
        print(f"  Avg intent size  : {df_out['intent_size'].mean():.2f}")
        print(f"  Avg extent size  : {df_out['extent_size'].mean():.2f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
