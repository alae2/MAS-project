"""
Group: 7
Members: Ouissal BOUTOUATOU, Alae TAOUDI, Mohammed SBAIHI
Date: March 18, 2026
Description: Batch analysis + visualisation for Robot Mission MAS experiments.
             Supports exploration_mode (M0/M1/M2) AND communication_enabled (C0/C1).
             Generates 7 publication-quality figures.
"""
import matplotlib
matplotlib.use("Agg")

import os
import warnings

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)


# ---------------------------------------------------------------------------
# Palette & helpers
# ---------------------------------------------------------------------------

MAS_PALETTE = {
    "0: Sweep":  "#88c8f3",
    "1: Random": "#3ca954",
    "2: BFS":    "#000d70",
}

MODE_MAP   = {"M0": "0: Sweep",  "M1": "1: Random", "M2": "2: BFS"}
ROBOT_MAP  = {"RL": "Low",       "RM": "Medium",     "RH": "High"}
WASTE_MAP  = {"WS": "Sparse",    "WB": "Balanced",   "WH": "Heavy"}
COMM_MAP   = {"C0": "OFF",       "C1": "ON"}

# Order categories for consistent axis ordering
ROBOT_ORDER = ["Low", "Medium", "High"]
WASTE_ORDER = ["Sparse", "Balanced", "Heavy"]
COMM_ORDER  = ["OFF", "ON"]


def _load_master_df(results_dir):
    """
    Load all CSV result files from results_dir and return a tidy master DataFrame.

    Expected filename format (produced by run.py):
        data_<ConfigID>_seed<N>.csv
    where ConfigID follows: M<x>_R<y>_W<z>_C<c>
    e.g.  data_M0_RL_WS_C1_seed7.csv
    """
    files = [f for f in os.listdir(results_dir) if f.endswith(".csv")]
    if not files:
        raise FileNotFoundError(f"No CSV files found in '{results_dir}'")

    records = []
    for file in files:
        # Strip leading "data_" prefix if present
        name = file.replace("data_", "").replace(".csv", "")
        parts = name.split("_")

        df = pd.read_csv(os.path.join(results_dir, file))
        last = df.iloc[-1].copy()

        # Parse config tokens – tolerate missing comm token (backward compat)
        mode_token  = next((p for p in parts if p.startswith("M")), "M0")
        robot_token = next((p for p in parts if p.startswith("R") and len(p) == 2), "RM")
        waste_token = next((p for p in parts if p.startswith("W")), "WB")
        comm_token  = next((p for p in parts if p.startswith("C") and len(p) == 2), "C1")
        seed_token  = next((p for p in parts if p.startswith("seed")), "seed0")

        last["Mode"]         = MODE_MAP.get(mode_token,  mode_token)
        last["Robot_Density"]= ROBOT_MAP.get(robot_token, robot_token)
        last["Waste_Density"]= WASTE_MAP.get(waste_token, waste_token)
        last["Comm"]         = COMM_MAP.get(comm_token,  comm_token)
        last["Seed"]         = seed_token.replace("seed", "")

        last["Global_Coverage"] = (
            last["Visited_Ratio_Z1"]
            + last["Visited_Ratio_Z2"]
            + last["Visited_Ratio_Z3"]
        ) / 3

        records.append(last)

    master = pd.DataFrame(records)

    # Apply category ordering where possible
    for col, order in [
        ("Robot_Density", ROBOT_ORDER),
        ("Waste_Density", WASTE_ORDER),
        ("Comm", COMM_ORDER),
    ]:
        present = [v for v in order if v in master[col].unique()]
        if present:
            master[col] = pd.Categorical(master[col], categories=present, ordered=True)

    return master


# ---------------------------------------------------------------------------
# Individual plot functions
# ---------------------------------------------------------------------------

def _plot_disposal_bars(master_df, output_path):
    """PLOT 1 – Waste Disposed grouped by Mode, faceted by Robot × Waste density."""
    sns.set_theme(style="whitegrid", context="talk")

    g = sns.catplot(
        data=master_df, kind="bar",
        x="Mode", y="Waste_Disposed", hue="Mode",
        col="Waste_Density", row="Robot_Density",
        col_order=WASTE_ORDER, row_order=ROBOT_ORDER,
        palette=MAS_PALETTE, height=4, aspect=1.2,
        dodge=False, alpha=0.9, edgecolor=".2",
    )
    g.set_titles(row_template="Robots: {row_name}", col_template="Waste: {col_name}")
    g.fig.suptitle("Performance Analysis: Waste Disposed", y=1.03, fontsize=20, fontweight="bold")
    path = os.path.join(output_path, "fig1_disposal_bars.png")
    g.savefig(path, bbox_inches="tight", dpi=150)
    plt.close("all")
    print(f"  Saved → {path}")


