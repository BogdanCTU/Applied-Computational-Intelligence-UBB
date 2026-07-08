#!/usr/bin/env python3
"""
==============================================================
Per-condition Dyadic Context Slices and Concept Lattice Sizes
==============================================================

This script computes the dyadic context slice for every condition
of a triadic context and reports the size of its concept lattice.

Input:
    triadic_context.csv

Format:
    Object,Attributes,Condition

Example:
Object,Attributes,Condition
30011717,steel_type=Arm500,steel_weighttonn_BIN=High
30011717,steel_type=Arm500,resistance_tonn_BIN=Low
...

Requirements:
    pip install pandas concepts
"""

import pandas as pd
import concepts

# ==============================================================
# Configuration
# ==============================================================

INPUT_CSV = "Final_Processed_Steel_Data_Clean_V2_Triadic_V2.csv"

# ==============================================================
# Read triadic context
# ==============================================================

df = pd.read_csv(INPUT_CSV)

required = {"Object", "Attributes", "Condition"}

if not required.issubset(df.columns):
    raise Exception(
        "CSV must contain Object, Attributes and Condition columns."
    )

# ==============================================================
# General statistics
# ==============================================================

objects = sorted(df["Object"].unique())
attributes = sorted(df["Attributes"].unique())
conditions = sorted(df["Condition"].unique())

print("=" * 70)
print("TRIADIC CONTEXT")
print("=" * 70)
print(f"Objects    : {len(objects)}")
print(f"Attributes : {len(attributes)}")
print(f"Conditions : {len(conditions)}")
print(f"Relations  : {len(df)}")
print("=" * 70)
print()

# ==============================================================
# Compute dyadic slices
# ==============================================================

results = []

for condition in conditions:

    # ---------------------------------------------
    # Extract one condition
    # ---------------------------------------------

    slice_df = df[df["Condition"] == condition]

    # ---------------------------------------------
    # Binary incidence matrix
    # ---------------------------------------------

    incidence = pd.crosstab(
        slice_df["Object"],
        slice_df["Attributes"]
    )

    incidence = incidence.astype(bool)

    # ---------------------------------------------
    # Convert to FCA context
    # ---------------------------------------------

    object_names = incidence.index.astype(str).tolist()
    attribute_names = incidence.columns.astype(str).tolist()

    bool_matrix = incidence.values.tolist()

    ctx = concepts.Context(
        object_names,
        attribute_names,
        bool_matrix
    )

    lattice = ctx.lattice

    num_objects = len(object_names)
    num_attributes = len(attribute_names)
    num_concepts = len(lattice)

    ratio = (
        num_concepts / num_objects
        if num_objects > 0 else 0
    )

    results.append({
        "Condition": condition,
        "Objects": num_objects,
        "Attributes": num_attributes,
        "Concepts": num_concepts,
        "Ratio": ratio
    })

# ==============================================================
# Sort by lattice complexity
# ==============================================================

results = sorted(
    results,
    key=lambda x: x["Concepts"],
    reverse=True
)

# ==============================================================
# Print table
# ==============================================================

print("=" * 110)
print("PER-CONDITION DYADIC CONTEXT SLICES")
print("=" * 110)

header = (
    f'{"Condition":45}'
    f'{"Objects":>10}'
    f'{"Attrs":>10}'
    f'{"Concepts":>12}'
    f'{"Concepts/Object":>18}'
)

print(header)
print("-" * len(header))

for r in results:

    print(
        f'{r["Condition"]:45}'
        f'{r["Objects"]:>10}'
        f'{r["Attributes"]:>10}'
        f'{r["Concepts"]:>12}'
        f'{r["Ratio"]:>18.2f}'
    )

print()

# ==============================================================
# Summary
# ==============================================================

largest = max(results, key=lambda x: x["Concepts"])
smallest = min(results, key=lambda x: x["Concepts"])

print("=" * 70)
print("SUMMARY")
print("=" * 70)

print(
    f"Largest lattice : "
    f"{largest['Condition']} "
    f"({largest['Concepts']} concepts)"
)

print(
    f"Smallest lattice: "
    f"{smallest['Condition']} "
    f"({smallest['Concepts']} concepts)"
)

avg = sum(r["Concepts"] for r in results) / len(results)

print(f"Average concepts per slice : {avg:.2f}")

print("=" * 70)