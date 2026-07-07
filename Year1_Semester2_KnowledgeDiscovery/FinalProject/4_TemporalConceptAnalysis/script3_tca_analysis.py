"""
=============================================================================
Script 3 - Temporal Concept Analysis (Life Tracks)
=============================================================================
Temporal Concept Analysis (TCA) - Continuous Casting Machine Dataset

INPUT  : tca_s2_concepts.csv   (output of Script 2)
OUTPUT : tca_s3_analysis.csv   (all TCA results in one multi-section CSV)

What it does
------------
1. Reads all formal concepts produced by Script 2.
2. Matches concepts across days by identical intent (the concept's intent
   is its identity - extents may differ across days).
3. Computes the LIFE TRACK of every unique concept:
     LifeTrack(C) = {t | intent(C) in Concepts(K_t)}
4. Computes LIFESPAN and classifies every concept:
     Universal    - alive in all time windows
     Long-lived   - alive in >= 70% of windows
     Medium-lived - alive in 30-69% of windows
     Short-lived  - alive in 10-29% of windows
     Ephemeral    - alive in < 10% of windows
5. Detects BIRTH (first appearance) and DEATH (last appearance).
6. Computes attribute PREVALENCE per day (% of records at each BIN level).
7. Writes everything into ONE CSV using a `record_type` discriminator column
   so that Script 4 can filter the section it needs.

Output sections (record_type values)
--------------------------------------
  "life_track"    - one row per unique concept intent
  "lattice_stats" - one row per day (concept count, density, ...)
  "prevalence"    - one row per (day, attribute, level)
  "births_deaths" - one row per day (n_births, n_deaths, n_alive)
  "summary"       - overall TCA metrics (Metric + Value columns)

Usage
-----
  python script3_tca_analysis.py
=============================================================================
"""

import sys
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths  (single input -> single output)
# ---------------------------------------------------------------------------

BASE_DIR   = Path(__file__).parent
INPUT_CSV  = BASE_DIR / "tca_s2_concepts.csv"
OUTPUT_CSV = BASE_DIR / "tca_s3_analysis.csv"

# ---------------------------------------------------------------------------
# Life-track classification thresholds (fraction of all days)
# ---------------------------------------------------------------------------

THRESHOLDS = {
    "Universal":    1.00,
    "Long-lived":   0.70,
    "Medium-lived": 0.30,
    "Short-lived":  0.10,
    "Ephemeral":    0.00,
}

# BIN columns for prevalence (must be present in tca_s2_concepts.csv via
# the expanded intent strings - we reconstruct them from the intent column)
BIN_COL_PREFIXES = [
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
    "steel_type",
    "alloy_type",
    "workpiece_slice_geometry",
]


# ---------------------------------------------------------------------------
# Step 1 - Load concepts CSV
# ---------------------------------------------------------------------------

def load_concepts(path: Path):
    """
    Load tca_s2_concepts.csv and reconstruct the per-day concept dict.

    Returns
    -------
    days         : sorted list[str]
    day_concepts : {date: list of {"intent": list[str], "extent": list[str]}}
    df           : the raw DataFrame (for lattice stats)
    """
    df = pd.read_csv(path, low_memory=False)
    required = {"date", "intent", "extent", "intent_size", "extent_size",
                "n_objects", "n_attributes"}
    missing = required - set(df.columns)
    if missing:
        sys.exit(f"ERROR: missing columns in {path.name}: {missing}")

    days = sorted(df["date"].unique())
    day_concepts = {}
    for date_str in days:
        day_df = df[df["date"] == date_str]
        day_concepts[date_str] = [
            {
                "intent": [s.strip() for s in str(row["intent"]).split(" | ") if s.strip()],
                "extent": [s.strip() for s in str(row["extent"]).split(" | ") if s.strip()],
            }
            for _, row in day_df.iterrows()
        ]

    total = sum(len(v) for v in day_concepts.values())
    print(f"[1/6] Loaded {len(days)} days, {total:,} concept instances.")
    print(f"      Date range : {days[0]} -> {days[-1]}")
    return days, day_concepts, df


# ---------------------------------------------------------------------------
# Step 2 - Build life tracks
# ---------------------------------------------------------------------------

