"""
Group: 7
Members: Ouissal BOUTOUATOU, Alae TAOUDI, Mohammed SBAIHI
Date: March 18, 2026
Description: Script to run the RobotMission simulation
"""

from model import RobotMissionModel
import matplotlib.pyplot as plt
import pandas as pd


def run_simulation(
    n_steps=150,
    width=40,
    height=20,
    n_green_robots=7,
    n_yellow_robots=5,
    n_red_robots=3,
    n_initial_green_waste=10,
    n_initial_yellow_waste=5,
    n_initial_red_waste=3,
    seed=7
):
    """
    Run the robot waste collection simulation.
    
    Args:
        n_steps: Number of simulation steps
        width: Grid width
        height: Grid height
        n_green_robots: Number of green robots
        n_yellow_robots: Number of yellow robots
        n_red_robots: Number of red robots
        n_initial_green_waste: Number of initial green waste items
        n_initial_yellow_waste: Number of initial yellow waste items
        n_initial_red_waste: Number of initial red waste items
        seed: Random seed for reproducibility
    """
    
    print("------ ROBOT WASTE COLLECTION MULTI-AGENT SYSTEM ------")
    print(f"\nSimulation Parameters:")
    print(f"  Grid: {width}x{height}")
    print(f"  Green Robots: {n_green_robots}")
    print(f"  Yellow Robots: {n_yellow_robots}")
    print(f"  Red Robots: {n_red_robots}")
    print(f"  Initial Green Waste: {n_initial_green_waste}")
    print(f"  Initial Yellow Waste: {n_initial_yellow_waste}")
    print(f"  Initial Red Waste: {n_initial_red_waste}")
    print(f"  Steps: {n_steps}")
    print("\n" + "-" * 55 + "\n")
    
    model = RobotMissionModel(
        width=width,
        height=height,
        n_green_robots=n_green_robots,
        n_yellow_robots=n_yellow_robots,
        n_red_robots=n_red_robots,
        n_initial_green_waste=n_initial_green_waste,
        n_initial_yellow_waste=n_initial_yellow_waste,
        n_initial_red_waste=n_initial_red_waste,
        max_steps=None,
        seed=seed
    )
    
    for _ in range(n_steps):
        model.step()
    
    model_data = model.datacollector.get_model_vars_dataframe()
    
    print("\n" + "-" * 60)
    print("SIMULATION COMPLETED")
    print("-" * 60)
    print(f"\nFinal Statistics:")
    print(f"  Green Waste on Ground: {model_data['Green_Waste_Ground'].iloc[-1]}")
    print(f"  Green Waste Being Carried: {model_data['Green_Waste_Carried'].iloc[-1]}")
    print(f"  Yellow Waste on Ground: {model_data['Yellow_Waste_Ground'].iloc[-1]}")
    print(f"  Yellow Waste Being Carried: {model_data['Yellow_Waste_Carried'].iloc[-1]}")
    print(f"  Red Waste on Ground: {model_data['Red_Waste_Ground'].iloc[-1]}")
    print(f"  Red Waste Being Carried: {model_data['Red_Waste_Carried'].iloc[-1]}")
    print(f"  Total Waste Disposed: {model_data['Waste_Disposed'].iloc[-1]}")
    
    return model, model_data


