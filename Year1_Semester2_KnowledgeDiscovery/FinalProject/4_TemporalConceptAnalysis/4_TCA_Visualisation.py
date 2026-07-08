"""
=============================================================================
Script 4 - TCA Visualisation
=============================================================================
Temporal Concept Analysis (TCA) - Continuous Casting Machine Dataset

INPUT  : tca_s3_analysis.csv   (output of Script 3)
OUTPUT : tca_s4_figures.pdf    (all 10 figures in one multi-page PDF)

What it does
------------
Reads the multi-section CSV produced by Script 3 (filtered by record_type)
and produces 10 publication-quality figures, all saved into a SINGLE
multi-page PDF:

  Page 1  - Attribute Prevalence Heatmap
  Page 2  - RUL Category Prevalence Over Time (line)
  Page 3  - Key Attribute Prevalence (5-panel faceted lines)
  Page 4  - Concept Lifespan Histogram
  Page 5  - Concept Classification Pie Chart
  Page 6  - Daily Concept Count Evolution
  Page 7  - Life-Track Timeline (top-lived + ephemeral concepts)
  Page 8  - Concept Birth & Death per Day
  Page 9  - Temporal Complexity (concepts vs objects, intent vs extent size)
  Page 10 - Steel Type Prevalence Heatmap

Usage
-----
  python script4_tca_visualisation.py
=============================================================================
"""

import warnings
from pathlib import Path

import matplotlib
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import LinearSegmentedColormap

matplotlib.use("Agg")
warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths  (single input -> single output)
# ---------------------------------------------------------------------------

BASE_DIR   = Path(__file__).parent
INPUT_CSV  = BASE_DIR / "tca_s3_analysis.csv"
OUTPUT_PDF = BASE_DIR / "tca_s4_figures.pdf"

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

plt.rcParams.update({
    "font.family":       "DejaVu Sans",
    "font.size":         10,
    "axes.titlesize":    13,
    "axes.labelsize":    11,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "figure.dpi":        150,
    "savefig.dpi":       180,
    "savefig.facecolor": "white",
})

C_CRITICAL = "#e63946"
C_LOW      = "#f4a261"
C_MEDIUM   = "#2a9d8f"
C_HEALTHY  = "#457b9d"

LEVEL_COLOURS = {
    "Critical": C_CRITICAL, "Low": C_LOW,
    "Medium":   C_MEDIUM,   "Healthy": C_HEALTHY,
    "High":     C_CRITICAL,
}

KEY_ATTRS = {
    "RUL_BIN":                            ["Critical", "Low", "Medium", "Healthy"],
    "steel_temperature_grab1Celsius_BIN": ["High", "Medium", "Low"],
    "resistance_tonn_BIN":                ["High", "Medium", "Low"],
    "water_consumption_BIN":              ["High", "Medium", "Low"],
    "alloy_speed_meter_minute_BIN":       ["High", "Medium", "Low"],
}


# ---------------------------------------------------------------------------
# Data loader
# ---------------------------------------------------------------------------

def load_sections(csv_path: Path):
    """Return a dict of DataFrames keyed by record_type."""
    df = pd.read_csv(csv_path, low_memory=False)
    if "record_type" not in df.columns:
        raise ValueError("Input CSV must have a 'record_type' column (Script 3 output).")

    sections = {rt: df[df["record_type"] == rt].copy() for rt in df["record_type"].unique()}
    for rt, sub in sections.items():
        print(f"  record_type={rt:<15}: {len(sub):>5,} rows")
    return sections


# ---------------------------------------------------------------------------
# Axis helpers
# ---------------------------------------------------------------------------

