"""
Group: 7
Members: Ouissal BOUTOUATOU, Alae TAOUDI, Mohammed SBAIHI
Date:
Description: Web visualization server for Robot Waste Collection MAS using Solara
Run with: solara run server.py
"""

import solara
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from mesa.visualization import (
    SolaraViz,
    Slider,
    make_plot_component,
    make_space_component,
)
from mesa.visualization.utils import update_counter

from model import RobotMissionModel
from agents import GreenRobot, YellowRobot, RedRobot
from objects import Waste, WasteType, RadioactivityCell, WasteDisposalZone


def agent_portrayal(agent):
    """
    Define how agents are displayed on the grid.
    Robots: large circles | Waste: smaller circles
    """
    if isinstance(agent, RadioactivityCell):
        zone_colors = {
            "z1": "#e6f4e6",
            "z2": "#fff3d6",
            "z3": "#fde2e2",
        }
        x, _ = agent.pos
        z1_end = agent.model.width // 3
        z2_end = (2 * agent.model.width) // 3
        is_frontier = x == z1_end or x == z2_end
        return {
            "size": 1000,
            "color": "#9b9a9a" if is_frontier else zone_colors.get(agent.zone_name, "white"),
            "marker": "s",
            "alpha": 0.35 if is_frontier else 0.18,
        }

    if isinstance(agent, WasteDisposalZone):
        return {"size": 300, "color": "#7674f4", "marker": "s", "alpha": 0.6}

    if isinstance(agent, Waste):
        if agent.waste_type == WasteType.GREEN:
            color = "#059934"
        elif agent.waste_type == WasteType.YELLOW:
            color = "#feb924"
        else:  
            color = "#fb3e3e"
        return {"size": 60, "color": color, "marker": "."}
    
    elif isinstance(agent, GreenRobot):
        return {"size": 180, "color": "#0b3402", "marker": "o", "alpha": 0.95}
    
    elif isinstance(agent, YellowRobot):
        return {"size": 180, "color": "#e4e40a", "marker": "o", "alpha": 0.95}
    
    elif isinstance(agent, RedRobot):
        return {"size": 180, "color": "#641313", "marker": "o", "alpha": 0.95}
    
    return {}


@solara.component
def InventoryCounter(model):
    """Display current inventory statistics with ground and carried waste"""
    update_counter.get()
    
    green_robots_with_inv = model._count_robots_with_inventory(GreenRobot)
    yellow_robots_with_inv = model._count_robots_with_inventory(YellowRobot)
    red_robots_with_inv = model._count_robots_with_inventory(RedRobot)
    
    # Ground waste
    green_ground = model._count_waste(WasteType.GREEN)
    yellow_ground = model._count_waste(WasteType.YELLOW)
    red_ground = model._count_waste(WasteType.RED)
    
    # Carried waste
    green_carried = model._count_carried_waste(WasteType.GREEN)
    yellow_carried = model._count_carried_waste(WasteType.YELLOW)
    red_carried = model._count_carried_waste(WasteType.RED)
    
    stats_text = f"""
    ------------------ MODEL PARAMETERS ------------------
    Grid: {model.width}x{model.height} | Step: {model.steps}/{model.max_steps}
    
    ------------------ WASTE INVENTORY ------------------
    GREEN WASTE:  Ground: {green_ground}  |  Carried: {green_carried}
    YELLOW WASTE: Ground: {yellow_ground}  |  Carried: {yellow_carried}
    RED WASTE:    Ground: {red_ground}   |  Carried: {red_carried}
    
    DISPOSAL PROGRESS: {model.waste_disposed} waste disposed
    
    ROBOTS WITH CARGO:
      Green Robots: {green_robots_with_inv}  |  Yellow Robots: {yellow_robots_with_inv}  |  Red Robots: {red_robots_with_inv}
    """
    
    solara.Markdown(f"```\n{stats_text}\n```")


@solara.component
def WasteDistributionChart(model):
    """Display waste distribution (ground vs carried) using Matplotlib"""
    update_counter.get()
    
    fig = Figure(figsize=(6, 4))
    ax = fig.subplots()
    
    waste_ground = [
        model._count_waste(WasteType.GREEN),
        model._count_waste(WasteType.YELLOW),
        model._count_waste(WasteType.RED),
    ]
    
    waste_carried = [
        model._count_carried_waste(WasteType.GREEN),
        model._count_carried_waste(WasteType.YELLOW),
        model._count_carried_waste(WasteType.RED),
    ]
    
    types = ["Green", "Yellow", "Red"]
    x = range(len(types))
    width = 0.35
    
    ax.bar([i - width/2 for i in x], waste_ground, width, label="Ground", color=["lightgreen", "lightyellow", "lightcoral"])
    ax.bar([i + width/2 for i in x], waste_carried, width, label="Carried", color=["darkgreen", "orange", "darkred"])
    
    ax.set_ylabel("Count")
    ax.set_title("Waste Distribution: Ground vs Carried")
    ax.set_xticks(x)
    ax.set_xticklabels(types)
    ax.legend()
    ax.set_ylim(0, max(max(waste_ground), max(waste_carried)) + 5)
    
    solara.FigureMatplotlib(fig)


@solara.component
def DisposalChart(model):
    """Display cumulative waste disposal using Matplotlib"""
    update_counter.get()
    
    fig = Figure(figsize=(6, 4))
    ax = fig.subplots()
    
    data = model.datacollector.get_model_vars_dataframe()
    
    ax.plot(data.index, data["Waste_Disposed"], color="green", linewidth=2, marker='o', markersize=4)
    ax.fill_between(data.index, data["Waste_Disposed"], alpha=0.3, color="green")
    ax.set_xlabel("Step")
    ax.set_ylabel("Waste Disposed")
    ax.set_title("Cumulative Waste Disposal")
    ax.grid(True, alpha=0.3)
    
    solara.FigureMatplotlib(fig)


# Model parameters
model_params = {
    "width": Slider("Grid Width", value=40, min=20, max=60, step=5),
    "height": Slider("Grid Height", value=20, min=10, max=30, step=5),
    "n_green_robots": Slider("Green Robots", value=5, min=1, max=10, step=1),
    "n_yellow_robots": Slider("Yellow Robots", value=3, min=1, max=8, step=1),
    "n_red_robots": Slider("Red Robots", value=2, min=1, max=5, step=1),
    "n_initial_green_waste": Slider("Initial Green Waste", value=30, min=5, max=50, step=5),
    "n_initial_yellow_waste": Slider("Initial Yellow Waste", value=5, min=0, max=40, step=5),
    "n_initial_red_waste": Slider("Initial Red Waste", value=3, min=0, max=30, step=5),
    "max_steps": Slider("Max Steps", value=150, min=50, max=500, step=50),
}

SpaceGraph = make_space_component(agent_portrayal, backend="matplotlib")

# Create initial model instance
initial_model = RobotMissionModel()

page = SolaraViz(
    initial_model,
    components=[
        SpaceGraph,
        InventoryCounter,
        WasteDistributionChart,
        DisposalChart,
    ],
    model_params=model_params,
    name="Robot Waste Collection Mission - Group 7",
)
page
