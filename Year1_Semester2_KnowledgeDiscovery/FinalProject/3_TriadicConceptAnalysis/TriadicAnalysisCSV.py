import pandas as pd
import argparse

INPUT = "Final_Processed_Steel_Data_Clean_V2.csv"
OUTPUT = "Final_Processed_Steel_Data_Clean_V2_Triadic.csv"

OBJECT_COLUMN = "sleeve"

ATTRIBUTE_COLUMNS = [
    "steel_type",
    "workpiece_slice_geometry",
    "alloy_type",
    "FCA_BIN",
    "num_stream_BIN",
    "num_crystallizer_BIN"
]

CONDITION_COLUMNS = [
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
    "temperature_measurement2_Celsius_BIN"
]


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--threshold", type=float, default=0.60)
    parser.add_argument("--min-support", type=int, default=10)

    args = parser.parse_args()

    df = pd.read_csv(INPUT)

    triplets = []

    grouped = df.groupby(OBJECT_COLUMN)

    for sleeve, group in grouped:

        if len(group) < args.min_support:
            continue

        for attr in ATTRIBUTE_COLUMNS:

            values = group[attr].unique()

            for value in values:

                subset = group[group[attr] == value]

                if len(subset) == 0:
                    continue

                for cond in CONDITION_COLUMNS:

                    counts = subset[cond].value_counts()

                    for cond_value, cnt in counts.items():

                        ratio = cnt / len(subset)

                        if ratio >= args.threshold:

                            triplets.append({

                                "Object": sleeve,

                                "Attribute": f"{attr}={value}",

                                "Condition": f"{cond}={cond_value}"

                            })

    result = pd.DataFrame(triplets)

    result.to_csv(OUTPUT, index=False)

    print()

    print("=" * 60)

    print("TRIADIC CONTEXT SUMMARY")

    print("=" * 60)

    print("Objects:", result["Object"].nunique())

    print("Attributes:", result["Attribute"].nunique())

    print("Conditions:", result["Condition"].nunique())

    print("Triples:", len(result))

    density = len(result) / (

        result["Object"].nunique()

        * result["Attribute"].nunique()

        * result["Condition"].nunique()

    )

    print("Density:", f"{density:.2%}")

    print("=" * 60)


if __name__ == "__main__":
    main()