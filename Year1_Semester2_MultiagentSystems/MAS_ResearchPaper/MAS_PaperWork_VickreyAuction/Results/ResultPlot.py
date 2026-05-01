import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


# ================= LOAD DATA =================
df = pd.read_csv("vickrey_auction_results.csv")


# ================= OUTPUT DIR =================
OUT_DIR = "vickrey_plots"
os.makedirs(OUT_DIR, exist_ok=True)


# ================= GLOBAL STYLE =================
plt.rcParams["figure.figsize"] = (10, 5)


def save_plot(name):
    path = os.path.join(OUT_DIR, name)
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close()   # IMPORTANT: prevents memory leaks + GUI dependency


# ================= PRECOMPUTE COLUMNS =================
bid_cols = [c for c in df.columns if "_Bid" in c]
profit_cols = [c for c in df.columns if "_Profit" in c]


# ================= PLOTS =================

# 1. Winning bid over time
plt.figure()
plt.plot(df["Round"], df["Winning_Bid"])
plt.title("Winning Bid Over Time")
plt.xlabel("Round")
plt.ylabel("Winning Bid")
save_plot("01_winning_bid.png")


# 2. Second price over time
plt.figure()
plt.plot(df["Round"], df["Second_Price"])
plt.title("Second Price Evolution")
plt.xlabel("Round")
plt.ylabel("Second Price")
save_plot("02_second_price.png")


# 3. Efficiency gap
plt.figure()
plt.plot(df["Round"], df["Winning_Bid"] - df["Second_Price"])
plt.title("Winner Surplus Gap (Bid - Price)")
plt.xlabel("Round")
plt.ylabel("Gap")
save_plot("03_efficiency_gap.png")


# 4. Winner frequency
plt.figure()
df["Winner_ID"].value_counts().plot(kind="bar")
plt.title("Win Frequency per Agent")
plt.xlabel("Agent ID")
plt.ylabel("Wins")
save_plot("04_winner_frequency.png")


# 5. Avg bid per agent
avg_bids = {c: df[c].mean() for c in bid_cols}
plt.figure()
plt.bar(avg_bids.keys(), avg_bids.values())
plt.title("Average Bid per Agent")
plt.xticks(rotation=90)
save_plot("05_avg_bid.png")


# 6. Avg true value per agent
val_cols = [c for c in df.columns if "_TrueVal" in c]
avg_vals = {c: df[c].mean() for c in val_cols}
plt.figure()
plt.bar(avg_vals.keys(), avg_vals.values())
plt.title("Average True Valuation per Agent")
plt.xticks(rotation=90)
save_plot("06_avg_true_value.png")


# 7. Avg profit per agent
avg_profit = {c: df[c].mean() for c in profit_cols}
plt.figure()
plt.bar(avg_profit.keys(), avg_profit.values())
plt.title("Average Profit per Agent")
plt.xticks(rotation=90)
save_plot("07_avg_profit.png")


# 8. Total profit per agent
total_profit = {c: df[c].sum() for c in profit_cols}
plt.figure()
plt.bar(total_profit.keys(), total_profit.values())
plt.title("Total Profit per Agent")
plt.xticks(rotation=90)
save_plot("08_total_profit.png")


# 9. Bid dispersion
df["Bid_STD"] = df[bid_cols].std(axis=1)
plt.figure()
plt.plot(df["Round"], df["Bid_STD"])
plt.title("Bid Dispersion Over Time")
plt.xlabel("Round")
plt.ylabel("STD of Bids")
save_plot("09_bid_dispersion.png")


# 10. Mean bid evolution
df["Mean_Bid"] = df[bid_cols].mean(axis=1)
plt.figure()
plt.plot(df["Round"], df["Mean_Bid"])
plt.title("Mean Bid Evolution")
plt.xlabel("Round")
plt.ylabel("Mean Bid")
save_plot("10_mean_bid.png")


# 11. Bid vs price scatter
plt.figure()
plt.scatter(df["Winning_Bid"], df["Second_Price"])
plt.title("Winning Bid vs Second Price")
plt.xlabel("Winning Bid")
plt.ylabel("Second Price")
save_plot("11_bid_vs_price.png")


# 12. Revenue
plt.figure()
plt.plot(df["Round"], df["Second_Price"])
plt.title("Auction Revenue (Second Price)")
plt.xlabel("Round")
plt.ylabel("Revenue")
save_plot("12_revenue.png")


# 13. Profit distribution
all_profits = pd.concat([df[c] for c in profit_cols])
plt.figure()
plt.hist(all_profits, bins=30)
plt.title("Profit Distribution (All Agents)")
save_plot("13_profit_distribution.png")


# 14. Total profit distribution
plt.figure()
plt.hist(df[[c for c in df.columns if "_TotalProfit" in c]].sum(axis=0), bins=10)
plt.title("Total Profit Distribution")
save_plot("14_total_profit_distribution.png")


# 15. Strategy distribution
strategy_cols = [c for c in df.columns if "_Strategy" in c]
strategies = pd.Series(df[strategy_cols].values.flatten()).value_counts()
plt.figure()
strategies.plot(kind="bar")
plt.title("Strategy Distribution")
plt.xticks(rotation=90)
save_plot("15_strategy_distribution.png")


# 16. Markup dynamics
plt.figure()
plt.plot(df["Round"], df["Winning_Bid"] - df["Second_Price"])
plt.title("Auction Markup Dynamics")
save_plot("16_markup.png")


# 17. Winning bid volatility
plt.figure()
plt.plot(df["Round"], df["Winning_Bid"].rolling(5).std())
plt.title("Winning Bid Volatility")
save_plot("17_winning_volatility.png")


# 18. Second price volatility
plt.figure()
plt.plot(df["Round"], df["Second_Price"].rolling(5).std())
plt.title("Second Price Volatility")
save_plot("18_second_price_volatility.png")


# 19. Correlation heatmap
bid_matrix = df[bid_cols].corr()
plt.figure()
plt.imshow(bid_matrix, cmap="coolwarm")
plt.title("Bid Correlation Matrix")
plt.colorbar()
save_plot("19_correlation_heatmap.png")


# 20. Winner turnover dynamics
winner_series = df["Winner_ID"].astype(str)
winner_change = (winner_series != winner_series.shift()).cumsum()

plt.figure()
plt.plot(df["Round"], winner_change)
plt.title("Winner Turnover Dynamics")
plt.xlabel("Round")
plt.ylabel("Change Events")
save_plot("20_winner_turnover.png")