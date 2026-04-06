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


# def plot_results(model_data):
#     """Plot simulation results with ground and carried waste tracking"""

    
#     fig = plt.figure(figsize=(16, 10))
#     gs = gridspec.GridSpec(2, 3, figure=fig)
#     fig.suptitle('Robot Waste Collection Mission - Results', fontsize=16, fontweight='bold')
    
#     # Plot 1: Ground Waste over Time
#     ax = fig.add_subplot(gs[0, 0])
#     ax.plot(model_data.index, model_data['Green_Waste_Ground'], label='Green (Ground)', marker='o', markersize=3, color='green')
#     ax.plot(model_data.index, model_data['Yellow_Waste_Ground'], label='Yellow (Ground)', marker='s', markersize=3, color='gold')
#     ax.plot(model_data.index, model_data['Red_Waste_Ground'], label='Red (Ground)', marker='^', markersize=3, color='red')
#     ax.set_xlabel('Step')
#     ax.set_ylabel('Count')
#     ax.set_title('Waste on Ground Over Time')
#     ax.legend()
#     ax.grid(True, alpha=0.3)
    
#     # Plot 2: Carried Waste over Time
#     ax = fig.add_subplot(gs[0, 1])
#     ax.plot(model_data.index, model_data['Green_Waste_Carried'], label='Green (Carried)', marker='o', markersize=3, color='darkgreen')
#     ax.plot(model_data.index, model_data['Yellow_Waste_Carried'], label='Yellow (Carried)', marker='s', markersize=3, color='orange')
#     ax.plot(model_data.index, model_data['Red_Waste_Carried'], label='Red (Carried)', marker='^', markersize=3, color='darkred')
#     ax.set_xlabel('Step')
#     ax.set_ylabel('Count')
#     ax.set_title('Waste Being Carried Over Time')
#     ax.legend()
#     ax.grid(True, alpha=0.3)
    
#     # Plot 3: Waste Disposal Progress
#     ax = fig.add_subplot(gs[1, 0])
#     ax.plot(model_data.index, model_data['Waste_Disposed'], color='darkgreen', linewidth=2.5, marker='o', markersize=3)
#     ax.fill_between(model_data.index, model_data['Waste_Disposed'], alpha=0.3, color='green')
#     ax.set_xlabel('Step')
#     ax.set_ylabel('Cumulative Waste Disposed')
#     ax.set_title('Waste Disposal Progress')
#     ax.grid(True, alpha=0.3)
    
#     # Plot 4: Robots with Inventory
#     ax = fig.add_subplot(gs[1, 1])
#     ax.plot(model_data.index, model_data['Green_Robots_With_Inventory'], label='Green Robots', marker='o', markersize=3, color='darkgreen')
#     ax.plot(model_data.index, model_data['Yellow_Robots_With_Inventory'], label='Yellow Robots', marker='s', markersize=3, color="orange")
#     ax.plot(model_data.index, model_data['Red_Robots_With_Inventory'], label='Red Robots', marker='^', markersize=3, color='darkred')
#     ax.set_xlabel('Step')
#     ax.set_ylabel('Number of Robots')
#     ax.set_title('Robots Carrying Waste')
#     ax.legend()
#     ax.grid(True, alpha=0.3)
    