def build_life_tracks(days, day_concepts):
    """
    Match concepts across days by identical frozen intent set.
    Returns {frozenset(intent): {date: extent_list}}
    """
    tracks = defaultdict(dict)
    for date_str in days:
        for concept in day_concepts[date_str]:
            key = frozenset(concept["intent"])
            tracks[key][date_str] = concept["extent"]

    print(f"\n[2/6] Life-track matching done.  Unique concepts: {len(tracks):,}")
    return tracks


# ---------------------------------------------------------------------------
# Step 3 - Classify and build life-track table
# ---------------------------------------------------------------------------

def classify(lifespan, total_days):
    frac = lifespan / max(total_days, 1)
    for label, thresh in THRESHOLDS.items():
        if frac >= thresh:
            return label
    return "Ephemeral"


def build_life_track_df(tracks, days):
    total_days = len(days)
    rows = []
    for key, day_extents in tracks.items():
        alive = sorted(day_extents.keys())
        ls    = len(alive)
        ext_sizes = [len(day_extents[d]) for d in alive]
        rows.append({
            "record_type":      "life_track",
            "intent_str":       " | ".join(sorted(key)),
            "intent_size":      len(key),
            "lifespan":         ls,
            "lifespan_pct":     round(ls / total_days * 100, 2),
            "classification":   classify(ls, total_days),
            "birth_day":        alive[0],
            "last_alive_day":   alive[-1],
            "still_alive_at_end": alive[-1] == days[-1],
            "alive_days":       " | ".join(alive),
            "avg_extent_size":  round(np.mean(ext_sizes), 2),
        })

    df = pd.DataFrame(rows)
    df.sort_values(["lifespan", "intent_size"], ascending=[False, True], inplace=True)
    df.reset_index(drop=True, inplace=True)

    print(f"\n[3/6] Life-track table built.  {len(df):,} unique concepts.")
    for cat in ["Universal", "Long-lived", "Medium-lived", "Short-lived", "Ephemeral"]:
        n = (df["classification"] == cat).sum()
        print(f"        {cat:<14}: {n:>5,}")
    return df


# ---------------------------------------------------------------------------
# Step 4 - Births and deaths per day
# ---------------------------------------------------------------------------

def build_births_deaths_df(tracks, days):
    born_per_day  = defaultdict(int)
    dead_per_day  = defaultdict(int)
    alive_per_day = defaultdict(int)

    for key, day_extents in tracks.items():
        alive = sorted(day_extents.keys())
        born_per_day[alive[0]]  += 1
        dead_per_day[alive[-1]] += 1
        for d in alive:
            alive_per_day[d] += 1

    rows = []
    for date_str in days:
        rows.append({
            "record_type": "births_deaths",
            "date":        date_str,
            "n_births":    born_per_day[date_str],
            "n_deaths":    dead_per_day[date_str],
            "n_alive":     alive_per_day.get(date_str, 0),
        })

    print(f"\n[4/6] Births/deaths computed.")
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Step 5 - Attribute prevalence (reconstructed from intent strings)
# ---------------------------------------------------------------------------

def build_prevalence_df(days, day_concepts, raw_concepts_df):
    """
    For each day, count how many concepts contain each attribute=value token
    in their intent, normalised by the total number of concepts that day.
    This yields the "attribute prevalence" analogous to the paper's Table 9.
    """
    rows = []
    for date_str in days:
        concepts = day_concepts[date_str]
        if not concepts:
            continue
        n_concepts = len(concepts)
        # Count attribute=value tokens across all intents
        token_counts = defaultdict(int)
        for c in concepts:
            for token in c["intent"]:
                token_counts[token] += 1
        for token, cnt in token_counts.items():
            if "=" not in token:
                continue
            attr, level = token.split("=", 1)
            rows.append({
                "record_type":    "prevalence",
                "date":           date_str,
                "attribute":      attr,
                "level":          level,
                "prevalence_pct": round(cnt / n_concepts * 100, 2),
                "n_concepts":     n_concepts,
            })

    print(f"\n[5/6] Prevalence table built.  {len(rows):,} rows.")
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Step 6 - Lattice statistics and summary
# ---------------------------------------------------------------------------

