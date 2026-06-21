import os
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
from typing import Dict, List


class CTSOTAnalyzer:
    """
    Temporal Concept Analysis (TCA) extraction for sleeve degradation.

    States:
        S1 = Healthy
        S2 = Medium
        S3 = Low
        S4 = Critical
    """

    def __init__(
        self,
        data_frame: pd.DataFrame,
        object_col: str,
        time_col: str
    ):

        self.df = data_frame.copy()
        self.object_col = object_col
        self.time_col = time_col

        self.df[self.time_col] = pd.to_datetime(
            self.df[self.time_col],
            errors="coerce"
        )

        self.df = (
            self.df
            .dropna(subset=[self.time_col])
            .sort_values(
                by=[self.object_col, self.time_col]
            )
            .reset_index(drop=True)
        )

        self.state_labels = {
            "S1": "Healthy",
            "S2": "Medium",
            "S3": "Low",
            "S4": "Critical"
        }

    # ------------------------------------------------------------------
    # STATE MAPPING
    # ------------------------------------------------------------------

    def map_formal_states(self) -> pd.DataFrame:
        """
        Direct mapping from RUL class to FCA/TCA state.
        """

        mapping = {
            "healthy": "S1",
            "medium": "S2",
            "low": "S3",
            "critical": "S4"
        }

        self.df["formal_state"] = (
            self.df["RUL_Class"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map(mapping)
        )

        self.df = self.df.dropna(subset=["formal_state"])

        return self.df

    # ------------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------------

    def validate_degradation_path(
        self,
        sleeve_id: int
    ) -> Dict:

        subset = (
            self.df[self.df[self.object_col] == sleeve_id]
            .sort_values(self.time_col)
        )

        state_order = {
            "S1": 1,
            "S2": 2,
            "S3": 3,
            "S4": 4
        }

        states = subset["formal_state"].tolist()

        violations = []

        for i in range(1, len(states)):

            prev_state = state_order[states[i - 1]]
            curr_state = state_order[states[i]]

            if curr_state < prev_state:
                violations.append(
                    (
                        states[i - 1],
                        states[i]
                    )
                )

        return {
            "sleeve": sleeve_id,
            "num_records": len(states),
            "states": states,
            "monotonic": len(violations) == 0,
            "violations": violations
        }

    # ------------------------------------------------------------------
    # LIFE TRACKS
    # ------------------------------------------------------------------

    def generate_targeted_lifetracks_plot(
        self,
        output_path: str,
        target_sleeves: List[int]
    ) -> None:

        if "formal_state" not in self.df.columns:
            self.map_formal_states()

        state_numeric = {
            "S1": 4,
            "S2": 3,
            "S3": 2,
            "S4": 1
        }

        plt.figure(figsize=(15, 7))

        plotted = False

        for sleeve_id in target_sleeves:

            subset = (
                self.df[self.df[self.object_col] == sleeve_id]
                .sort_values(self.time_col)
            )

            if subset.empty:
                print(
                    f"Warning: Sleeve {sleeve_id} not found."
                )
                continue

            plotted = True

            timestamps = subset[self.time_col]

            y = [
                state_numeric[s]
                for s in subset["formal_state"]
            ]

            validation = self.validate_degradation_path(
                sleeve_id
            )

            label = (
                f"{sleeve_id}"
                if validation["monotonic"]
                else f"{sleeve_id} (non-monotonic)"
            )

            plt.step(
                timestamps,
                y,
                where="post",
                linewidth=2.5,
                label=label
            )

            plt.scatter(
                timestamps,
                y,
                s=25
            )

        if not plotted:
            print("No sleeves were plotted.")
            return

        plt.yticks(
            [4, 3, 2, 1],
            [
                "S1 (Healthy)",
                "S2 (Medium)",
                "S3 (Low)",
                "S4 (Critical)"
            ]
        )

        plt.ylim(0.5, 4.5)

        plt.title(
            "Temporal Concept Analysis Life-Tracks",
            fontsize=14,
            fontweight="bold"
        )

        plt.xlabel("Time")
        plt.ylabel("Conceptual State")

        plt.grid(
            True,
            linestyle=":",
            alpha=0.5
        )

        plt.legend()

        plt.tight_layout()

        plt.savefig(
            output_path,
            dpi=300,
            bbox_inches="tight"
        )

        plt.close()

    # ------------------------------------------------------------------
    # TRANSITION TOPOLOGY
    # ------------------------------------------------------------------

    def generate_transition_topology(
        self,
        output_dir: str
    ) -> None:

        graph = nx.DiGraph()

        graph.add_edges_from(
            [
                ("S1", "S2"),
                ("S2", "S3"),
                ("S3", "S4")
            ]
        )

        plt.figure(figsize=(9, 4))

        pos = {
            "S1": (0, 0),
            "S2": (1, 0),
            "S3": (2, 0),
            "S4": (3, 0)
        }

        nx.draw_networkx_nodes(
            graph,
            pos,
            node_size=1800
        )

        nx.draw_networkx_edges(
            graph,
            pos,
            arrows=True,
            arrowsize=25,
            width=2
        )

        nx.draw_networkx_labels(
            graph,
            pos,
            font_weight="bold"
        )

        plt.title(
            "Ideal TCA State Transition Topology"
        )

        plt.axis("off")

        plt.tight_layout()

        plt.savefig(
            os.path.join(
                output_dir,
                "tca_state_transitions_topology.png"
            ),
            dpi=300
        )

        plt.close()


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------

if __name__ == "__main__":

    input_filename = "Final_Processed_Steel_Data_Clean.csv"
    output_directory = "TCA_Results"

    os.makedirs(
        output_directory,
        exist_ok=True
    )

    print(
        f"Loading dataset: {input_filename}"
    )

    try:
        raw_data = pd.read_csv(input_filename)

    except FileNotFoundError:

        print(
            f"Dataset not found: {input_filename}"
        )

        raise SystemExit(1)

    engine = CTSOTAnalyzer(
        data_frame=raw_data,
        object_col="sleeve",
        time_col="datetime_combined"
    )

    print("Mapping states...")
    engine.map_formal_states()

    requested_ids = [
        30011705,
        30013875,
        30014079,
        30014082
    ]

    print("\nValidation Results")

    for sleeve in requested_ids:

        result = engine.validate_degradation_path(
            sleeve
        )

        print(
            f"\nSleeve {sleeve}"
        )

        print(
            f"Records: {result['num_records']}"
        )

        print(
            f"Monotonic: {result['monotonic']}"
        )

        if result["violations"]:
            print(
                f"Violations: {result['violations']}"
            )

    print(
        "\nGenerating empirical life-tracks..."
    )

    engine.generate_targeted_lifetracks_plot(
        output_path=os.path.join(
            output_directory,
            "tca_empirical_lifetracks.png"
        ),
        target_sleeves=requested_ids
    )

    print(
        "Generating transition topology..."
    )

    engine.generate_transition_topology(
        output_directory
    )

    print("\nDone.")