def _plot_efficiency_scatter(master_df, output_path):
    """PLOT 2 – Coverage vs. pickup speed coloured by Mode."""
    sns.set_theme(style="whitegrid", context="talk")

    plt.figure(figsize=(12, 7))
    sns.scatterplot(
        data=master_df,
        x="Global_Coverage", y="Avg_Green_Collection_Time",
        hue="Mode", style="Waste_Density", size="Robot_Density",
        sizes=(100, 500), palette=MAS_PALETTE, alpha=0.75, edgecolor="w",
    )
    plt.title("Search Efficiency: Coverage vs. Pickup Speed", fontsize=16, fontweight="bold")
    plt.xlabel("Global Coverage (avg over 3 zones)")
    plt.ylabel("Avg Green Collection Time (steps)")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left", borderaxespad=0.0)
    plt.tight_layout()
    path = os.path.join(output_path, "fig2_efficiency_scatter.png")
    plt.savefig(path, dpi=150)
    plt.close("all")
    print(f"  Saved → {path}")


def _plot_seed_reliability(master_df, output_path):
    """PLOT 3 – Boxplot + strip across seeds per Mode."""
    sns.set_theme(style="whitegrid", context="talk")

    plt.figure(figsize=(12, 6))
    sns.boxplot(
        data=master_df, x="Mode", y="Waste_Disposed",
        palette=MAS_PALETTE, width=0.4, fliersize=0,
    )
    sns.stripplot(
        data=master_df, x="Mode", y="Waste_Disposed",
        color=".2", size=6, alpha=0.5, jitter=True,
    )
    plt.title("Algorithm Reliability across Randomised Seeds", fontsize=16, fontweight="bold")
    plt.ylabel("Waste Disposed (final step)")
    plt.tight_layout()
    path = os.path.join(output_path, "fig3_seed_reliability.png")
    plt.savefig(path, dpi=150)
    plt.close("all")
    print(f"  Saved → {path}")


def _plot_coverage_stability(master_df, output_path):
    """PLOT 4 – Per-seed coverage stability per Mode."""
    sns.set_theme(style="whitegrid", context="talk")

    plt.figure(figsize=(10, 6))
    sns.pointplot(
        data=master_df, x="Seed", y="Global_Coverage", hue="Mode",
        palette=MAS_PALETTE, markers=["o", "s", "D"], linestyles=["-", "--", "-."],
    )
    plt.title("Exploration Stability per Seed", fontsize=16, fontweight="bold")
    plt.ylabel("Global Coverage (0→1)")
    plt.ylim(0, 1)
    plt.tight_layout()
    path = os.path.join(output_path, "fig4_coverage_stability.png")
    plt.savefig(path, dpi=150)
    plt.close("all")
    print(f"  Saved → {path}")


def _plot_communication_impact(master_df, output_path):
    """
    PLOT 5 – Communication ON vs OFF: side-by-side bars per Mode.
    Answers: 'Does enabling communication improve disposal?'
    """
    if "Comm" not in master_df.columns or master_df["Comm"].nunique() < 2:
        print("  [SKIP] fig5 – not enough Comm variety in results.")
        return

    sns.set_theme(style="whitegrid", context="talk")

    plt.figure(figsize=(10, 6))
    ax = sns.barplot(
        data=master_df, x="Mode", y="Waste_Disposed",
        hue="Comm", hue_order=COMM_ORDER,
        palette={"OFF": "#e0e0e0", "ON": "#1a73e8"},
        edgecolor=".2", alpha=0.88,
    )
    ax.set_title("Impact of Communication on Waste Disposal (all configs)", fontsize=16, fontweight="bold")
    ax.set_ylabel("Mean Waste Disposed ± 95 % CI")
    ax.legend(title="Communication")
    plt.tight_layout()
    path = os.path.join(output_path, "fig5_communication_impact.png")
    plt.savefig(path, dpi=150)
    plt.close("all")
    print(f"  Saved → {path}")


