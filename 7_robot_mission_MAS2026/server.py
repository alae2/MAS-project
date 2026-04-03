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
    make_space_component,

)
from mesa.visualization.utils import update_counter
from svg_pltmarker import get_marker_from_svg

from model import RobotMissionModel
from agents import GreenRobot, YellowRobot, RedRobot
from objects import Waste, WasteType, RadioactivityCell, WasteDisposalZone

import warnings
warnings.filterwarnings("ignore")


# Markers
ROBOT_MARKER = get_marker_from_svg(filepath="markers/robot.svg")
WASTE_MARKER = get_marker_from_svg(filepath="markers/waste_marker.svg")
DEPOSAL_ZONE_MARKER = get_marker_from_svg(filepath="markers/waste_disposal.svg")




def agent_portrayal(agent):
    """
    Define how agents are displayed on the grid.
    Robots: large circles | Waste: smaller circles
    """
    if isinstance(agent, RadioactivityCell):
        zone_colors = {
            "z1": "#eeffee",
            "z2": "#f9f4e7",
            "z3": "#ffefef",
        }
        x, _ = agent.pos
        z1_end = agent.model.width // 3
        z2_end = (2 * agent.model.width) // 3
        is_frontier = x == z1_end or x == z2_end

        return {
            "size": 500,
            "color": "#9b9a9a" if is_frontier else zone_colors.get(agent.zone_name, "white"),
            "marker": "s",
            "alpha": 0.35 if is_frontier else 0.18,
            "zorder": 0 if is_frontier else -1,
        }

    if isinstance(agent, WasteDisposalZone):
        return {"size": 500, "color": "#ff0000", "marker": DEPOSAL_ZONE_MARKER, "alpha": 0.6, "linewidth": 0, "zorder": 1}

    if isinstance(agent, Waste):
        if agent.waste_type == WasteType.GREEN:
            color = "#00A210"
        elif agent.waste_type == WasteType.YELLOW:
            color = "#c4cb00"
        else:
            color = "#c60000"

        return {"size": 180, "color": color, "marker": WASTE_MARKER, "alpha": 0.95, "linewidth": 0, "zorder": 2}

    elif isinstance(agent, GreenRobot):
        return {"size": 300, "color": "#00ff91", "marker": ROBOT_MARKER, "alpha": 0.95, "linewidth": 0, "zorder": 3}

    elif isinstance(agent, YellowRobot):
        return {"size": 300, "color": "#ffbb00", "marker": ROBOT_MARKER, "alpha": 0.95, "linewidth": 0, "zorder": 3}

    elif isinstance(agent, RedRobot):
        return {"size": 300, "color": "#E5007A", "marker": ROBOT_MARKER, "alpha": 0.95, "linewidth": 0, "zorder": 3}

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


@solara.component
def TransformationsChart(model):
    """Display cumulative transformations over steps."""
    update_counter.get()

    fig = Figure(figsize=(6, 4))
    ax = fig.subplots()
    data = model.datacollector.get_model_vars_dataframe()

    ax.plot(
        data.index,
        data["Green_to_Yellow_Transformations"],
        label="Green -> Yellow",
        color="#1e8f42",
        linewidth=2,
    )
    ax.plot(
        data.index,
        data["Yellow_to_Red_Transformations"],
        label="Yellow -> Red",
        color="#d09000",
        linewidth=2,
    )
    ax.set_xlabel("Step")
    ax.set_ylabel("Cumulative Transformations")
    ax.set_title("Transformations Over Time")
    ax.legend()
    ax.grid(True, alpha=0.3)

    solara.FigureMatplotlib(fig)


@solara.component
def GroundWasteOverTimeChart(model):
    """Display on-ground waste counts per type over steps."""
    update_counter.get()

    fig = Figure(figsize=(6, 4))
    ax = fig.subplots()
    data = model.datacollector.get_model_vars_dataframe()

    ax.plot(data.index, data["Green_Waste_Ground"], label="Green", color="#00A210", linewidth=2)
    ax.plot(data.index, data["Yellow_Waste_Ground"], label="Yellow", color="#c4cb00", linewidth=2)
    ax.plot(data.index, data["Red_Waste_Ground"], label="Red", color="#c60000", linewidth=2)
    ax.set_xlabel("Step")
    ax.set_ylabel("On-Ground Waste Count")
    ax.set_title("On-Ground Waste Over Time")
    ax.legend()
    ax.grid(True, alpha=0.3)

    solara.FigureMatplotlib(fig)


@solara.component
def CollectionTimeChart(model):
    """Display average first->second pickup time for green and yellow robots."""
    update_counter.get()

    fig = Figure(figsize=(6, 4))
    ax = fig.subplots()
    data = model.datacollector.get_model_vars_dataframe()

    ax.plot(data.index, data["Avg_Green_Collection_Time"], label="Green", color="#1e8f42", linewidth=2)
    ax.plot(data.index, data["Avg_Yellow_Collection_Time"], label="Yellow", color="#d09000", linewidth=2)
    ax.set_xlabel("Step")
    ax.set_ylabel("Average Steps (1st -> 2nd Pickup)")
    ax.set_title("Average Collection Time")
    ax.legend()
    ax.grid(True, alpha=0.3)

    solara.FigureMatplotlib(fig)


@solara.component
def ZoneCoverageChart(model):
    """Display visited-cell ratio per zone over steps."""
    update_counter.get()

    fig = Figure(figsize=(6, 4))
    ax = fig.subplots()
    data = model.datacollector.get_model_vars_dataframe()

    ax.plot(data.index, data["Visited_Ratio_Z1"], label="z1", color="#4caf50", linewidth=2)
    ax.plot(data.index, data["Visited_Ratio_Z2"], label="z2", color="#c6a700", linewidth=2)
    ax.plot(data.index, data["Visited_Ratio_Z3"], label="z3", color="#c24f4f", linewidth=2)
    ax.set_xlabel("Step")
    ax.set_ylabel("Visited Ratio")
    ax.set_ylim(0, 1.05)
    ax.set_title("Visited Cells Ratio Per Zone")
    ax.legend()
    ax.grid(True, alpha=0.3)

    solara.FigureMatplotlib(fig)


# Model parameters
model_params = {
    "exploration_mode": Slider("Exploration Mode", value=0, min=0, max=2, step=1),
    "width": Slider("Grid Width", value=20, min=10, max=60, step=5),
    "height": Slider("Grid Height", value=20, min=10, max=30, step=5),
    "n_green_robots": Slider("Green Robots", value=5, min=1, max=10, step=1),
    "n_yellow_robots": Slider("Yellow Robots", value=3, min=0, max=8, step=1),
    "n_red_robots": Slider("Red Robots", value=2, min=0, max=5, step=1),
    "n_initial_green_waste": Slider("Initial Green Waste", value=12, min=0, max=50, step=2),
    "n_initial_yellow_waste": Slider("Initial Yellow Waste", value=4, min=0, max=40, step=2),
    "n_initial_red_waste": Slider("Initial Red Waste", value=2, min=0, max=30, step=2),
    "max_steps": Slider("Max Steps", value=150, min=50, max=1000, step=25),
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
        TransformationsChart,
        GroundWasteOverTimeChart,
        CollectionTimeChart,
        ZoneCoverageChart,
    ],
    model_params=model_params,
    name="Robot Waste Collection Mission - Group 7",
)
page
