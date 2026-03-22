"""
Group: 7
Members:
Date:
Description: Script to run the RobotMission simulation.
"""

import os
from model import RobotMissionModel
import matplotlib.pyplot as plt


def run_simulation(
    n_steps: int = 150,
    width: int = 40,
    height: int = 20,
    n_green_robots: int = 7,
    n_yellow_robots: int = 5,
    n_red_robots: int = 3,
    n_initial_green_waste: int = 10,
    seed: int = 7,
):
    """Run the robot waste collection simulation."""

    print("------ ROBOT WASTE COLLECTION MULTI-AGENT SYSTEM ------")
    print(f"\nSimulation Parameters:")
    print(f"  Grid: {width}x{height}")
    print(f"  Green Robots: {n_green_robots}")
    print(f"  Yellow Robots: {n_yellow_robots}")
    print(f"  Red Robots: {n_red_robots}")
    print(f"  Initial Green Waste: {n_initial_green_waste}")
    print(f"  Steps: {n_steps}")
    print("\n" + "-" * 55 + "\n")

    model = RobotMissionModel(
        width=width,
        height=height,
        n_green_robots=n_green_robots,
        n_yellow_robots=n_yellow_robots,
        n_red_robots=n_red_robots,
        n_initial_green_waste=n_initial_green_waste,
        max_steps=None,
        seed=seed,
    )

    for _ in range(n_steps):
        model.step()

    model_data = model.datacollector.get_model_vars_dataframe()

    print("\n" + "-" * 60)
    print("SIMULATION COMPLETED")
    print("-" * 60)
    print(f"\nFinal Statistics:")
    for col in model_data.columns:
        print(f"  {col}: {model_data[col].iloc[-1]}")

    return model, model_data


def plot_results(model_data):
    """Plot simulation results."""
    import matplotlib.gridspec as gridspec

    os.makedirs("figs", exist_ok=True)
    os.makedirs("results", exist_ok=True)

    fig = plt.figure(figsize=(16, 10))
    gs = gridspec.GridSpec(2, 3, figure=fig)
    fig.suptitle("Robot Waste Collection Mission — Results", fontsize=16, fontweight="bold")

    # Ground waste over time
    ax = fig.add_subplot(gs[0, 0])
    ax.plot(model_data.index, model_data["Green_Waste_Ground"],  color="green",   label="Green (Ground)",  marker="o", markersize=3)
    ax.plot(model_data.index, model_data["Yellow_Waste_Ground"], color="gold",    label="Yellow (Ground)", marker="s", markersize=3)
    ax.plot(model_data.index, model_data["Red_Waste_Ground"],    color="red",     label="Red (Ground)",    marker="^", markersize=3)
    ax.set_title("Waste on Ground Over Time")
    ax.set_xlabel("Step"); ax.set_ylabel("Count")
    ax.legend(); ax.grid(True, alpha=0.3)

    # Carried waste over time
    ax = fig.add_subplot(gs[0, 1])
    ax.plot(model_data.index, model_data["Green_Waste_Carried"],  color="darkgreen", label="Green (Carried)",  marker="o", markersize=3)
    ax.plot(model_data.index, model_data["Yellow_Waste_Carried"], color="orange",    label="Yellow (Carried)", marker="s", markersize=3)
    ax.plot(model_data.index, model_data["Red_Waste_Carried"],    color="darkred",   label="Red (Carried)",    marker="^", markersize=3)
    ax.set_title("Waste Being Carried Over Time")
    ax.set_xlabel("Step"); ax.set_ylabel("Count")
    ax.legend(); ax.grid(True, alpha=0.3)

    # Disposal progress
    ax = fig.add_subplot(gs[1, 0])
    ax.plot(model_data.index, model_data["Waste_Disposed"], color="darkgreen", linewidth=2.5, marker="o", markersize=3)
    ax.fill_between(model_data.index, model_data["Waste_Disposed"], alpha=0.3, color="green")
    ax.set_title("Waste Disposal Progress")
    ax.set_xlabel("Step"); ax.set_ylabel("Cumulative Waste Disposed")
    ax.grid(True, alpha=0.3)

    # Robots with inventory
    ax = fig.add_subplot(gs[1, 1])
    ax.plot(model_data.index, model_data["Green_Robots_With_Inventory"],  color="darkgreen", label="Green Robots",  marker="o", markersize=3)
    ax.plot(model_data.index, model_data["Yellow_Robots_With_Inventory"], color="orange",    label="Yellow Robots", marker="s", markersize=3)
    ax.plot(model_data.index, model_data["Red_Robots_With_Inventory"],    color="darkred",   label="Red Robots",    marker="^", markersize=3)
    ax.set_title("Robots Carrying Waste")
    ax.set_xlabel("Step"); ax.set_ylabel("Number of Robots")
    ax.legend(); ax.grid(True, alpha=0.3)

    # Summary text
    ax = fig.add_subplot(gs[:, 2])
    ax.axis("off")
    total_disposed = model_data["Waste_Disposed"].iloc[-1]
    summary = f"""
    SIMULATION SUMMARY

    Total Steps: {len(model_data) - 1}

    Final Ground Waste:
      Green:  {model_data['Green_Waste_Ground'].iloc[-1]}
      Yellow: {model_data['Yellow_Waste_Ground'].iloc[-1]}
      Red:    {model_data['Red_Waste_Ground'].iloc[-1]}

    In-Transit (Carried):
      Green:  {model_data['Green_Waste_Carried'].iloc[-1]}
      Yellow: {model_data['Yellow_Waste_Carried'].iloc[-1]}
      Red:    {model_data['Red_Waste_Carried'].iloc[-1]}

    Total Waste Disposed: {total_disposed}
    """
    ax.text(0.1, 0.5, summary, fontsize=11, verticalalignment="center",
            fontfamily="monospace", bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

    plt.tight_layout()
    out_path = "figs/robot_mission_results.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\nResults saved to '{out_path}'")


if __name__ == "__main__":
    model, data = run_simulation(
        n_steps=250,
        width=40,
        height=20,
        n_green_robots=3,
        n_yellow_robots=2,
        n_red_robots=1,
        n_initial_green_waste=10,
        seed=7,
    )

    plot_results(data)

    data.to_csv("results/robot_mission_data.csv")
    print("Data saved to 'results/robot_mission_data.csv'")