def date_ticks(ax, dates, max_ticks=12):
    step = max(1, len(dates) // max_ticks)
    ax.set_xticks(range(0, len(dates), step))
    ax.set_xticklabels(
        [str(dates[i]) for i in range(0, len(dates), step)],
        rotation=45, ha="right", fontsize=8,
    )


# ---------------------------------------------------------------------------
# Page 1 – Attribute Prevalence Heatmap
# ---------------------------------------------------------------------------

def page_prevalence_heatmap(pdf, prev_df):
    selected = {
        "RUL_BIN=Critical":                         "RUL Critical",
        "RUL_BIN=Low":                              "RUL Low",
        "RUL_BIN=Medium":                           "RUL Medium",
        "RUL_BIN=Healthy":                          "RUL Healthy",
        "steel_temperature_grab1Celsius_BIN=High":  "Temp High",
        "steel_temperature_grab1Celsius_BIN=Medium": "Temp Medium",
        "steel_temperature_grab1Celsius_BIN=Low":   "Temp Low",
        "alloy_speed_meter_minute_BIN=High":        "Alloy Speed High",
        "alloy_speed_meter_minute_BIN=Medium":        "Alloy Speed Medium",
        "alloy_speed_meter_minute_BIN=Low":        "Alloy Speed Low",
        "water_consumption_BIN=High":              "Water High",
        "water_consumption_BIN=Medium":           "Water Medium",
        "water_consumption_BIN=Low":              "Water Low",
        "steel_weighttonn_BIN=High":                "Weight High",
        "steel_weighttonn_BIN=Medium":                "Weight Medium",
        "steel_weighttonn_BIN=Low":                "Weight Low"
    }

    prev_df = prev_df.copy()
    prev_df["attr_level"] = prev_df["attribute"] + "=" + prev_df["level"].astype(str)

    pivot = prev_df[prev_df["attr_level"].isin(selected)].pivot_table(
        index="attr_level", columns="date", values="prevalence_pct", aggfunc="mean"
    )
    if pivot.empty:
        return
    pivot.index = [selected.get(i, i) for i in pivot.index]

    # Trim columns for readability
    if pivot.shape[1] > 30:
        pivot = pivot.iloc[:, :: pivot.shape[1] // 30]
    pivot.columns = [str(c)[5:] for c in pivot.columns]   # MM-DD

    cmap = LinearSegmentedColormap.from_list("tca", ["#eaf4fb", "#1a78c2", "#0d2137"])
    fig, ax = plt.subplots(figsize=(max(12, pivot.shape[1] * 0.36), 5))
    im = ax.imshow(pivot.values, aspect="auto", cmap=cmap, vmin=0, vmax=100)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=9)
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=70, ha="right", fontsize=7)
    ax.set_title("Figure 1 - Attribute Prevalence Heatmap (% concepts per day)", pad=10)
    ax.set_xlabel("Date (MM-DD)")
    ax.set_ylabel("Attribute = Level")
    cb = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
    cb.set_label("Prevalence (%)")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            v = pivot.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.0f}", ha="center", va="center",
                        fontsize=6, color="white" if v > 60 else "black")
    fig.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print("  Page 1  saved.")


# ---------------------------------------------------------------------------
# Page 2 – RUL Prevalence Line
# ---------------------------------------------------------------------------

def page_rul_line(pdf, prev_df):
    rul = prev_df[prev_df["attribute"] == "RUL_BIN"].copy()
    rul["date"] = pd.to_datetime(rul["date"])
    rul.sort_values("date", inplace=True)
    dates = sorted(rul["date"].unique())

    fig, ax = plt.subplots(figsize=(13, 5))
    for level, colour in [("Healthy", C_HEALTHY), ("Medium", C_MEDIUM),
                           ("Low", C_LOW), ("Critical", C_CRITICAL)]:
        sub = rul[rul["level"] == level]
        if sub.empty:
            continue
        series = sub.set_index("date").reindex(dates)["prevalence_pct"].fillna(0)
        ax.plot(range(len(dates)), series.values, marker="o", markersize=3,
                linewidth=1.8, color=colour, label=f"RUL {level}")
        ax.fill_between(range(len(dates)), series.values, alpha=0.08, color=colour)

    date_ticks(ax, dates)
    ax.set_xlabel("Date")
    ax.set_ylabel("Prevalence (%)")
    ax.set_title("Figure 2 - RUL Category Prevalence Over Time")
    ax.legend(loc="upper right", framealpha=0.9)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    fig.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print("  Page 2  saved.")


# ---------------------------------------------------------------------------
# Page 3 – Key Attributes Faceted Lines
# ---------------------------------------------------------------------------

def page_key_attrs(pdf, prev_df):
    prev_df = prev_df.copy()
    prev_df["date"] = pd.to_datetime(prev_df["date"])
    all_dates = sorted(prev_df["date"].unique())

    attrs = list(KEY_ATTRS.keys())
    fig, axes = plt.subplots(len(attrs), 1, figsize=(13, 3 * len(attrs)), sharex=True)
    if len(attrs) == 1:
        axes = [axes]

    for ax, attr in zip(axes, attrs):
        sub = prev_df[prev_df["attribute"] == attr]
        for level in KEY_ATTRS[attr]:
            lvl = sub[sub["level"] == level]
            if lvl.empty:
                continue
            series = lvl.set_index("date").reindex(all_dates)["prevalence_pct"].fillna(0)
            ax.plot(range(len(all_dates)), series.values, label=level,
                    color=LEVEL_COLOURS.get(level, "#555"), linewidth=1.6,
                    marker=".", markersize=3)
        ax.set_ylabel("Prevalence (%)", fontsize=8)
        ax.set_title(attr.replace("_BIN", "").replace("_", " ").title(), fontsize=10, loc="left")
        ax.legend(loc="upper right", fontsize=8, framealpha=0.8)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter())

    date_ticks(axes[-1], all_dates)
    axes[-1].set_xlabel("Date")
    fig.suptitle("Figure 3 - Key Attribute Prevalence Over Time", y=1.01, fontsize=13)
    fig.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print("  Page 3  saved.")


