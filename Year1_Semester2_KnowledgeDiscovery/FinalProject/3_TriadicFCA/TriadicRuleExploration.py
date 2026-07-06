import os
import argparse
import pandas as pd

def calculate_support(lhs, rhs, conditions, relations, objects):
    """
    Calculates support of
    (lhs U rhs) under given conditions.
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

    return count / len(objects)


# --------------------------------------------------------
# Rule Mining
# --------------------------------------------------------

def mine_rules(objects,
               attributes,
               conditions,
               relations,
               min_support,
               min_confidence):

    rules = []

    for condition in conditions:

        for antecedent in attributes:

            for consequent in attributes:

                if antecedent == consequent:
                    continue

                supp_A = calculate_support(
                    [antecedent],
                    [],
                    [condition],
                    relations,
                    objects
                )

                if supp_A == 0:
                    continue

                supp_AB = calculate_support(
                    [antecedent],
                    [consequent],
                    [condition],
                    relations,
                    objects
                )

                confidence = supp_AB / supp_A

                if supp_AB >= min_support and confidence >= min_confidence:

                    rules.append({

                        "Rule":
                        f"{{{antecedent}}} -> {{{consequent}}} | {{{condition}}}",

                        "Support":
                        round(supp_AB, 4),

                        "Confidence":
                        round(confidence, 4)

                    })

    return rules


# --------------------------------------------------------
# Main
# --------------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description="Mine Triadic Association Rules"
    )

    parser.add_argument(
        "--input",
        default="Final_Processed_Steel_Data_Clean_V2_Triadic_Reduced_5_Sleeves.csv",
        help="Triadic context CSV"
    )

    parser.add_argument(
        "--output",
        default="Final_Processed_Steel_Data_Clean_V2_Triadic_Reduced_5_Sleeves_Rules.csv",
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
        default=0.80
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

    rules = sorted(
        rules,
        key=lambda x: (x["Confidence"], x["Support"]),
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