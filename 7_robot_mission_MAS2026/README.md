# MAS PROJECT 2026: Robot Waste Collection
### Group 7

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [MAS Architecture Definition](#2-mas-architecture-definition)
3. [System Scope & Experimental Framework](#3-system-scope--experimental-framework)
4. [Agent Architecture](#4-agent-architecture)
5. [Environment Design](#5-environment-design)
6. [Agent Behavioral Strategies](#6-agent-behavioral-strategies)
7. [Interaction & Organization](#7-interaction--organization)
8. [Evaluation Criteria & Results](#8-evaluation-criteria--results)
9. [Configurations Tested](#9-configurations-tested)
10. [How to Run](#10-how-to-run)
11. [File Structure](#11-file-structure)

---

## 1. Project Overview

This project implements a **Multi-Agent Based Simulation (MABS)** of a robot waste collection mission. Multiple autonomous robots collaborate to collect, transform, and safely dispose of radioactive waste across a three-zone environment with varying levels of radioactivity.

![Grid layout](figs/fig1_grid_layout.png)

### Mission Summary

| Robot Type | Capabilities | Zone Access |
|---|---|---|
| Green Robot | Collects green waste (×2), transforms -> 1 yellow, deposits at z1/z2 frontier | z1 only |
| Yellow Robot | Collects yellow waste (×2), transforms -> 1 red, deposits at z2/z3 frontier | z1 + z2 |
| Red Robot | Collects red waste (×1), transports to disposal column | z1 + z2 + z3 |

### Waste Processing Pipeline

![Pipeline](figs/fig2_pipeline.png)

```
[Green Waste × 2] -> [Green Robot] -> [Yellow Waste × 1]
[Yellow Waste × 2] -> [Yellow Robot] -> [Red Waste × 1]
[Red Waste × 1]   -> [Red Robot]   -> [DISPOSED]
```

---

## 2. MAS Architecture Definition

### What makes this a MAS?

- **Multiple autonomous agents**: Three robot types act independently with encapsulated state and decision logic.
- **Shared environment**: A 2D grid divided into three radioactivity zones, serving as the common medium through which agents interact indirectly (via waste objects).
- **Distributed problem solving**: Each sub-problem (collection, transformation, transport) is solved by a specialized agent type; the global solution (complete disposal) emerges from local behaviors.
- **No direct communication** (Step 1): Agents do not send messages to each other. All coordination is implicit via the environment.

### Agent Classification

Our robots are **cognitive agents**:

| Property | Our Implementation |
|---|---|
| Internal state | `self.knowledge` dict: position, inventory beliefs, visited cells, move history, sweep direction, frontier mode |
| Memory | `visited` set tracking explored cells; `move_history` for backtrack avoidance |
| Deliberation | `deliberate(knowledge)` reasons from beliefs to prioritized actions |
| Action failures | `model.do()` validates feasibility; agent continues if action fails |
| Planning | No explicit planner, but goal-driven prioritized action selection |

> The `deliberate()` function takes only `knowledge` as input, it has **no access to external variables**, fulfilling the encapsulation requirement from the specification.

### Environment Properties

| Property | Classification | Justification |
|---|---|---|
| Observability | **Partially observable** | Agents only perceive their cell + 4 Von Neumann neighbors |
| Determinism | **Deterministic** | `model.do()` applies actions with guaranteed, unique effects |
| Dynamism | **Dynamic** | Other agents modify the environment (collect/deposit waste) between steps |
| Discreteness | **Discrete** | Finite grid cells, finite action set, integer steps |

### Coupling Level

This MAS is **loosely coupled**: no agent makes assumptions about other agents' states, positions, or intentions. All inter-agent coordination flows through the environment (waste objects at zone frontiers). This ensures robustness; removing or adding robots does not require design changes.

### Autonomy Level

- **Agent level**: Pro-active. Robots sweep zones autonomously, periodically scanning frontier columns without waiting for external triggers.
- **Interaction level**: Full autonomy, robots never explicitly request anything from other robots or the environment beyond their percept/action cycle.
- **MAS level**: No autonomy, robots are designed to achieve the collective mission. They follow well-defined zone rules and the global task emerges correctly by design.

---

## 3. System Scope & Experimental Framework

Following M&S theory:

### The Six M&S Entities

| Entity | Definition in this project |
|---|---|
| **Source System** | A hypothetical nuclear site requiring autonomous robotic decontamination |
| **Behavioral Database** | Observable data: waste counts per zone over time, disposal rate, robot cargo status |
| **Experimental Scope** | Objectives: (1) validate that all waste is eventually disposed; (2) measure efficiency (steps to full disposal); (3) observe emergent bottlenecks |
| **Model** | `model.py` + `agents.py` + `objects.py` : the full specification of environment and agent behaviors |
| **Simulator** | Mesa framework (Python) + Solara visualization server |
| **Modeling Relationship** | Acceptable simplification: robots are memoryless between sessions, no physical collisions, no energy constraints |
| **Simulation Relationship** | Verified via Mesa's scheduler (`shuffle_do`) and `DataCollector`, which faithfully execute the model |

### Objectives

The simulation is designed to answer:

1. **Correctness**: Can the multi-robot pipeline fully dispose of all waste within `max_steps`?
2. **Efficiency**: How many steps does disposal take as a function of robot counts and initial waste quantities?
3. **Bottleneck identification**: Which robot type creates the pipeline bottleneck?
4. **Coverage**: Do robots explore their zones effectively, or do large amounts of waste remain uncollected?

---

## 4. Agent Architecture

### The Perception–Deliberation–Action Loop

Each robot executes the following procedural loop every step:

![PDA loop](figs/fig5_pda_loop.png)

```python
def step_agent(self):
    percepts = self.model.perceive(self)        # Step 1: Environment -> Agent
    self.knowledge["pos"] = self.pos
    self.knowledge["observations"] = percepts
    self.knowledge["inventory"] = [w.waste_type for w in self.inventory]
    self.knowledge["visited"].add(self.pos)
    action = self.deliberate(self.knowledge)    # Step 2: Agent reasons
    if action:
        self.model.do(self, action)             # Step 3: Agent acts -> Environment
```

### What agents perceive

Each step, `model.perceive()` returns a dictionary of **dynamic, observable information only**, what is physically present on the grid right now. Static environment constants (grid dimensions, zone boundaries, frontier coordinates) are given to each robot once at `__init__` time and are not re-sent every step.

```python
percepts = {
    "agent_pos":      current (x, y),
    "waste_here":     [Waste objects in current cell, filtered by accessibility],
    "agents_here":    [other robot agents in current cell],
    "neighbors":      [nearby waste with positions and types],
    "radioactivity":  float in [0, 1],
    "zone":           "z1" | "z2" | "z3",
    "disposal_zone_x": rightmost column x-coordinate,
    "action_failed":  bool - True if last action was rejected by model.do()
}
```

### Knowledge Base per Robot Type

Each robot type receives exactly the information it needs, no more. Static values are set once at `__init__`; dynamic observations arrive every step via percepts.

![Knowledge base](figs/fig8_knowledge.png)

The design principle: `deliberate()` reads only from `knowledge`. It never calls `self.model`, `self.grid`, or any attribute outside its argument. Zone boundaries and frontier positions are stored in `knowledge` at initialisation so the deliberation function remains fully encapsulated.

### Deliberation Priority

All robot types share the same priority hierarchy, the first applicable rule fires and the rest are skipped:

![Deliberation priority](figs/fig6_deliberation.png)

### Green Robot Deliberation

```
if inventory has ≥ 2 green  ->  TRANSFORM to yellow
if inventory has yellow     ->  move EAST until deposit_frontier, then PUT DOWN
if green waste in cell      ->  PICK UP
if green waste in neighbor  ->  MOVE toward it
else                        ->  SWEEP z1 systematically
```

### Yellow Robot Deliberation

```
if inventory has ≥ 2 yellow  ->  TRANSFORM to red
if inventory has red         ->  move EAST until deposit_frontier, then PUT DOWN
if yellow waste in cell      ->  PICK UP
if yellow waste in neighbor  ->  MOVE toward it
periodically                 ->  FRONTIER SCAN at pickup_frontier (z1/z2 boundary)
if drifted into z1           ->  return EAST to z2
else                         ->  SWEEP z2 systematically
```

### Red Robot Deliberation

```
if inventory has red        ->  move EAST until disposal_x, then DISPOSE
if red waste in cell        ->  PICK UP
if red waste in neighbor    ->  MOVE toward it
periodically                ->  FRONTIER SCAN at pickup_frontier (z2/z3 boundary)
if drifted west of z3       ->  return EAST to z3
else                        ->  SWEEP z3 systematically
```

---

## 5. Environment Design

### Grid & Zone Layout

```
x=0                x=w/3             x=2w/3            x=w-1
|                  |                 |                  |
|   z1             |   z2            |   z3             | <- disposal
|   (radioactivity |  (radioactivity |   (radioactivity |   column
|   0.00–0.33)     |   0.33–0.66)    |   0.66–1.00)     |
|                  |                 |                  |
Green Robots       Yellow Robots     Red Robots         <- zone access
only               + z1              + z1 + z2
```

### Objects

| Class | Type | Attributes | Behavior |
|---|---|---|---|
| `Waste` | Passive | `waste_type`, `collected`, `carried_by` | None — pure data object |
| `RadioactivityCell` | Passive | `zone_name`, `radioactivity_level` | None, marks zone identity per cell |
| `WasteDisposalZone` | Passive | (none) | None, marks disposal column |

### Zone Restrictions (enforced by `model.do()`)

- Green robots: `can_move_to(pos)` returns True only if `pos.x =< z1_end`
- Yellow robots: `can_move_to(pos)` returns True only if `pos.x =< z2_end`
- Red robots: unrestricted

### Waste Accessibility Rules

```python
GreenRobot:  waste_type == GREEN  AND  pos.x =< z1_end
YellowRobot: waste_type == YELLOW AND (pos.x == z1_end OR z1_end < pos.x =< z2_end)
RedRobot:    waste_type == RED    AND (pos.x == z2_end OR pos.x > z2_end)
```

Yellow and red robots can also pick waste directly from the frontier column, this reduces unnecessary waiting for inter-robot handoffs.

### Action Set

| Action | Preconditions (checked by `model.do()`) | Effects |
|---|---|---|
| `move` | target within bounds, robot can enter zone | `grid.move_agent(agent, target_pos)` |
| `pick_up` | waste in same cell, waste accessible to robot type | waste added to `agent.inventory`, removed from grid |
| `transform` | ≥ 2 wastes of source type in inventory | source wastes removed, 1 new waste of target type added to inventory |
| `put_down` | inventory non-empty, robot at correct frontier x-coordinate | waste placed on grid at robot's current cell |
| `dispose` | inventory non-empty, robot at `disposal_zone_x` | waste removed from model, `waste_disposed += 1` |

---

## 6. Agent Behavioral Strategies

### Exploration Strategy: Systematic Sweep + Frontier Scanning

Rather than random walk, robots use a **boustrophedon (lawnmower) sweep**:

![Sweep strategy](figs/fig3_sweep.png)

The left panel shows the sweep pattern, the robot passes east along a row, steps south, then sweeps back west, covering the zone row by row. The right panel shows `_prefer_unvisited()` in action: when the natural sweep candidate is already visited, the robot picks a random unvisited neighbor instead (highlighted in yellow), maximising coverage.

- Direction tracked in `knowledge["sweep_dir"]` as `"east"` or `"west"`
- On hitting a zone boundary, robot steps one cell south and reverses direction
- When the candidate step is already visited, the robot biases toward any unvisited neighbor
- Recent move history (last 20 positions) prevents immediate backtracking

### Frontier Scanning (Yellow & Red Robots)

Yellow and Red robots additionally perform periodic **frontier scans** to detect waste deposited by upstream robots:

![Frontier scan](figs/fig4_frontier_scan.png)

1. Every `frontier_check_interval` steps (default: 8), `frontier_mode` activates
2. Robot navigates to its `pickup_frontier` x-column
3. Robot sweeps the full y-axis of that column
4. After completing the scan, counter resets and normal sweep resumes

This ensures waste deposited at zone boundaries is picked up promptly without requiring any direct communication between robot types.

### Anti-Backtracking

`_prefer_unvisited(pos, candidate)` applies a three-level fallback:

1. **Candidate unvisited** -> use it directly
2. **Candidate visited, unvisited neighbor exists** -> pick a random unvisited neighbor
3. **All neighbors visited** -> pick any neighbor that isn't where the robot just came from (`move_history[-2]`)

This prevents the robot from entering ping-pong loops when it has covered all nearby cells.

### Zone Return Logic

If a Yellow or Red robot drifts too far west, it immediately redirects eastward until back in its operational zone. This prevents robots from spending cycles searching in zones where their target waste cannot appear.

---

## 7. Interaction & Organization

### Indirect Coordination

Agents coordinate **indirectly** through the environment, without any direct communication:

![Stigmergy](figs/fig7_coordination.png)

```
Green Robot deposits yellow waste at x = z1_end (deposit_frontier)
        ↓  yellow waste object appears on grid
Yellow Robot perceives yellow waste during sweep or frontier scan
        ↓  collects it, transforms, deposits red waste at x = z2_end
Red Robot perceives red waste during sweep or frontier scan
        ↓  collects it, transports to disposal column, disposes
```

This is a **tightly coupled pipeline** by design, each robot type depends on the output of the upstream type, but **loosely coupled** in terms of agent interactions: no agent makes assumptions about the internal state of another.

### Scheduling

- **Synchronous** model: all robots execute one step per model `step()` call
- **Random activation order**: `shuffle_do("step_agent")` randomizes execution order within each step, preventing systematic bias where one robot type always acts before another

### Organization

| Level | Structure |
|---|---|
| Individual | Each robot has role-specific deliberation logic and zone constraints |
| Team | Three specialized roles forming a processing pipeline |
| System | Emergent property: global cleanup from local behaviors with no central coordinator |

---

## 8. Evaluation Criteria & Results

### Primary Metrics

| Metric | Description |
|---|---|
| **Disposal Rate** | `waste_disposed / step`, how fast waste is permanently removed |
| **Pipeline Throughput** | Number of transformation events per time window |
| **Collection Coverage** | Fraction of zone explored per robot per 50 steps |
| **Residual Waste** | Ground + carried waste remaining at `max_steps` |

### Baseline Configuration Results (seed=7)

### Bottleneck Analysis

---

## 9. Configurations Tested

---

## 10. How to Run

### Prerequisites

```bash
pip install mesa solara matplotlib pandas
```

### Option 1: Visual Interface (Solara)

```bash
solara run server.py
```

Opens a browser at `http://localhost:8765`. Use the sliders to adjust grid dimensions, number of robots, initial waste quantities, and max steps.

### Option 2: Headless Simulation

```bash
python run.py
```

Runs with default parameters (3G/2Y/1R robots, 10G/5Y/3R waste, 250 steps, seed=7). Edit the `run_simulation(...)` call at the bottom of `run.py` to test different configurations:

```python
model, data = run_simulation(
    n_steps=250,
    n_green_robots=5,
    n_yellow_robots=3,
    n_red_robots=2,
    n_initial_green_waste=30,
    n_initial_yellow_waste=5,
    n_initial_red_waste=3,
    seed=42
)
```

Outputs:

- `figs/robot_mission_results.png` - 4-panel results chart
- `results/robot_mission_data.csv` - step-by-step metrics

```bash
mkdir -p figs results   # create output directories before first run
```

---

## 11. File Structure

```
robot_mission_MAS2026/
│
├── agents.py         - Robot agent classes (GreenRobot, YellowRobot, RedRobot)
│                       BaseRobot with shared exploration, sweep, and frontier logic
│
├── model.py          - RobotMissionModel (Mesa Model)
│                       Grid setup, zone boundaries, percept generation, action execution
│
├── objects.py        - Passive environment objects
│                       Waste, RadioactivityCell, WasteDisposalZone
│
├── server.py         - Solara visualization server
│                       Grid display, inventory counters, live charts
│
├── run.py            - Headless simulation runner
│                       Configurable parameters, result plots, CSV export
│
├── figs/             - Figures (README illustrations + simulation result plots)
├── results/          - CSV data output
│
└── README.md         - This document
```

---

## Design Choices & Limitations

### Design Choices

- **Cognitive over reactive**: agents maintain visited-cell memory and move history, enabling more efficient systematic coverage than random walk.
- **Minimal knowledge per robot**: each robot type is given only the frontier coordinates relevant to its role. Shared constants (`grid_width`, `grid_height`) live in `knowledge` from `__init__`; dynamic observations arrive via percepts. `deliberate()` never accesses `self.model`.
- **Action feasibility in `model.do()`**: the environment is the sole authority on what is possible, agents cannot directly modify the grid; all changes go through `do()`.
- **Frontier scanning**: periodic proactive behavior prevents yellow/red robots from missing deposited waste even when their systematic sweep hasn't yet reached the frontier.
- **No communication (Step 1)**: coordination via environment (stigmergy) is sufficient for the pipeline to function correctly.

### Known Limitations

- With many green robots and sparse waste, robots may target the same waste cell; only one succeeds, the others waste a step.
- The sweep algorithm does not coordinate between same-type robots, two green robots may cover the same sub-zone redundantly.
- No learning or adaptation, robots do not update their strategy based on past performance.