#     # Plot 5: Summary Statistics 
#     ax = fig.add_subplot(gs[:, 2])
#     ax.axis('off')
def plot_results(model_data, filename=None):
    """Plot simulation results with ground, carried, and performance tracking + Text Summary"""
    
    fig = plt.figure(figsize=(20, 14))
    # 3 rows, 3 columns grid
    gs = gridspec.GridSpec(3, 3, figure=fig)
    fig.suptitle('Robot Waste Mission Analysis - Batch Report', fontsize=20, fontweight='bold')

    # --- [PLOT 1: Ground Waste] ---
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(model_data['Green_Waste_Ground'], color='green', label='Green')
    ax1.plot(model_data['Yellow_Waste_Ground'], color='gold', label='Yellow')
    ax1.plot(model_data['Red_Waste_Ground'], color='red', label='Red')
    ax1.set_title('Waste on Ground')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # --- [PLOT 2: Zone Coverage] ---
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(model_data['Visited_Ratio_Z1'], label='Z1 (Green)', color='#4caf50')
    ax2.plot(model_data['Visited_Ratio_Z2'], label='Z2 (Yellow)', color='#c6a700')
    ax2.plot(model_data['Visited_Ratio_Z3'], label='Z3 (Red)', color='#c24f4f')
    ax2.set_title('Exploration Coverage Ratio')
    ax2.set_ylim(0, 1.05)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # --- [PLOT 3: Transformations] ---
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.plot(model_data['Green_to_Yellow_Transformations'], label='G -> Y', color='darkgreen')
    ax3.plot(model_data['Yellow_to_Red_Transformations'], label='Y -> R', color='orange')
    ax3.set_title('Cumulative Transformations')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # --- [PLOT 4: Disposal Progress] ---
    ax4 = fig.add_subplot(gs[1, 0])
    ax4.fill_between(model_data.index, model_data['Waste_Disposed'], color='green', alpha=0.2)
    ax4.plot(model_data['Waste_Disposed'], color='green', linewidth=2)
    ax4.set_title('Total Waste Disposed')
    ax4.grid(True, alpha=0.3)

    # --- [PLOT 5: Collection Time Efficiency] ---
    ax5 = fig.add_subplot(gs[1, 1])
    ax5.plot(model_data['Avg_Green_Collection_Time'], label='Green Avg', color='darkgreen')
    ax5.plot(model_data['Avg_Yellow_Collection_Time'], label='Yellow Avg', color='orange')
    ax5.set_title('Avg Collection Time (1st -> 2nd)')
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    # --- [PLOT 6: Robots Carrying Cargo] ---
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.plot(model_data['Green_Robots_With_Inventory'], color='darkgreen', label='Green')
    ax6.plot(model_data['Yellow_Robots_With_Inventory'], color='orange', label='Yellow')
    ax6.plot(model_data['Red_Robots_With_Inventory'], color='darkred', label='Red')
    ax6.set_title('Robots Carrying Waste')
    ax6.legend()
    ax6.grid(True, alpha=0.3)

    # --- [PLOT 7: SUMMARY TEXT BOX] ---
    # We place this in the bottom row, spanning the middle and right columns for visibility
    ax_sum = fig.add_subplot(gs[2, :]) 
    ax_sum.axis('off')
    
    total_disposed = model_data['Waste_Disposed'].iloc[-1]
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
    
    ax_sum.text(0.5, 0.5, summary_text, fontsize=13, verticalalignment='center', 
                horizontalalignment='center', fontfamily='monospace', 
                bbox=dict(boxstyle='round,pad=1', facecolor='wheat', alpha=0.3))

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    if filename:
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"Results saved to '{filename}'")
    
    plt.tight_layout()
    # plt.savefig('./7_robot_mission_MAS2026/figures/robot_mission_results.png', dpi=150, bbox_inches='tight')
    # print("\n Results saved to './7_robot_mission_MAS2026/figures/robot_mission_results.png'")
    
    plt.close() # Close figure to free memory during batch runs


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
    BASE_PATH = "./7_robot_mission_MAS2026"
    CONFIG_DIR = os.path.join(BASE_PATH, "configs")
    RESULTS_DIR = os.path.join(BASE_PATH, "experiments/results")
    FIGURES_DIR = os.path.join(BASE_PATH, "experiments/figures")

    for folder in [CONFIG_DIR, RESULTS_DIR, FIGURES_DIR]:
        os.makedirs(folder, exist_ok=True)

    config_files = [f for f in os.listdir(CONFIG_DIR) if f.endswith('.json')]
    
    # Define the seeds you want to test for each configuration
    seeds_to_test = [7, 16, 32] 

    for config_file in config_files:
        config_id = os.path.splitext(config_file)[0]
        
        with open(os.path.join(CONFIG_DIR, config_file), 'r') as f:
            base_params = json.load(f)

        for s in seeds_to_test:
            # Override the seed in the parameters
            params = base_params.copy()
            params['seed'] = s
            
            # Create a unique ID for this specific run
            run_id = f"{config_id}_seed{s}"
            
            print(f"\n>>> Running: {run_id}")
            model, data = run_simulation(params)
            
            # Save individual plot
            plot_path = os.path.join(FIGURES_DIR, f"plot_{run_id}.png")
            plot_results(data, filename=plot_path)
            
            # Save individual CSV
            csv_path = os.path.join(RESULTS_DIR, f"data_{run_id}.csv")
            data.to_csv(csv_path)

    print("\nBatch processing with seed variation complete.")