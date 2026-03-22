# MAS-project


## Project Overview
This Multi-Agent System (MAS) simulates a collaborative robotic mission to decontaminate a radioactive environment. Robots must collect, transform, and transport hazardous waste across three zones of increasing radioactivity ($z_1$ to $z_3$) to a secure disposal area.

---

## Problem Modeling

### 1. Environment & Zones
The environment is a grid divided into three distinct radioactive zones:
* **$z_1$ (Low):** Contains initial **Green Waste**.
* **$z_2$ (Medium):** Intermediate transition zone.
* **$z_3$ (High):** Contains the **Waste Disposal Zone** for final storage.

### 2. Agent Roles & Capabilities
The system relies on a specialized pipeline where robots must collaborate to "upgrade" waste for final disposal:

| Robot Type | Access | Primary Action | Transformation Logic |
| :--- | :--- | :--- | :--- |
| **Green** | $z_1$ only | Collect 2 Green | 2 Green $\rightarrow$ 1 Yellow |
| **Yellow** | $z_1, z_2$ | Collect 2 Yellow | 2 Yellow $\rightarrow$ 1 Red |
| **Red** | $z_1, z_2, z_3$ | Collect 1 Red | Transport to Disposal Zone |

## System Architecture
The project follows a modular MAS structure using a **Percept-Deliberate-Do** cycle for agent reasoning.

### Core Components
* **`agents.py`**: Defines the logic for `greenAgent`, `yellowAgent`, and `redAgent`.
    * **Percepts**: Gathers data on adjacent tiles (waste, other agents, radioactivity).
    * **Deliberate**: Decision-making logic based on `self.knowledge` (e.g., move, pick up, transform).
    * **Do**: Communicates chosen actions back to the environment.
* **`objects.py`**: Contains non-behavioral entities:
    * **Radioactivity Agents**: Static markers defining zone boundaries and radiation levels ($0.0$ to $1.0$).
    * **Waste Agents**: Green, Yellow, or Red objects.
    * **Waste Disposal Zone**: The target destination in the far east.
* **`model.py`**: The orchestrator. Manages the grid, agent schedules, and the `do()` method which validates and executes actions.


## File Structure
```text
numberofthegroup_robot_mission_MAS2026/
├── agents.py   # Robot agent classes & logic
├── objects.py  # Environment entities (Waste, Radioactivity)
├── model.py    # Simulation setup & action validation (Model.do)
├── server.py   # Visualization settings
└── run.py      # Simulation entry point
```

## Implementation Phases
1.  **Step 1**: Basic coordination using random walk or memory-based navigation.
2.  **Step 2**: Enhanced collaboration through inter-agent communication.
3.  **Step 3**: Handling environmental uncertainties (TBA).