def plot_results(model_data):
    """Plot simulation results with ground and carried waste tracking"""

    import matplotlib.gridspec as gridspec
    
    fig = plt.figure(figsize=(16, 10))
    gs = gridspec.GridSpec(2, 3, figure=fig)
    fig.suptitle('Robot Waste Collection Mission - Results', fontsize=16, fontweight='bold')
    
    # Plot 1: Ground Waste over Time
    ax = fig.add_subplot(gs[0, 0])
    ax.plot(model_data.index, model_data['Green_Waste_Ground'], label='Green (Ground)', marker='o', markersize=3, color='green')
    ax.plot(model_data.index, model_data['Yellow_Waste_Ground'], label='Yellow (Ground)', marker='s', markersize=3, color='gold')
    ax.plot(model_data.index, model_data['Red_Waste_Ground'], label='Red (Ground)', marker='^', markersize=3, color='red')
    ax.set_xlabel('Step')
    ax.set_ylabel('Count')
    ax.set_title('Waste on Ground Over Time')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 2: Carried Waste over Time
    ax = fig.add_subplot(gs[0, 1])
    ax.plot(model_data.index, model_data['Green_Waste_Carried'], label='Green (Carried)', marker='o', markersize=3, color='darkgreen')
    ax.plot(model_data.index, model_data['Yellow_Waste_Carried'], label='Yellow (Carried)', marker='s', markersize=3, color='orange')
    ax.plot(model_data.index, model_data['Red_Waste_Carried'], label='Red (Carried)', marker='^', markersize=3, color='darkred')
    ax.set_xlabel('Step')
    ax.set_ylabel('Count')
    ax.set_title('Waste Being Carried Over Time')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 3: Waste Disposal Progress
    ax = fig.add_subplot(gs[1, 0])
    ax.plot(model_data.index, model_data['Waste_Disposed'], color='darkgreen', linewidth=2.5, marker='o', markersize=3)
    ax.fill_between(model_data.index, model_data['Waste_Disposed'], alpha=0.3, color='green')
    ax.set_xlabel('Step')
    ax.set_ylabel('Cumulative Waste Disposed')
    ax.set_title('Waste Disposal Progress')
    ax.grid(True, alpha=0.3)
    
    # Plot 4: Robots with Inventory
    ax = fig.add_subplot(gs[1, 1])
    ax.plot(model_data.index, model_data['Green_Robots_With_Inventory'], label='Green Robots', marker='o', markersize=3, color='darkgreen')
    ax.plot(model_data.index, model_data['Yellow_Robots_With_Inventory'], label='Yellow Robots', marker='s', markersize=3, color="orange")
    ax.plot(model_data.index, model_data['Red_Robots_With_Inventory'], label='Red Robots', marker='^', markersize=3, color='darkred')
    ax.set_xlabel('Step')
    ax.set_ylabel('Number of Robots')
    ax.set_title('Robots Carrying Waste')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 5: Summary Statistics 
    ax = fig.add_subplot(gs[:, 2])
    ax.axis('off')
    
    total_disposed = model_data['Waste_Disposed'].iloc[-1]
    summary_text = f"""

    SIMULATION SUMMARY
    
    Total Steps: {len(model_data) - 1}
    
    Final Ground Waste:
    Green: {model_data['Green_Waste_Ground'].iloc[-1]}
    Yellow: {model_data['Yellow_Waste_Ground'].iloc[-1]}
    Red: {model_data['Red_Waste_Ground'].iloc[-1]}
    
    In-Transit (Carried):
    Green: {model_data['Green_Waste_Carried'].iloc[-1]}
    Yellow: {model_data['Yellow_Waste_Carried'].iloc[-1]}
    Red: {model_data['Red_Waste_Carried'].iloc[-1]}
    
    Total Waste Disposed: {total_disposed}

    """
    
    ax.text(0.1, 0.5, summary_text, fontsize=11, verticalalignment='center',
            fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig('figs/robot_mission_results.png', dpi=150, bbox_inches='tight')
    print("\n Results saved to 'figs/robot_mission_results.png'")


if __name__ == "__main__":
    # Run simulation with default parameters
    model, data = run_simulation(
        n_steps=250,
        width=40,
        height=20,
        n_green_robots=3,
        n_yellow_robots=2,
        n_red_robots=1,
        n_initial_green_waste=10,
        n_initial_yellow_waste=5,
        n_initial_red_waste=3,
        seed=7
    )
    
    plot_results(data)
    
    data.to_csv('results/robot_mission_data.csv')
    print(" Data saved to 'results/robot_mission_data.csv'")
