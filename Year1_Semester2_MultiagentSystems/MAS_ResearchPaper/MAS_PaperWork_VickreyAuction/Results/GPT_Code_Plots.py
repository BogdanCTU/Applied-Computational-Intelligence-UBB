import pandas as pd
import matplotlib.pyplot as plt

# -----------------------------
# Configuration
# -----------------------------
INPUT_FILE = "vickrey_auction_results.csv"

players = {
    "truthful_P1": "P1 Truthful",
    "random_reasonable_P2": "P2 Random Reasonable",
    "underbid_bayesian_P3": "P3 Underbid Bayesian",
    "overbid_P4": "P4 Overbid",
    "noisybr_P5": "P5 Noisy Best Response",
}

plt.rcParams["font.family"] = "DejaVu Sans"

# -----------------------------
# Load Data
# -----------------------------
df = pd.read_csv(INPUT_FILE)

# Remove accidental unnamed empty columns if present
df = df.loc[:, ~df.columns.str.contains(r"^Unnamed")]

# Ensure numeric columns
for col in df.columns:
    if col != "Winner_ID":
        df[col] = pd.to_numeric(df[col], errors="coerce")

rounds = df["Round"]

# -----------------------------
# Helper Functions
# -----------------------------
def save_plot(title):
    safe_title = (
        title.lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("-", "_")
        .replace("(", "")
        .replace(")", "")
    )
    plt.title(title)
    plt.tight_layout()
    plt.savefig(f"{safe_title}.png", dpi=300, bbox_inches="tight")
    plt.close()


def line_plot(x, y, title, xlabel, ylabel):
    plt.figure(figsize=(10, 6))
    plt.plot(x, y, marker="o")
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    save_plot(title)


def multi_line_plot(x, ys_dict, title, xlabel, ylabel):
    plt.figure(figsize=(12, 7))
    for label, y in ys_dict.items():
        plt.plot(x, y, marker="o", label=label)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.legend()
    save_plot(title)


def bar_plot(categories, values, title, xlabel, ylabel):
    plt.figure(figsize=(10, 6))
    plt.bar(categories, values)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks(rotation=20)
    save_plot(title)


def scatter_plot(x, y, title, xlabel, ylabel):
    plt.figure(figsize=(10, 6))
    plt.scatter(x, y)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    save_plot(title)


def histogram_plot(values, title, xlabel, ylabel="Frequency"):
    plt.figure(figsize=(10, 6))
    plt.hist(values, bins=10)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    save_plot(title)


# -----------------------------
# Plot 1–5: True Values per Player
# -----------------------------
for prefix, label in players.items():
    line_plot(
        rounds,
        df[f"{prefix}_TrueVal"],
        f"{label} True Value by Round",
        "Round",
        "True Value",
    )

# -----------------------------
# Plot 6–10: Bids per Player
# -----------------------------
for prefix, label in players.items():
    line_plot(
        rounds,
        df[f"{prefix}_Bid"],
        f"{label} Bid by Round",
        "Round",
        "Bid",
    )

# -----------------------------
# Plot 11–15: Profit per Player
# -----------------------------
for prefix, label in players.items():
    line_plot(
        rounds,
        df[f"{prefix}_Profit"],
        f"{label} Profit by Round",
        "Round",
        "Profit",
    )

# -----------------------------
# Plot 16–20: Total Profit per Player
# -----------------------------
for prefix, label in players.items():
    line_plot(
        rounds,
        df[f"{prefix}_TotalProfit"],
        f"{label} Cumulative Profit by Round",
        "Round",
        "Total Profit",
    )

# -----------------------------
# Plot 21: All Bids Comparison
# -----------------------------
multi_line_plot(
    rounds,
    {label: df[f"{prefix}_Bid"] for prefix, label in players.items()},
    "All Players Bid Comparison",
    "Round",
    "Bid",
)

# -----------------------------
# Plot 22: All True Values Comparison
# -----------------------------
multi_line_plot(
    rounds,
    {label: df[f"{prefix}_TrueVal"] for prefix, label in players.items()},
    "All Players True Value Comparison",
    "Round",
    "True Value",
)

# -----------------------------
# Plot 23: All Profits Comparison
# -----------------------------
multi_line_plot(
    rounds,
    {label: df[f"{prefix}_Profit"] for prefix, label in players.items()},
    "All Players Profit Comparison",
    "Round",
    "Profit",
)

# -----------------------------
# Plot 24: All Total Profits Comparison
# -----------------------------
multi_line_plot(
    rounds,
    {label: df[f"{prefix}_TotalProfit"] for prefix, label in players.items()},
    "All Players Cumulative Profit Comparison",
    "Round",
    "Total Profit",
)

# -----------------------------
# Plot 25: Winning Bid vs Second Price
# -----------------------------
multi_line_plot(
    rounds,
    {
        "Winning Bid": df["Winning_Bid"],
        "Second Price": df["Second_Price"],
    },
    "Winning Bid vs Second Price",
    "Round",
    "Value",
)

# -----------------------------
# Plot 26: Winner Frequency
# -----------------------------
winner_counts = df["Winner_ID"].value_counts().sort_index()
bar_plot(
    [f"P{int(i)}" for i in winner_counts.index],
    winner_counts.values,
    "Winner Frequency by Player",
    "Player",
    "Wins",
)

# -----------------------------
# Plot 27: Bid vs True Value Scatter (All Players)
# -----------------------------
all_true_values = []
all_bids = []

for prefix in players:
    all_true_values.extend(df[f"{prefix}_TrueVal"].tolist())
    all_bids.extend(df[f"{prefix}_Bid"].tolist())

scatter_plot(
    all_true_values,
    all_bids,
    "Bid vs True Value Scatter",
    "True Value",
    "Bid",
)

# -----------------------------
# Plot 28: Winning Bid Histogram
# -----------------------------
histogram_plot(
    df["Winning_Bid"],
    "Winning Bid Distribution",
    "Winning Bid",
)

# -----------------------------
# Plot 29: Second Price Histogram
# -----------------------------
histogram_plot(
    df["Second_Price"],
    "Second Price Distribution",
    "Second Price",
)

# -----------------------------
# Plot 30: Average Bid per Player
# -----------------------------
avg_bids = {
    label: df[f"{prefix}_Bid"].mean()
    for prefix, label in players.items()
}

bar_plot(
    list(avg_bids.keys()),
    list(avg_bids.values()),
    "Average Bid per Player",
    "Player",
    "Average Bid",
)