# ---------------------------------------------------------------------------
# Page 4 – Lifespan Histogram
# ---------------------------------------------------------------------------

def page_lifespan_hist(pdf, lt_df):
    lt_df = lt_df.copy()
    lt_df["lifespan"] = pd.to_numeric(lt_df["lifespan"], errors="coerce")
    lt_df.dropna(subset=["lifespan"], inplace=True)

    fig, ax = plt.subplots(figsize=(10, 5))
    max_ls = int(lt_df["lifespan"].max())
    bins   = min(max_ls, 50)
    ax.hist(lt_df["lifespan"], bins=bins, color="#1982c4", edgecolor="white",
            linewidth=0.5, alpha=0.85)

    for lo_frac, hi_frac, colour, label in [
        (0.70, 1.00, "#2a9d8f", "Universal / Long-lived (>=70%)"),
        (0.30, 0.70, "#f4a261", "Medium-lived (30-69%)"),
        (0.00, 0.30, "#e63946", "Short-lived / Ephemeral (<30%)"),
    ]:
        ax.axvspan(max_ls * lo_frac, max_ls * hi_frac, alpha=0.10, color=colour, label=label)

    ax.set_xlabel("Lifespan (days alive)")
    ax.set_ylabel("Number of Concepts")
    ax.set_title("Figure 4 - Concept Lifespan Distribution")
    ax.legend(loc="upper right", fontsize=8)
    stats_txt = (f"n = {len(lt_df):,}\n"
                 f"median = {lt_df['lifespan'].median():.0f}\n"
                 f"mean = {lt_df['lifespan'].mean():.1f}")
    ax.text(0.98, 0.98, stats_txt, transform=ax.transAxes, fontsize=8,
            va="top", ha="right", bbox=dict(boxstyle="round,pad=0.4", fc="white", alpha=0.8))
    fig.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print("  Page 4  saved.")


# ---------------------------------------------------------------------------
# Page 5 – Classification Pie
# ---------------------------------------------------------------------------

def page_classification_pie(pdf, lt_df):
    cats    = ["Universal", "Long-lived", "Medium-lived", "Short-lived", "Ephemeral"]
    colours = ["#2a9d8f",   "#457b9d",    "#f4a261",      "#e76f51",     "#e63946"]
    counts  = [(lt_df["classification"] == c).sum() for c in cats]

    non_zero = [(f"{c}\n({n:,})", col, n)
                for c, col, n in zip(cats, colours, counts) if n > 0]
    if not non_zero:
        return
    labels_f, colours_f, counts_f = zip(*non_zero)

    fig, ax = plt.subplots(figsize=(8, 7))
    _, _, autotexts = ax.pie(
        counts_f, labels=labels_f, colors=colours_f,
        autopct="%1.1f%%", startangle=140,
        pctdistance=0.75, labeldistance=1.12,
        wedgeprops={"linewidth": 1.5, "edgecolor": "white"},
    )
    for at in autotexts:
        at.set_fontsize(9)
    ax.set_title("Figure 5 - Concept Classification by Lifespan", pad=14)
    fig.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print("  Page 5  saved.")


# ---------------------------------------------------------------------------
# Page 6 – Daily Concept Count
# ---------------------------------------------------------------------------

def page_daily_count(pdf, ls_df):
    ls_df = ls_df.copy()
    ls_df["date"] = pd.to_datetime(ls_df["date"])
    ls_df["n_concepts"] = pd.to_numeric(ls_df["n_concepts"], errors="coerce")
    ls_df.sort_values("date", inplace=True)
    dates  = ls_df["date"].tolist()
    counts = ls_df["n_concepts"].tolist()
    x      = list(range(len(dates)))

    fig, ax = plt.subplots(figsize=(13, 5))
    ax.bar(x, counts, color="#1982c4", alpha=0.70, width=0.8, label="# Concepts")
    if len(counts) > 3:
        z = np.polyfit(x, counts, 2)
        p = np.poly1d(z)
        ax.plot(x, p(x), color="#e63946", linewidth=2.2, linestyle="--", label="Trend (poly-2)")
    date_ticks(ax, dates)
    ax.set_xlabel("Date")
    ax.set_ylabel("Number of Formal Concepts")
    ax.set_title("Figure 6 - Daily Concept Count Evolution")
    ax.legend(framealpha=0.9)
    fig.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print("  Page 6  saved.")


