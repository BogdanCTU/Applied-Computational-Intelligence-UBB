#!/usr/bin/env python3
"""
==============================================================
Per-condition Dyadic Context Slices and Concept Lattice Sizes
==============================================================

This script computes the dyadic context slice for every condition
of a triadic context, reports the size of its concept lattice,
and saves a PNG image of each lattice using NetworkX and Matplotlib.

Input:
    triadic_context.csv

Format:
    Object,Attributes,Condition

Requirements:
    pip install pandas concepts networkx matplotlib
"""

import pandas as pd
import concepts
import networkx as nx
import matplotlib.pyplot as plt
import re

# ==============================================================
# Configuration
# ==============================================================

INPUT_CSV = "Final_Processed_Steel_Data_Clean_V2_Triadic_V2.csv"


# ==============================================================
# Image Generation Method
# ==============================================================

def save_lattice_image_networkx(lattice, condition):
    """
    Builds a directed graph representing a concept lattice.
    Creates a mapping dictionary to assign unique integer identifiers to concepts.
    Draws the graph using a spring layout and saves it as a PNG file.
    Creates a safe file name by replacing non-alphanumeric characters.
    """
    graph = nx.DiGraph()

    concept_to_index = {concept: index for index, concept in enumerate(lattice)}

    for concept, index in concept_to_index.items():

        intent_label = "\n".join(concept.intent) if concept.intent else "Top"
        graph.add_node(index, label=intent_label)

        for child in concept.lower_neighbors:
            child_index = concept_to_index[child]
            graph.add_edge(index, child_index)

    plt.figure(figsize=(12, 10))

    layout_positions = nx.spring_layout(graph, seed=42)

    nx.draw_networkx_nodes(
        graph,
        layout_positions,
        node_size=1500,
        node_color="lightgreen"
    )

    nx.draw_networkx_edges(
        graph,
        layout_positions,
        arrows=True,
        arrowsize=15,
        edge_color="gray"
    )

    node_labels = nx.get_node_attributes(graph, 'label')
    nx.draw_networkx_labels(
        graph,
        layout_positions,
        labels=node_labels,
        font_size=8
    )

    safe_name = re.sub(r'[^A-Za-z0-9]', '_', str(condition))
    file_name = f"lattice_{safe_name}.png"

    plt.title(f"Concept Lattice: {condition}")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(file_name, format="png")
    plt.close()


# ==============================================================
# Main Execution Method
# ==============================================================

def process_triadic_context(input_file):
    """
    Reads a triadic context CSV file and calculates dyadic slices.
    Generates a concept lattice for each slice condition.
    Calls the image generation method to output PNG files.
    Prints a statistical summary table to the console.
    """
    df = pd.read_csv(input_file)

    required_columns = {"Object", "Attributes", "Condition"}

    if not required_columns.issubset(df.columns):
        raise Exception(
            "CSV must contain Object, Attributes and Condition columns."
        )

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

    results = []

    for condition in conditions:
        slice_df = df[df["Condition"] == condition]

        incidence = pd.crosstab(
            slice_df["Object"],
            slice_df["Attributes"]
        )

        incidence = incidence.astype(bool)

        object_names = incidence.index.astype(str).tolist()
        attribute_names = incidence.columns.astype(str).tolist()
        bool_matrix = incidence.values.tolist()

        ctx = concepts.Context(
            object_names,
            attribute_names,
            bool_matrix
        )

        lattice = ctx.lattice

        save_lattice_image_networkx(lattice, condition)

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

    results = sorted(
        results,
        key=lambda x: x["Concepts"],
        reverse=True
    )

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


if __name__ == "__main__":
    process_triadic_context(INPUT_CSV)