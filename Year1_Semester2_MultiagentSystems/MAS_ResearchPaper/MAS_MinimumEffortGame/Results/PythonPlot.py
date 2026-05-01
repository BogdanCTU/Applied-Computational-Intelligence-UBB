import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ================= LOAD DATA =================
df = pd.read_csv("SIM_20Agents_100Rounds.csv", sep=None, engine="python")

# ================= CONFIG =================
round_col = "Round"
min_effort_col = "Min_Effort"

# Extract agent columns dynamically
strategy_cols = [c for c in df.columns if "_Strategy" in c]
effort_cols = [c for c in df.columns if "_Effort" in c]
payoff_cols = [c for c in df.columns if "_Payoff" in c]

# ================= STYLE =================
sns.set_theme(style="darkgrid")

# ============================================================
# 1. GLOBAL MIN EFFORT EVOLUTION
# ============================================================
plt.figure()
plt.plot(df[round_col], df[min_effort_col], marker="o")
plt.title("Global Minimum Effort Over Time")
plt.xlabel("Round")
plt.ylabel("Min Effort")
plt.tight_layout()
plt.savefig("01_min_effort_trend.png")
plt.close()

# ============================================================
# 2. AVERAGE EFFORT PER ROUND
# ============================================================
avg_effort = df[effort_cols].mean(axis=1)

plt.figure()
plt.plot(df[round_col], avg_effort, marker="o")
plt.title("Average Effort Across Agents")
plt.xlabel("Round")
plt.ylabel("Average Effort")
plt.tight_layout()
plt.savefig("02_avg_effort.png")
plt.close()

# ============================================================
# 3. HEATMAP: EFFORT EVOLUTION (Agents vs Rounds)
# ============================================================
effort_matrix = df[effort_cols].T

plt.figure(figsize=(12, 6))
sns.heatmap(effort_matrix, cmap="viridis")
plt.title("Agent Effort Heatmap (Evolution Over Rounds)")
plt.xlabel("Round Index")
plt.ylabel("Agents")
plt.tight_layout()
plt.savefig("03_effort_heatmap.png")
plt.close()

# ============================================================
# 4. PAYOFF DISTRIBUTION OVER TIME
# ============================================================
avg_payoff = df[payoff_cols].mean(axis=1)

plt.figure()
plt.plot(df[round_col], avg_payoff, marker="o", color="green")
plt.title("Average Payoff Over Time")
plt.xlabel("Round")
plt.ylabel("Payoff")
plt.tight_layout()
plt.savefig("04_avg_payoff.png")
plt.close()

# ============================================================
# 5. STRATEGY FREQUENCY (STATIC OVERALL)
# ============================================================
all_strategies = df[strategy_cols].iloc[0].values
strategy_counts = pd.Series(all_strategies).value_counts()

plt.figure(figsize=(10, 5))
strategy_counts.plot(kind="bar")
plt.title("Strategy Distribution")
plt.xlabel("Strategy")
plt.ylabel("Count")
plt.tight_layout()
plt.savefig("05_strategy_distribution.png")
plt.close()

# ============================================================
# 6. STRATEGY PERFORMANCE (AVG PAYOFF)
# ============================================================
strategy_perf = {}

for i in range(1, len(strategy_cols) + 1):
    strat = df[f"P{i}_Strategy"]
    payoff = df[f"P{i}_Payoff"]
    for s, p in zip(strat, payoff):
        strategy_perf.setdefault(s, []).append(p)

avg_strategy_perf = {k: sum(v)/len(v) for k, v in strategy_perf.items()}

plt.figure(figsize=(10, 5))
pd.Series(avg_strategy_perf).sort_values().plot(kind="bar")
plt.title("Average Payoff per Strategy")
plt.xlabel("Strategy")
plt.ylabel("Avg Payoff")
plt.tight_layout()
plt.savefig("06_strategy_performance.png")
plt.close()

# ============================================================
# 7. EFFORT DISTRIBUTION (BOXPLOT ACROSS AGENTS)
# ============================================================
plt.figure(figsize=(12, 6))
sns.boxplot(data=df[effort_cols])
plt.title("Effort Distribution Across Agents")
plt.xticks(rotation=90)
plt.tight_layout()
plt.savefig("07_effort_boxplot.png")
plt.close()

# ============================================================
# 8. PAYOFF DISTRIBUTION (BOXPLOT)
# ============================================================
plt.figure(figsize=(12, 6))
sns.boxplot(data=df[payoff_cols])
plt.title("Payoff Distribution Across Agents")
plt.xticks(rotation=90)
plt.tight_layout()
plt.savefig("08_payoff_boxplot.png")
plt.close()

print("All plots generated successfully.")