# ---------------------------------------------------------------------------
# Page 7 – Life-Track Timeline
# ---------------------------------------------------------------------------

def page_life_track_timeline(pdf, lt_df):
    lt_df = lt_df.copy()
    lt_df["lifespan"] = pd.to_numeric(lt_df["lifespan"], errors="coerce")

    all_days_set = set()
    for val in lt_df["alive_days"].dropna():
        for d in str(val).split(" | "):
            all_days_set.add(d.strip())
    all_days = sorted(all_days_set)
    day_idx  = {d: i for i, d in enumerate(all_days)}

    # Top 8 longest-lived + 8 ephemeral
    top_long   = lt_df.nlargest(8, "lifespan")
    ephemeral  = lt_df[lt_df["lifespan"] == 1].head(8)
    selected   = pd.concat([top_long, ephemeral], ignore_index=True).drop_duplicates()

    fig, ax = plt.subplots(figsize=(14, max(5, len(selected) * 0.65)))
    for row_i, (_, row) in enumerate(selected.iterrows()):
        alive = [d.strip() for d in str(row["alive_days"]).split(" | ") if d.strip()]
        idxs  = [day_idx[d] for d in alive if d in day_idx]
        if not idxs:
            continue
        colour = "#2a9d8f" if row["lifespan"] > 1 else "#e63946"
        ax.scatter(idxs, [row_i] * len(idxs), color=colour, s=22, zorder=3)
        for k in range(len(idxs) - 1):
            if idxs[k + 1] - idxs[k] == 1:
                ax.plot([idxs[k], idxs[k + 1]], [row_i, row_i],
                        color=colour, linewidth=2, zorder=2)
        label = str(row["intent_str"])[:55] + ("..." if len(str(row["intent_str"])) > 55 else "")
        ax.text(-0.5, row_i, label, va="center", ha="right",
                fontsize=7, transform=ax.get_yaxis_transform())

    date_ticks(ax, all_days, max_ticks=15)
    ax.set_yticks([])
    ax.set_xlabel("Date")
    ax.set_title("Figure 7 - Life-Track Timeline (long-lived vs ephemeral)")
    ax.legend(handles=[
        mpatches.Patch(color="#2a9d8f", label="Long-lived"),
        mpatches.Patch(color="#e63946", label="Ephemeral"),
    ], loc="upper right", framealpha=0.9)
    fig.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print("  Page 7  saved.")


# ---------------------------------------------------------------------------
# Page 8 – Births & Deaths per Day
# ---------------------------------------------------------------------------

def page_births_deaths(pdf, bd_df):
    bd_df = bd_df.copy()
    bd_df["date"]     = pd.to_datetime(bd_df["date"])
    bd_df["n_births"] = pd.to_numeric(bd_df["n_births"], errors="coerce").fillna(0)
    bd_df["n_deaths"] = pd.to_numeric(bd_df["n_deaths"], errors="coerce").fillna(0)
    bd_df.sort_values("date", inplace=True)
    dates = bd_df["date"].tolist()
    x     = np.arange(len(dates))

    fig, ax = plt.subplots(figsize=(13, 5))
    width = 0.4
    ax.bar(x - width / 2, bd_df["n_births"], width=width, label="Births",
           color="#2a9d8f", alpha=0.85)
    ax.bar(x + width / 2, bd_df["n_deaths"], width=width, label="Deaths",
           color="#e63946", alpha=0.85)
    date_ticks(ax, dates)
    ax.set_xlabel("Date")
    ax.set_ylabel("Number of Concepts")
    ax.set_title("Figure 8 - Concept Birth & Death per Day")
    ax.legend(framealpha=0.9)
    fig.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print("  Page 8  saved.")


# ---------------------------------------------------------------------------
# Page 9 – Temporal Complexity
# ---------------------------------------------------------------------------