def build_lattice_stats_df(raw_df, days):
    """Aggregate per-day lattice statistics from the raw concepts DataFrame."""
    rows = []
    for date_str in days:
        day = raw_df[raw_df["date"] == date_str]
        if day.empty:
            continue
        rows.append({
            "record_type":      "lattice_stats",
            "date":             date_str,
            "context_id":       day["context_id"].iloc[0],
            "n_concepts":       len(day),
            "n_objects":        int(day["n_objects"].iloc[0]),
            "n_attributes":     int(day["n_attributes"].iloc[0]),
            "density":          round(len(day) / max(1, int(day["n_objects"].iloc[0]) * int(day["n_attributes"].iloc[0])), 6),
            "avg_intent_size":  round(day["intent_size"].mean(), 3),
            "avg_extent_size":  round(day["extent_size"].mean(), 3),
            "max_intent_size":  int(day["intent_size"].max()),
            "max_extent_size":  int(day["extent_size"].max()),
        })
    return pd.DataFrame(rows)


def build_summary_df(lt_df, days):
    cat = lt_df["classification"].value_counts()
    metrics = [
        ("Time windows (days)",               len(days)),
        ("Total unique concepts",              len(lt_df)),
        ("Universal concepts (lifespan=100%)", int(cat.get("Universal",    0))),
        ("Long-lived concepts (>=70%)",        int(cat.get("Long-lived",   0))),
        ("Medium-lived concepts (30-69%)",     int(cat.get("Medium-lived", 0))),
        ("Short-lived concepts (10-29%)",      int(cat.get("Short-lived",  0))),
        ("Ephemeral concepts (<10%)",          int(cat.get("Ephemeral",    0))),
        ("Max lifespan (days)",                int(lt_df["lifespan"].max())),
        ("Min lifespan (days)",                int(lt_df["lifespan"].min())),
        ("Mean lifespan (days)",               round(float(lt_df["lifespan"].mean()), 2)),
        ("Median lifespan (days)",             float(lt_df["lifespan"].median())),
        ("Total concept-day instances",        int(lt_df["lifespan"].sum())),
    ]
    rows = [{"record_type": "summary", "Metric": m, "Value": str(v)} for m, v in metrics]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  Script 3 - Temporal Concept Analysis")
    print("  Continuous Casting Machine Dataset")
    print("=" * 60 + "\n")

    if not INPUT_CSV.exists():
        sys.exit(f"ERROR: {INPUT_CSV} not found.\n       Run script2_fca_per_day.py first.")

    # ---- Load ----
    days, day_concepts, raw_df = load_concepts(INPUT_CSV)

    # ---- Life tracks ----
    tracks  = build_life_tracks(days, day_concepts)
    lt_df   = build_life_track_df(tracks, days)

    # ---- Births/deaths ----
    bd_df   = build_births_deaths_df(tracks, days)

    # ---- Prevalence ----
    prev_df = build_prevalence_df(days, day_concepts, raw_df)

    # ---- Lattice stats ----
    ls_df   = build_lattice_stats_df(raw_df, days)

    # ---- Summary ----
    sum_df  = build_summary_df(lt_df, days)

    # ---- Combine all sections into ONE CSV ----
    print(f"\n[6/6] Writing output ...")
    combined = pd.concat([lt_df, bd_df, prev_df, ls_df, sum_df], ignore_index=True, sort=False)
    combined.to_csv(OUTPUT_CSV, index=False)
    print(f"       File          : {OUTPUT_CSV}")
    print(f"       Size          : {OUTPUT_CSV.stat().st_size / 1024:.1f} KB")
    print(f"       Total rows    : {len(combined):,}")
    for rt in ["life_track", "lattice_stats", "prevalence", "births_deaths", "summary"]:
        n = (combined["record_type"] == rt).sum()
        print(f"         record_type={rt:<15}: {n:>5,} rows")

    print("\n" + "=" * 60)
    print("  TCA SUMMARY")
    print("=" * 60)
    for _, row in sum_df.iterrows():
        print(f"  {row['Metric']:<45} {row['Value']}")

    print("\n  Top-5 longest-lived concepts:")
    for _, row in lt_df.head(5).iterrows():
        preview = row["intent_str"][:65] + ("..." if len(row["intent_str"]) > 65 else "")
        print(f"    lifespan={row['lifespan']:>3}d  [{row['classification']}]  {preview}")

    print("=" * 60)


if __name__ == "__main__":
    main()
