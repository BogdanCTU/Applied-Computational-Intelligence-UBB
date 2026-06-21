import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
from typing import Dict, List, Tuple, Set


class CTSOTAnalyzer:
    """
    Implements a Conceptual Time System with Objects and Time (CTSOT).
    Extracts formal states (S1-S4), maps object trajectories, and validates temporal patterns.
    """

    def __init__(self, data_frame: pd.DataFrame, object_col: str, time_col: str):
        """
        Initializes the CTSOT system with core data and parameters.
        """
        self.df: pd.DataFrame = data_frame.copy()
        self.object_col: str = object_col
        self.time_col: str = time_col

        # Ensure strict chronological sorting to establish successor relation (prec)
        self.df[self.time_col] = pd.to_datetime(self.df[self.time_col])
        self.df = self.df.sort_values(by=[self.object_col, self.time_col]).reset_index(drop=True)

        # Explicit formal state definitions derived from FCA knowledge documentation
        self.state_labels: Dict[str, str] = {
            "S1": "Healthy sleeve, low accumulated tonnage, high casting speed",
            "S2": "Medium sleeve condition, increasing tonnage, normal casting speed",
            "S3": "Low sleeve condition, reduced casting speed, increasing wear",
            "S4": "Critical sleeve, high accumulated tonnage, maintenance required"
        }

    def map_formal_states(self) -> pd.DataFrame:
        """
        Maps each temporal observation to one of the 4 representative FCA states
        based on the documentation criteria.
        """
        states = []

        for _, row in self.df.iterrows():
            rul_class = str(row.get('RUL_Class', '')).strip().lower()
            tonnage_bin = str(row.get('steel_weight, tonn_BIN', '')).strip().lower()
            speed_bin = str(row.get('alloy_speed, meter/minute_BIN', '')).strip().lower()

            # Mathematical classification based on logical combinations of attributes (intent)
            if rul_class == 'healthy' or (tonnage_bin == 'low' and speed_bin == 'high'):
                states.append('S1')
            elif rul_class == 'medium' or speed_bin == 'medium':
                states.append('S2')
            elif (rul_class == 'unhealthy' or speed_bin == 'low') and rul_class != 'critical':
                states.append('S3')
            elif rul_class == 'critical' or tonnage_bin == 'high':
                states.append('S4')
            else:
                states.append('S2')  # Default fallback mapping

        self.df['formal_state'] = states
        return self.df

    def evaluate_temporal_patterns(self) -> Dict[str, float]:
        """
        Calculates empirical verification percentages for the 5 documented temporal patterns.
        """
        if 'formal_state' not in self.df.columns:
            self.map_states_and_find_perfect_lifecycles()

        grouped = self.df.groupby(self.object_col)

        pattern_checks = {
            "P1_Healthy_Before_Critical": [],
            "P2_Tonnage_Precedes_Degradation": [],
            "P3_Speed_Drop_Precedes_Critical": [],
            "P4_Long_Sequences_Stable": [],
            "P5_Crystallizers_9_16_Degrade": []
        }

        for sleeve_id, group in grouped:
            sorted_group = group.sort_values(by=self.time_col)
            states = sorted_group['formal_state'].tolist()
            tonnages = sorted_group['steel_weight, tonn_BIN'].astype(str).str.lower().tolist()
            speeds = sorted_group['alloy_speed, meter/minute_BIN'].astype(str).str.lower().tolist()
            crystallizers = sorted_group['num_crystallizer'].tolist()
            sequence_len = len(sorted_group)

            if len(states) < 2:
                continue

            if 'S1' in states and 'S4' in states:
                pattern_checks["P1_Healthy_Before_Critical"].append(states.index('S1') < states.index('S4'))
            elif 'S4' in states and 'S1' not in states:
                pattern_checks["P1_Healthy_Before_Critical"].append(False)

            has_high_tonnage = 'high' in tonnages
            has_degradation = ('S3' in states or 'S4' in states)
            if has_high_tonnage and has_degradation:
                pattern_checks["P2_Tonnage_Precedes_Degradation"].append(
                    tonnages.index('high') <= max(states.index('S3') if 'S3' in states else 0,
                                                  states.index('S4') if 'S4' in states else 0))

            has_low_speed = 'low' in speeds
            if has_low_speed and 'S4' in states:
                pattern_checks["P3_Speed_Drop_Precedes_Critical"].append(speeds.index('low') < states.index('S4'))

            s4_transitions = sum(1 for i in range(len(states) - 1) if states[i] != 'S4' and states[i + 1] == 'S4')
            if sequence_len > 30:
                pattern_checks["P4_Long_Sequences_Stable"].append(s4_transitions <= 1)

            uses_target_crystallizer = any(9 <= int(c) <= 16 for c in crystallizers if str(c).isdigit())
            if uses_target_crystallizer:
                pattern_checks["P5_Crystallizers_9_16_Degrade"].append('S3' in states or 'S4' in states)

        results = {}
        for pattern, outcomes in pattern_checks.items():
            results[pattern] = float(np.mean(outcomes) * 100) if outcomes else 0.0

        return results

    def find_perfect_lifecycle_sleeves(self) -> List[str]:
        """
        Identifies and filters sleeves that contain all four operational states
        and follow a strict chronological degradation path.
        """
        if 'formal_state' not in self.df.columns:
            self.map_formal_states()

        perfect_sleeves = []
        grouped = self.df.groupby(self.object_col)

        for sleeve_id, group in grouped:
            sorted_states = group.sort_values(by=self.time_col)['formal_state'].tolist()
            unique_states = set(sorted_states)

            # Verify the sleeve experienced every single classification state
            if {'S1', 'S2', 'S3', 'S4'}.issubset(unique_states):
                # Enforce chronological ordering requirement (S1 index < S2 index < S3 index < S4 index)
                idx_s1 = sorted_states.index('S1')
                idx_s2 = sorted_states.index('S2')
                idx_s3 = sorted_states.index('S3')
                idx_s4 = sorted_states.index('S4')

                if idx_s1 < idx_s2 < idx_s3 < idx_s4:
                    perfect_sleeves.append(sleeve_id)

        return perfect_sleeves

    def generate_trajectory_matrices(self, output_dir: str, target_sleeves: List[str]) -> None:
        """
        Generates individual pathway visual line plots showing complete S1->S4 lifecycles
        with the vertical layout structured from top (Healthy) to bottom (Critical).
        """
        if not target_sleeves:
            print("[Warning] No sleeves found matching the strict sequential lifecycle S1->S2->S3->S4.")
            return

        plt.figure(figsize=(12, 6))

        # Mapping numeric values to map a descending layout trend
        # S1 (Healthy) mapped to 4 (Top), S4 (Critical) mapped to 1 (Bottom)
        state_map_numeric = {"S1": 4, "S2": 3, "S3": 2, "S4": 1}

        for sleeve_id in target_sleeves[:4]:  # Plot up to 4 pristine examples for contrast
            subset = self.df[self.df[self.object_col] == sleeve_id].sort_values(by=self.time_col)
            numeric_y = [state_map_numeric[s] for s in subset['formal_state']]
            plt.plot(subset[self.time_col], numeric_y, marker='o', alpha=0.9, linewidth=2.5,
                     label=f"Sleeve {sleeve_id}")

        # Re-label the ticks to correctly display descriptions despite the inverted layout tracking
        plt.yticks([4, 3, 2, 1], ['S1 (Healthy)', 'S2 (Medium)', 'S3 (Low)', 'S4 (Critical)'])
        plt.title(
            "Physical Asset Trajectories: Sequential Wear Life-Tracks ($S_1 \\rightarrow S_2 \\rightarrow S_3 \\rightarrow S_4$)",
            fontsize=13, fontweight='bold')
        plt.xlabel("Timeline Context (Chronological Successor Relation $\prec$)", fontsize=11)
        plt.ylabel("Observed Conceptual State", fontsize=11)
        plt.grid(True, linestyle=':', alpha=0.6)
        plt.legend(loc="upper right")
        plt.xticks(rotation=20)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "tca_empirical_lifetracks.png"), dpi=300)
        plt.close()

    def generate_transition_topology(self, output_dir: str) -> None:
        """
        Builds a directed graph visual showing the aggregated transitions across the system.
        """
        if 'formal_state' not in self.df.columns:
            self.map_formal_states()

        transitions = []
        grouped = self.df.groupby(self.object_col)

        for _, group in grouped:
            seq = group.sort_values(by=self.time_col)['formal_state'].tolist()
            for i in range(len(seq) - 1):
                transitions.append((seq[i], seq[i + 1]))

        plt.figure(figsize=(7, 5))
        graph = nx.DiGraph()
        graph.add_edges_from(transitions)

        layout = nx.circular_layout(graph)

        nx.draw_networkx_nodes(graph, layout, node_size=1200, node_color='#ffcccb', edgecolors='red')
        nx.draw_networkx_edges(graph, layout, arrowstyle='->', arrowsize=25, edge_color='black', width=2)
        nx.draw_networkx_labels(graph, layout, font_size=12, font_weight='bold')

        plt.title("State-Transition Diagram $S=(\\Sigma, \\rightarrow)$ Topology", fontsize=13, fontweight='bold')
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "tca_state_transitions_topology.png"), dpi=300)
        plt.close()