def page_temporal_complexity(pdf, ls_df):
    ls_df = ls_df.copy()
    ls_df["date"] = pd.to_datetime(ls_df["date"])
    for col in ["n_concepts", "n_objects", "avg_intent_size", "avg_extent_size"]:
        ls_df[col] = pd.to_numeric(ls_df[col], errors="coerce")
    ls_df.sort_values("date", inplace=True)
    dates = ls_df["date"].tolist()
    x     = range(len(dates))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    ax1.plot(x, ls_df["n_concepts"], color="#1982c4", linewidth=1.8,
             label="# Concepts", marker=".", markersize=4)
    ax1.plot(x, ls_df["n_objects"], color="#f4a261", linewidth=1.8,
             linestyle="--", label="# Sleeves", marker=".", markersize=4)
    ax1.set_ylabel("Count")
    ax1.set_title("Figure 9 - Temporal Complexity", loc="left")
    ax1.legend(fontsize=8, framealpha=0.9)

    ax2.plot(x, ls_df["avg_intent_size"], color="#6a4c93", linewidth=1.8,
             label="Avg Intent Size", marker=".", markersize=4)
    ax2.plot(x, ls_df["avg_extent_size"], color="#8ac926", linewidth=1.8,
             linestyle="--", label="Avg Extent Size", marker=".", markersize=4)
    ax2.set_ylabel("Avg Size")
    ax2.set_xlabel("Date")
    ax2.legend(fontsize=8, framealpha=0.9)
    date_ticks(ax2, dates)
    fig.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print("  Page 9  saved.")


# ---------------------------------------------------------------------------
# Page 10 – Steel Type Prevalence Heatmap (from prevalence section)
# ---------------------------------------------------------------------------

def page_steel_type_heatmap(pdf, prev_df):
    steel = prev_df[prev_df["attribute"] == "steel_type"].copy()
    if steel.empty:
        print("  Page 10 skipped (no steel_type prevalence data).")
        return

    pivot = steel.pivot_table(
        index="level", columns="date", values="prevalence_pct", aggfunc="mean", fill_value=0
    )
    if pivot.shape[1] > 30:
        pivot = pivot.iloc[:, :: pivot.shape[1] // 30]
    pivot.columns = [str(c)[5:] for c in pivot.columns]

    cmap = LinearSegmentedColormap.from_list("steel", ["#f8f9fa", "#264653", "#0a1628"])
    fig, ax = plt.subplots(figsize=(max(12, pivot.shape[1] * 0.38), 5))
    im = ax.imshow(pivot.values, aspect="auto", cmap=cmap, vmin=0, vmax=100)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=9)
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=70, ha="right", fontsize=7)
    ax.set_title("Figure 10 - Steel Type Prevalence Over Time (%)", pad=10)
    ax.set_xlabel("Date (MM-DD)")
    ax.set_ylabel("Steel Type")
    cb = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
    cb.set_label("% of daily concepts")
    fig.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print("  Page 10 saved.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  Script 4 - TCA Visualisation")
    print("  Continuous Casting Machine Dataset")
    print("=" * 60 + "\n")

    if not INPUT_CSV.exists():
        import sys
        sys.exit(f"ERROR: {INPUT_CSV} not found.\n       Run script3_tca_analysis.py first.")

    print(f"[1/3] Loading: {INPUT_CSV.name}\n")
    sections = load_sections(INPUT_CSV)

    lt_df   = sections.get("life_track",    pd.DataFrame())
    bd_df   = sections.get("births_deaths", pd.DataFrame())
    prev_df = sections.get("prevalence",    pd.DataFrame())
    ls_df   = sections.get("lattice_stats", pd.DataFrame())

    print(f"\n[2/3] Generating 10 figures into single PDF ...")
    print(f"       Output: {OUTPUT_PDF}\n")

    with PdfPages(OUTPUT_PDF) as pdf:
        # Set PDF metadata
        d = pdf.infodict()
        d["Title"]   = "Temporal Concept Analysis - Continuous Casting Machine"
        d["Subject"] = "TCA Visualisation"

        page_prevalence_heatmap(pdf, prev_df)
        page_rul_line(pdf, prev_df)
        page_key_attrs(pdf, prev_df)
        page_lifespan_hist(pdf, lt_df)
        page_classification_pie(pdf, lt_df)
        page_daily_count(pdf, ls_df)
        page_life_track_timeline(pdf, lt_df)
        page_births_deaths(pdf, bd_df)
        page_temporal_complexity(pdf, ls_df)
        page_steel_type_heatmap(pdf, prev_df)

    print(f"\n[3/3] Done.")
    print("=" * 60)
    print(f"  Input  : {INPUT_CSV.name}")
    print(f"  Output : {OUTPUT_PDF.name}")
    print(f"  Size   : {OUTPUT_PDF.stat().st_size / 1024:.1f} KB")
    print(f"  Pages  : 10")
    print("=" * 60)


if __name__ == "__main__":
    main()
