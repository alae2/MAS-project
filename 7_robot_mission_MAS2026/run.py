"""
Group: 7
Members: Ouissal BOUTOUATOU, Alae TAOUDI, Mohammed SBAIHI
Date: March 18, 2026
Description: Script to run the RobotMission simulation (batch + single mode)
             Supports exploration_mode (0/1/2) and communication_enabled (0/1).
"""
import matplotlib
matplotlib.use("Agg")

import json
import os

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import pandas as pd

from model import RobotMissionModel


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------

def run_simulation(config_dict):
    """
    Run the robot waste collection simulation.

    Args:
        config_dict: Dictionary containing simulation parameters.

    Returns:
        (model, model_data) tuple.
    """
    print("------ ROBOT WASTE COLLECTION MULTI-AGENT SYSTEM ------")
    print(f"\nSimulation Parameters:")
    print(f"  Grid: {config_dict.get('width', 40)}x{config_dict.get('height', 20)}")
    print(f"  Exploration Mode: {config_dict.get('exploration_mode', 0)}")
    print(f"  Communication: {'ON' if config_dict.get('communication_enabled', 1) else 'OFF'}")
    print(f"  Green Robots:  {config_dict.get('n_green_robots', 3)}")
    print(f"  Yellow Robots: {config_dict.get('n_yellow_robots', 2)}")
    print(f"  Red Robots:    {config_dict.get('n_red_robots', 1)}")
    print(f"  Initial Green Waste:  {config_dict.get('n_initial_green_waste', 10)}")
    print(f"  Initial Yellow Waste: {config_dict.get('n_initial_yellow_waste', 5)}")
    print(f"  Initial Red Waste:    {config_dict.get('n_initial_red_waste', 3)}")
    print(f"  Steps: {config_dict.get('n_steps', 150)}")
    print("\n" + "-" * 55 + "\n")

    model = RobotMissionModel(
        width=config_dict.get("width", 40),
        height=config_dict.get("height", 20),
        exploration_mode=config_dict.get("exploration_mode", 0),
        communication_enabled=config_dict.get("communication_enabled", 1),
        n_green_robots=config_dict.get("n_green_robots", 3),
        n_yellow_robots=config_dict.get("n_yellow_robots", 2),
        n_red_robots=config_dict.get("n_red_robots", 1),
        n_initial_green_waste=config_dict.get("n_initial_green_waste", 10),
        n_initial_yellow_waste=config_dict.get("n_initial_yellow_waste", 5),
        n_initial_red_waste=config_dict.get("n_initial_red_waste", 3),
        seed=config_dict.get("seed", 7),
        max_steps=config_dict.get("n_steps", 150),
    )

    n_steps = config_dict.get("n_steps", 150)
    for _ in range(n_steps):
        model.step()

    model_data = model.datacollector.get_model_vars_dataframe()

    print("\n" + "-" * 60)
    print("SIMULATION COMPLETED")
    print("-" * 60)
    print(f"\nFinal Statistics:")
    print(f"  Green Waste on Ground:    {model_data['Green_Waste_Ground'].iloc[-1]}")
    print(f"  Green Waste Being Carried:{model_data['Green_Waste_Carried'].iloc[-1]}")
    print(f"  Yellow Waste on Ground:   {model_data['Yellow_Waste_Ground'].iloc[-1]}")
    print(f"  Yellow Waste Being Carried:{model_data['Yellow_Waste_Carried'].iloc[-1]}")
    print(f"  Red Waste on Ground:      {model_data['Red_Waste_Ground'].iloc[-1]}")
    print(f"  Red Waste Being Carried:  {model_data['Red_Waste_Carried'].iloc[-1]}")
    print(f"  Total Waste Disposed:     {model_data['Waste_Disposed'].iloc[-1]}")

    return model, model_data


# ---------------------------------------------------------------------------
# Per-run plot
# ---------------------------------------------------------------------------

