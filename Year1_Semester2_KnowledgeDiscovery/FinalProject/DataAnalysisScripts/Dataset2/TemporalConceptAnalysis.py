import os
import json
import pandas as pd
from typing import Dict, List, Tuple, Set


class TemporalConceptAnalyzer:
    """
    Performs Temporal Concept Analysis (TCA) on industrial time-series data.
    Extracts formal states, builds transitions, and maps object life-tracks.
    """

    def __init__(self, data_frame: pd.DataFrame, object_col: str, time_col: str, attribute_cols: List[str]):
        """
        Initializes the analyzer with dataset definitions.
        """
        self.df: pd.DataFrame = data_frame.copy()
        self.object_col: str = object_col
        self.time_col: str = time_col
        self.attribute_cols: List[str] = attribute_cols

        # Ensure time column is sorted chronologically
        self.df[self.time_col] = pd.to_datetime(self.df[self.time_col])
        self.df = self.df.sort_values(by=[self.object_col, self.time_col]).reset_index(drop=True)

        # State mapping storage
        self.intents_to_state_id: Dict[Tuple[str, ...], int] = {}
        self.state_id_to_intents: Dict[int, Tuple[str, ...]] = {}

    def _generate_state_intent(self, row: pd.Series) -> Tuple[str, ...]:
        """
        Generates a unique, sorted tuple of attribute-value pairs representing a formal intent.
        """
        intent_elements = []
        for col in self.attribute_cols:
            val = str(row[col])
            intent_elements.append(f"{col}={val}")
        return tuple(sorted(intent_elements))

    def compute_state_space(self) -> pd.DataFrame:
        """
        Identifies unique formal concepts (states) based on identical attribute intents.
        Appends a unique state identifier to the dataset.
        """
        state_ids = []
        state_counter = 0

        for _, row in self.df.iterrows():
            intent = self._generate_state_intent(row)
            if intent not in self.intents_to_state_id:
                self.intents_to_state_id[intent] = state_counter
                self.state_id_to_intents[state_counter] = intent
                state_counter += 1
            state_ids.append(self.intents_to_state_id[intent])

        self.df['state_id'] = state_ids
        return self.df

    def extract_life_tracks(self) -> Dict[str, List[Tuple[str, int]]]:
        """
        Extracts the life-track trajectory for each physical object asset.
        Returns a dictionary mapping object IDs to a sequence of (timestamp, state_id) tuples.
        """
        if 'state_id' not in self.df.columns:
            self.compute_state_space()

        life_tracks = {}
        grouped = self.df.groupby(self.object_col)

        for obj_id, group in grouped:
            track = []
            for _, row in group.iterrows():
                timestamp_str = row[self.time_col].strftime('%Y-%m-%d %H:%M')
                state_id = int(row['state_id'])
                track.append((timestamp_str, state_id))
            life_tracks[str(obj_id)] = track

        return life_tracks

    def build_state_transitions(self) -> Set[Tuple[int, int]]:
        """
        Identifies the direct transitions between formal states across consecutive time granules.
        """
        if 'state_id' not in self.df.columns:
            self.compute_state_space()

        transitions = set()
        grouped = self.df.groupby(self.object_col)

        for _, group in grouped:
            state_sequence = group['state_id'].tolist()
            for i in range(len(state_sequence) - 1):
                from_state = state_sequence[i]
                to_state = state_sequence[i + 1]
                transitions.add((from_state, to_state))

        return transitions

    def get_state_details(self, state_id: int) -> Tuple[str, ...]:
        """
        Returns the formal attribute intent associated with a given state identifier.
        """
        return self.state_id_to_intents.get(state_id, ())


if __name__ == "__main__":
    # Define input and output file configurations
    input_filename = "Final_Processed_Steel_Data_Clean.csv"
    output_directory = "TCA_Results"

    # Establish target output directory structures
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    print(f"Reading dataset: {input_filename}...")
    try:
        raw_data = pd.read_csv(input_filename)
    except FileNotFoundError:
        print(f"Error: The file '{input_filename}' was not found in the current directory.")
        exit(1)

    # Establish operational configuration variables for the evaluation
    object_identifier_column = "sleeve"
    temporal_granule_column = "datetime_combined"

    # Identify relevant categorical/binned attributes to define formal intents
    formal_attribute_columns = [
        "RUL_Class",
        "steel_weight, tonn_BIN",
        "steel_temperature_grab1, Celsius deg._BIN",
        "resistance, tonn_BIN",
        "swing_frequency, amount/minute_BIN",
        "crystallizer_movement, mm_BIN",
        "alloy_speed, meter/minute_BIN",
        "water_consumption, liter/minute_BIN",
        "water_temperature_delta, Celsius deg._BIN",
        "temperature_measurement1, Celsius deg._BIN",
        "temperature_measurement2, Celsius deg._BIN"
    ]

    print("Initializing Temporal Concept Analysis engine...")
    analyzer = TemporalConceptAnalyzer(
        data_frame=raw_data,
        object_col=object_identifier_column,
        time_col=temporal_granule_column,
        attribute_cols=formal_attribute_columns
    )

    print("Step 1: Extracting Formal Semantic States...")
    mapped_dataframe = analyzer.compute_state_space()
    mapped_dataframe.to_csv(os.path.join(output_directory, "mapped_states_timeline.csv"), index=False)

    print("Step 2: Compiling State Dictionary Intent Mappings...")
    state_dictionary = {
        int(state_id): list(intent)
        for state_id, intent in analyzer.state_id_to_intents.items()
    }
    with open(os.path.join(output_directory, "state_definitions_intent.json"), "w") as json_file:
        json.dump(state_dictionary, json_file, indent=4)

    print("Step 3: Extracting Object Asset Life-Tracks...")
    extracted_tracks = analyzer.extract_life_tracks()
    with open(os.path.join(output_directory, "object_life_tracks.json"), "w") as json_file:
        json.dump(extracted_tracks, json_file, indent=4)

    print("Step 4: Compiling State Transition Trajectories...")
    computed_transitions = analyzer.build_state_transitions()
    transition_list = [{"from_state": edge[0], "to_state": edge[1]} for edge in computed_transitions]
    transition_dataframe = pd.DataFrame(transition_list)
    transition_dataframe.to_csv(os.path.join(output_directory, "state_transitions.csv"), index=False)

    print("\n========================================================")
    print(f"Analysis successfully completed! Results saved to summary folder: '{output_directory}'")
    print(f" - mapped_states_timeline.csv       : Full timeline tagged with Formal State IDs.")
    print(f" - state_definitions_intent.json    : Exact description (intent) of every state.")
    print(f" - object_life_tracks.json          : Time-ordered trajectories per physical asset.")
    print(f" - state_transitions.csv            : Directed adjacency matrix connections.")
    print("========================================================\n")