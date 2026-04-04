"""
Group: 7
Members: Ouissal BOUTOUATOU, Alae TAOUDI, Mohammed SBAIHI
Date: March 18, 2026
Description: Script to run the RobotMission simulation
"""

from os import mkdir
import json
import os 
from model import RobotMissionModel
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.gridspec as gridspec

def run_simulation(config_dict):
    """
    Run the robot waste collection simulation.
    
    Args:
        config_dict: Dictionary containing simulation parameters

    """
    
    print("------ ROBOT WASTE COLLECTION MULTI-AGENT SYSTEM ------")
    print(f"\nSimulation Parameters:")
    print(f"  Grid: {config_dict.get('width', 40)}x{config_dict.get('height', 20)}")
    print(f"  Green Robots: {config_dict.get('n_green_robots', 3)}")
    print(f"  Yellow Robots: {config_dict.get('n_yellow_robots', 2)}")
    print(f"  Red Robots: {config_dict.get('n_red_robots', 1)}")
    print(f"  Initial Green Waste: {config_dict.get('n_initial_green_waste', 10)}")
    print(f"  Initial Yellow Waste: {config_dict.get('n_initial_yellow_waste', 5)}")
    print(f"  Initial Red Waste: {config_dict.get('n_initial_red_waste', 3)}")
    print(f"  Steps: {config_dict.get('n_steps', 150)}")
    print("\n" + "-" * 55 + "\n")
    
    model = RobotMissionModel(
        width=config_dict.get("width", 40),
        height=config_dict.get("height", 20),
        exploration_mode=config_dict.get("exploration_mode", 0),
        n_green_robots=config_dict.get("n_green_robots", 3),
        n_yellow_robots=config_dict.get("n_yellow_robots", 2),
        n_red_robots=config_dict.get("n_red_robots", 1),
        n_initial_green_waste=config_dict.get("n_initial_green_waste", 10),
        n_initial_yellow_waste=config_dict.get("n_initial_yellow_waste", 5),
        n_initial_red_waste=config_dict.get("n_initial_red_waste", 3),
        seed=config_dict.get("seed", 7),
        max_steps=config_dict.get("n_steps", 150)
    )
    
    n_steps = config_dict.get("n_steps", 150)
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
    plt.savefig('./7_robot_mission_MAS2026/figures/robot_mission_results.png', dpi=150, bbox_inches='tight')
    print("\n Results saved to './7_robot_mission_MAS2026/figures/robot_mission_results.png'")


# if __name__ == "__main__":
#     # Run simulation with default parameters
#     model, data = run_simulation(
#         n_steps=250,
#         width=40,
#         height=20,
#         exploration_mode=0,  # 0: No exploration, 1: Random exploration, 2: Directed exploration
#         n_green_robots=3,
#         n_yellow_robots=2,
#         n_red_robots=1,
#         n_initial_green_waste=10,
#         n_initial_yellow_waste=5,
#         n_initial_red_waste=3,
#         seed=7
#     )
    
#     plot_results(data)
    
#     data.to_csv('./7_robot_mission_MAS2026/results/robot_mission_data_explore.csv')
#     print(" Data saved to './7_robot_mission_MAS2026/results/robot_mission_data_explore.csv'")

if __name__ == "__main__":
    # Define significant paths
    BASE_PATH = "./7_robot_mission_MAS2026"
    CONFIG_DIR = os.path.join(BASE_PATH, "configs")
    RESULTS_DIR = os.path.join(BASE_PATH, "results")
    FIGURES_DIR = os.path.join(BASE_PATH, "figures")

    # Ensure directories exist
    for folder in [CONFIG_DIR, RESULTS_DIR, FIGURES_DIR]:
        os.makedirs(folder, exist_ok=True)

    # List all config files
    config_files = [f for f in os.listdir(CONFIG_DIR) if f.endswith('.json')]
    
    if not config_files:
        print(f"No configuration files found in {CONFIG_DIR}")
    else:
        print(f"Found {len(config_files)} configurations. Processing...")

    for config_file in config_files:
        # Generate a significant ID from the filename (e.g., 'explore_mode_2')
        config_id = os.path.splitext(config_file)[0]
        
        # Load parameters
        with open(os.path.join(CONFIG_DIR, config_file), 'r') as f:
            params = json.load(f)
        
        print(f"\n>>> Starting Simulation: {config_id}")
        
        # Run
        model, data = run_simulation(params)
        
        # Save Plot 
        plot_results(data, filename=f"{FIGURES_DIR}/plot_{config_id}.png")
        
        # Save CSV with significant ID
        csv_path = os.path.join(RESULTS_DIR, f"robot_mission_data_{config_id}.csv")
        data.to_csv(csv_path)
        
        print(f"--- Finished: {config_id} ---")
        print(f"--- Data saved to: {csv_path}")

    print("\nAll batch configurations have been processed.")