def plot_results(model_data, filename=None, run_id=""):
    """
    Plot simulation results for a single run.
    Includes ground waste, zone coverage, transformations, disposal progress,
    collection time, robots carrying cargo, and a text summary.
    """
    fig = plt.figure(figsize=(20, 14))
    gs = gridspec.GridSpec(3, 3, figure=fig)
    title = f"Robot Waste Mission Analysis{(' — ' + run_id) if run_id else ''}"
    fig.suptitle(title, fontsize=18, fontweight="bold")

    # [1] Ground Waste
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(model_data["Green_Waste_Ground"], color="green", label="Green")
    ax1.plot(model_data["Yellow_Waste_Ground"], color="gold", label="Yellow")
    ax1.plot(model_data["Red_Waste_Ground"], color="red", label="Red")
    ax1.set_title("Waste on Ground")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # [2] Zone Coverage
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(model_data["Visited_Ratio_Z1"], label="Z1 (Green)", color="#4caf50")
    ax2.plot(model_data["Visited_Ratio_Z2"], label="Z2 (Yellow)", color="#c6a700")
    ax2.plot(model_data["Visited_Ratio_Z3"], label="Z3 (Red)", color="#c24f4f")
    ax2.set_title("Exploration Coverage Ratio")
    ax2.set_ylim(0, 1.05)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # [3] Cumulative Transformations
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.plot(model_data["Green_to_Yellow_Transformations"], label="G→Y", color="darkgreen")
    ax3.plot(model_data["Yellow_to_Red_Transformations"], label="Y→R", color="orange")
    ax3.set_title("Cumulative Transformations")
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # [4] Disposal Progress
    ax4 = fig.add_subplot(gs[1, 0])
    ax4.fill_between(model_data.index, model_data["Waste_Disposed"], color="green", alpha=0.2)
    ax4.plot(model_data["Waste_Disposed"], color="green", linewidth=2)
    ax4.set_title("Total Waste Disposed")
    ax4.grid(True, alpha=0.3)

    # [5] Collection Time Efficiency
    ax5 = fig.add_subplot(gs[1, 1])
    ax5.plot(model_data["Avg_Green_Collection_Time"], label="Green Avg", color="darkgreen")
    ax5.plot(model_data["Avg_Yellow_Collection_Time"], label="Yellow Avg", color="orange")
    ax5.set_title("Avg Collection Time (1st→2nd pickup)")
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    # [6] Robots Carrying Cargo
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.plot(model_data["Green_Robots_With_Inventory"], color="darkgreen", label="Green")
    ax6.plot(model_data["Yellow_Robots_With_Inventory"], color="orange", label="Yellow")
    ax6.plot(model_data["Red_Robots_With_Inventory"], color="darkred", label="Red")
    ax6.set_title("Robots Carrying Waste")
    ax6.legend()
    ax6.grid(True, alpha=0.3)

    # [7] Summary text
    ax_sum = fig.add_subplot(gs[2, :])
    ax_sum.axis("off")
    total_disposed = model_data["Waste_Disposed"].iloc[-1]
    summary_text = f"""
    ================ SIMULATION SUMMARY ================

    Total Simulation Steps: {len(model_data) - 1}

    FINAL GROUND WASTE:        IN-TRANSIT (CARRIED):
    - Green:  {model_data['Green_Waste_Ground'].iloc[-1]:<10} | - Green:  {model_data['Green_Waste_Carried'].iloc[-1]}
    - Yellow: {model_data['Yellow_Waste_Ground'].iloc[-1]:<10} | - Yellow: {model_data['Yellow_Waste_Carried'].iloc[-1]}
    - Red:    {model_data['Red_Waste_Ground'].iloc[-1]:<10} | - Red:    {model_data['Red_Waste_Carried'].iloc[-1]}

    TOTAL WASTE SUCCESSFULLY DISPOSED: {total_disposed}
    ====================================================
    """
    ax_sum.text(
        0.5, 0.5, summary_text,
        fontsize=13, verticalalignment="center", horizontalalignment="center",
        fontfamily="monospace",
        bbox=dict(boxstyle="round,pad=1", facecolor="wheat", alpha=0.3),
    )

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    if filename:
        plt.savefig(filename, dpi=150, bbox_inches="tight")
        print(f"  Plot saved → '{filename}'")
    plt.close()


# ---------------------------------------------------------------------------
# Batch entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    BASE_PATH = "./7_robot_mission_MAS2026"
    CONFIG_DIR = os.path.join(BASE_PATH, "configs")
    RESULTS_DIR = os.path.join(BASE_PATH, "experiments/results")
    FIGURES_DIR = os.path.join(BASE_PATH, "experiments/figures")

    for folder in [CONFIG_DIR, RESULTS_DIR, FIGURES_DIR]:
        os.makedirs(folder, exist_ok=True)

    config_files = sorted(f for f in os.listdir(CONFIG_DIR) if f.endswith(".json"))

    if not config_files:
        print(f"[WARNING] No config JSON files found in '{CONFIG_DIR}'. Exiting.")
        raise SystemExit(0)

    # Seeds to test for every configuration
    seeds_to_test = [7, 16, 32]

    for config_file in config_files:
        config_id = os.path.splitext(config_file)[0]

        with open(os.path.join(CONFIG_DIR, config_file), "r") as f:
            base_params = json.load(f)

        for s in seeds_to_test:
            params = base_params.copy()
            params["seed"] = s

            run_id = f"{config_id}_seed{s}"
            print(f"\n>>> Running: {run_id}")

            model, data = run_simulation(params)

            # Save per-run plot
            plot_path = os.path.join(FIGURES_DIR, f"plot_{run_id}.png")
            plot_results(data, filename=plot_path, run_id=run_id)

            # Save CSV
            csv_path = os.path.join(RESULTS_DIR, f"data_{run_id}.csv")
            data.to_csv(csv_path)
            print(f"  CSV  saved → '{csv_path}'")

    print("\nBatch processing complete.")