if __name__ == "__main__":
    input_filename = "Final_Processed_Steel_Data_Clean.csv"
    output_directory = "TCA_Results"

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    print(f"Loading dataset: {input_filename}...")
    try:
        raw_data = pd.read_csv(input_filename)
    except FileNotFoundError:
        print(f"Error: The dataset '{input_filename}' was not found.")
        exit(1)

    object_sleeve_key = "sleeve"
    temporal_granule_key = "datetime_combined"

    engine = CTSOTAnalyzer(
        data_frame=raw_data,
        object_col=object_sleeve_key,
        time_col=temporal_granule_key
    )

    print("Step 1: Computing Event Context Mappings...")
    engine.map_formal_states()

    print(
        "Step 2: Isolating sleeves with complete sequential trajectories ($S_1 \\rightarrow S_2 \\rightarrow S_3 \\rightarrow S_4$)...")
    valid_lifecycle_sleeves = engine.find_perfect_lifecycle_sleeves()
    print(f" -> Found {len(valid_lifecycle_sleeves)} sleeves matching strict lifecycle criteria.")

    print("Step 3: Generating Tabular Data Outputs...")
    state_descriptions_table = pd.DataFrame([
        {"State": key, "Concept Description": value}
        for key, value in engine.state_labels.items()
    ])
    state_descriptions_table.to_csv(os.path.join(output_directory, "table_state_definitions.csv"), index=False)

    pattern_metrics = engine.evaluate_temporal_patterns()
    pattern_table = pd.DataFrame([
        {"Temporal Pattern Hypothesis": key, "Empirical Validation Rate (%)": f"{value:.2f}%"}
        for key, value in pattern_metrics.items()
    ])
    pattern_table.to_csv(os.path.join(output_directory, "table_pattern_validation.csv"), index=False)

    print("Step 4: Rendering Inverted Lifecycle Graphs...")
    engine.generate_trajectory_matrices(output_directory, valid_lifecycle_sleeves)
    engine.generate_transition_topology(output_directory)

    print("\n========================================================")
    print(f"TCA Complete! Perfect lifecycle trends saved to: '{output_directory}'")
    print(" - tca_empirical_lifetracks.png     : Top-to-bottom degradation plot.")
    print("========================================================\n")