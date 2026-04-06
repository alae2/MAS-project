import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import warnings

# Silence the warnings we discussed
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

def run_global_comparison(results_dir="./7_robot_mission_MAS2026/experiments/results"):
    # 1. GLOBAL STYLE CONFIGURATION
    sns.set_theme(style="whitegrid", context="talk") # 'talk' makes labels larger/readable
    
    # Professional fixed palette for your 3 modes
    # Blue for Sweep, Orange for Random, Green for BFS
    mas_palette = {"0: Sweep": "#88c8f3", "1: Random": "#3b2793", "2: BFS": "#000d70"}
    
    data_list = []
    mode_map = {"M0": "0: Sweep", "M1": "1: Random", "M2": "2: BFS"}
    robot_map = {"RL": "Low", "RM": "Medium", "RH": "High"}
    waste_map = {"WS": "Sparse", "WB": "Balanced", "WH": "Heavy"}

    # --- DATA LOADING ---
    files = [f for f in os.listdir(results_dir) if f.endswith('.csv')]
    for file in files:
        parts = file.replace('.csv', '').split('_')
        df = pd.read_csv(os.path.join(results_dir, file))
        last_step = df.iloc[-1].copy()
        
        last_step['Mode'] = mode_map.get(parts[2], parts[2])
        last_step['Robot_Density'] = robot_map.get(parts[3], parts[3])
        last_step['Waste_Density'] = waste_map.get(parts[4], parts[4])
        last_step['Seed'] = parts[5].replace('seed', '')
        
        last_step['Global_Coverage'] = (last_step['Visited_Ratio_Z1'] + 
                                        last_step['Visited_Ratio_Z2'] + 
                                        last_step['Visited_Ratio_Z3']) / 3
        data_list.append(last_step)

    master_df = pd.DataFrame(data_list)
    output_path = "./7_robot_mission_MAS2026/experiments"

    # --- PLOT 1: DISPOSAL PERFORMANCE (Standardized Bars) ---
    g = sns.catplot(
        data=master_df, kind="bar",
        x="Mode", y="Waste_Disposed", hue="Mode",
        col="Waste_Density", row="Robot_Density",
        palette=mas_palette, height=4, aspect=1.2,
        dodge=False, alpha=0.9, edgecolor=".2"
    )
    g.fig.suptitle("Performance Analysis: Waste Disposed", y=1.05, fontsize=20, fontweight='bold')
    plt.savefig(f"{output_path}/final_disposal_comparison.png", bbox_inches='tight')

    # --- PLOT 2: SEARCH INTELLIGENCE (Standardized Scatter) ---
    plt.figure(figsize=(12, 7))
    sns.scatterplot(
        data=master_df, 
        x="Global_Coverage", y="Avg_Green_Collection_Time", 
        hue="Mode", style="Waste_Density", size="Robot_Density",
        sizes=(100, 500), palette=mas_palette, alpha=0.7, edgecolor="w"
    )
    plt.title("Search Efficiency: Coverage vs. Pickup Speed", fontsize=16, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
    plt.tight_layout()
    plt.savefig(f"{output_path}/final_efficiency_scatter.png")

    # --- PLOT 3: SEED RELIABILITY (Standardized Boxplots) ---
    plt.figure(figsize=(12, 6))
    # Boxplot for the distribution
    sns.boxplot(data=master_df, x="Mode", y="Waste_Disposed", palette=mas_palette, width=0.4, fliersize=0)
    # Stripplot for the individual seeds (black dots for contrast)
    sns.stripplot(data=master_df, x="Mode", y="Waste_Disposed", color=".2", size=6, alpha=0.5, jitter=True)
    plt.title("Algorithm Reliability across Randomized Seeds", fontsize=16, fontweight='bold')
    plt.savefig(f"{output_path}/seed_impact_disposal.png")

    # --- PLOT 4: COVERAGE STABILITY (Standardized Pointplot) ---
    plt.figure(figsize=(10, 6))
    sns.pointplot(data=master_df, x="Seed", y="Global_Coverage", hue="Mode", 
                  palette=mas_palette, markers=["o", "s", "D"], linestyles=["-", "--", "-."])
    plt.title("Exploration Stability per Seed", fontsize=16, fontweight='bold')
    plt.ylim(0, 1)
    plt.savefig(f"{output_path}/coverage_stability.png")

    print(f"Success!  Plots saved to {output_path}")

if __name__ == "__main__":
    run_global_comparison()