import os
import argparse
import pandas as pd

def calculate_support(lhs, rhs, conditions, relations, objects):
    """
    Calculates the count of objects that meet the given criteria.
    Returns an integer representing the raw count.
    """
    required = set(lhs) | set(rhs)
    count = 0

    for obj in objects:
        valid = True
        for cond in conditions:
            for attr in required:
                if (obj, attr, cond) not in relations:
                    valid = False
                    break
            if not valid:
                break
        if valid:
            count += 1

    return count


# --------------------------------------------------------
# Rule Mining
# --------------------------------------------------------

def mine_rules(objects,
               attributes,
               conditions,
               relations,
               min_support,
               min_confidence):
    """
    Generates association rules that meet minimum support and confidence thresholds.
    Formats the support metric as a fraction string.
    """
    rules = []
    total_objects = len(objects)

    for condition in conditions:
        for antecedent in attributes:
            for consequent in attributes:

                if antecedent == consequent:
                    continue

                count_A = calculate_support(
                    [antecedent],
                    [],
                    [condition],
                    relations,
                    objects
                )

                if count_A == 0:
                    continue

                count_AB = calculate_support(
                    [antecedent],
                    [consequent],
                    [condition],
                    relations,
                    objects
                )

                support_ratio = count_AB / total_objects
                confidence = count_AB / count_A

                if support_ratio >= min_support and confidence >= min_confidence:
                    rules.append({
                        "Rule": f"{{{antecedent}}} -> {{{consequent}}} | {{{condition}}}",
                        "Support": f"{count_AB}/{total_objects}",
                        "Confidence": round(confidence, 4)
                    })

    return rules


# --------------------------------------------------------
# Main
# --------------------------------------------------------

def main():
    """
    Parses command line arguments, loads data, and executes rule mining.
    Sorts the rules and exports the final list to a CSV file.
    """
    parser = argparse.ArgumentParser(
        description="Mine Triadic Association Rules"
    )

    parser.add_argument(
        "--input",
        default="Final_Processed_Steel_Data_Clean_V2_Triadic_Reduced_5_Sleeves_V2.csv",
        help="Triadic context CSV"
    )

    parser.add_argument(
        "--output",
        default="Final_Processed_Steel_Data_Clean_V2_Triadic_Reduced_5_Sleeves_V2_Rules.csv",
        help="Output CSV"
    )

    parser.add_argument(
        "--min-support",
        type=float,
        default=0.50
    )

    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.50
    )

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print("Input file not found.")
        return

    df = pd.read_csv(args.input)
    df.columns = ["Object", "Attribute", "Condition"]

    relations = set(
        tuple(x)
        for x in df[["Object", "Attribute", "Condition"]].values
    )

    objects = sorted(df["Object"].unique())
    attributes = sorted(df["Attribute"].unique())
    conditions = sorted(df["Condition"].unique())

    print("=" * 60)
    print("TRIADIC CONTEXT")
    print("=" * 60)
    print(f"Objects    : {len(objects)}")
    print(f"Attributes : {len(attributes)}")
    print(f"Conditions : {len(conditions)}")
    print(f"Relations  : {len(relations)}")
    print("=" * 60)

    rules = mine_rules(
        objects,
        attributes,
        conditions,
        relations,
        args.min_support,
        args.min_confidence
    )

    # Convert the string fraction back to a float for correct mathematical sorting
    rules = sorted(
        rules,
        key=lambda x: (
            x["Confidence"],
            float(x["Support"].split('/')[0]) / float(x["Support"].split('/')[1])
        ),
        reverse=True
    )

    result = pd.DataFrame(rules)
    result.to_csv(args.output, index=False)

    print()
    print(f"Mined {len(result)} rules.")
    print()

    if len(result):
        print(result.to_string(index=False))

    print()
    print(f"Rules saved to {args.output}")


if __name__ == "__main__":
    main()