def _plot_heatmap_disposal(master_df, output_path):
    """
    PLOT 6 – Heatmap: mean Waste_Disposed for Robot_Density × Waste_Density,
    one facet per Mode.
    """
    sns.set_theme(style="white", context="talk")

    modes = master_df["Mode"].unique()
    n_modes = len(modes)
    fig, axes = plt.subplots(1, n_modes, figsize=(6 * n_modes, 5), sharey=True)
    if n_modes == 1:
        axes = [axes]

    for ax, mode in zip(axes, sorted(modes)):
        sub = master_df[master_df["Mode"] == mode]
        pivot = (
            sub.groupby(["Robot_Density", "Waste_Density"])["Waste_Disposed"]
            .mean()
            .unstack("Waste_Density")
        )
        # Reorder axes if possible
        pivot = pivot.reindex(
            index=[r for r in ROBOT_ORDER if r in pivot.index],
            columns=[w for w in WASTE_ORDER if w in pivot.columns],
        )
        sns.heatmap(
            pivot, ax=ax, annot=True, fmt=".1f",
            cmap="YlGn", linewidths=0.5, cbar=ax is axes[-1],
        )
        ax.set_title(f"Mode: {mode}", fontsize=14, fontweight="bold")
        ax.set_xlabel("Waste Density")
        ax.set_ylabel("Robot Density")

    fig.suptitle("Mean Waste Disposed Heatmap (Robot × Waste)", fontsize=18, fontweight="bold", y=1.02)
    plt.tight_layout()
    path = os.path.join(output_path, "fig6_heatmap_disposal.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close("all")
    print(f"  Saved → {path}")


def _plot_collection_time_comparison(master_df, output_path):
    """
    PLOT 7 – Violin plots of Avg_Green_Collection_Time per Mode,
    split by Robot_Density. Shows distribution shape, not just mean.
    """
    sns.set_theme(style="whitegrid", context="talk")

    robot_densities = [r for r in ROBOT_ORDER if r in master_df["Robot_Density"].unique()]
    n = len(robot_densities)
    fig, axes = plt.subplots(1, n, figsize=(6 * n, 6), sharey=True)
    if n == 1:
        axes = [axes]

    for ax, density in zip(axes, robot_densities):
        sub = master_df[master_df["Robot_Density"] == density]
        sns.violinplot(
            data=sub, x="Mode", y="Avg_Green_Collection_Time",
            palette=MAS_PALETTE, inner="box", cut=0, ax=ax,
        )
        ax.set_title(f"Robots: {density}", fontsize=13, fontweight="bold")
        ax.set_xlabel("")
        ax.set_ylabel("Avg Green Collection Time (steps)" if ax is axes[0] else "")
        ax.grid(True, axis="y", linestyle="--", alpha=0.5)

    fig.suptitle("Green Collection Time Distribution by Robot Density", fontsize=17, fontweight="bold")
    plt.tight_layout()
    path = os.path.join(output_path, "fig7_collection_time_violin.png")
    plt.savefig(path, dpi=150)
    plt.close("all")
    print(f"  Saved → {path}")


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def run_global_comparison(
    results_dir="./7_robot_mission_MAS2026/experiments/results",
    output_path="./7_robot_mission_MAS2026/experiments",
):
    """Load all CSVs and produce all comparison figures."""
    print(f"\n=== Global Comparison ===")
    print(f"  Results dir : {results_dir}")
    print(f"  Output dir  : {output_path}\n")

    master_df = _load_master_df(results_dir)
    print(f"  Loaded {len(master_df)} runs — columns: {list(master_df.columns)}\n")

    os.makedirs(output_path, exist_ok=True)

    _plot_disposal_bars(master_df, output_path)
    _plot_efficiency_scatter(master_df, output_path)
    _plot_seed_reliability(master_df, output_path)
    _plot_coverage_stability(master_df, output_path)
    _plot_communication_impact(master_df, output_path)
    _plot_heatmap_disposal(master_df, output_path)
    _plot_collection_time_comparison(master_df, output_path)

    print(f"\nAll figures saved to '{output_path}'")


if __name__ == "__main__":
    run_global_comparison()