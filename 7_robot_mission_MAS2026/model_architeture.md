# Robot Mission MAS: Model, Architecture, Behaviors, and Design Choices

## 1) What this system models

This project implements a multi-agent waste processing pipeline on a 2D grid, where waste is progressively transformed and moved east across three risk zones:

- z1 (west): low radioactivity, source zone for green waste
- z2 (middle): medium radioactivity, staging/transformation zone
- z3 (east): high radioactivity, final handling and disposal

The core idea is role specialization:

- Green robots perform stage 1 collection/transformation
- Yellow robots perform stage 2 collection/transformation
- Red robots perform final transport/disposal

The environment, not the robots, is the authority that validates and applies actions.

## 2) High-level architecture

The system follows a clean split between agent reasoning and environment execution.

### Main modules

- objects.py
  - Defines passive entities:
    - Waste with type GREEN, YELLOW, RED
    - RadioactivityCell for per-cell zone metadata
    - WasteDisposalZone markers on the east boundary
- agents.py
  - Defines robot agent classes and decision logic:
    - BaseRobot with generic control loop and movement helpers
    - GreenRobot, YellowRobot, RedRobot with specialized behavior
- model.py
  - Defines RobotMissionModel, the environment:
    - Grid creation and zoning
    - Robot and waste initialization
    - Perception API for agents
    - Action execution and constraint checking
    - Data collection and diagnostics
- run.py
  - Batch simulation runner, summary stats, and export plots/CSV
- server.py
  - Solara interactive visualization, live counters and charts

### Control loop pattern

Each robot executes the same loop every step:

1. Perceive: get local observations from model.perceive(agent)
2. Update knowledge: internal beliefs (position, inventory, visited cells, etc.)
3. Deliberate: choose one action dict based on robot-specific policy
4. Act: send action to model.do(agent, action)

Important: robots decide intent, while the model enforces world rules.

## 3) Environment model and zoning

The grid is created as a Mesa MultiGrid and split by x-coordinate into three non-overlapping zones:

- Z1: x from 0 to width/3
- Z2: x from width/3 + 1 to 2*width/3
- Z3: x from 2*width/3 + 1 to width - 1

Each cell receives:

- a zone label (z1, z2, z3)
- a sampled radioactivity level range consistent with the zone

A disposal area is created as the whole eastmost column (x = width - 1).

## 4) Robot capabilities and behavior policies

## Green robot

Role:

- collect green waste
- transform 2 GREEN into 1 YELLOW
- move YELLOW east and put it down at the z1/z2 frontier

Movement constraint:

- cannot move beyond Z1 (max x limited to end of z1)

Policy summary:

1. If carrying at least 2 GREEN, request transform GREEN -> YELLOW
2. Else if carrying YELLOW, move east toward frontier and put down there
3. Else if GREEN exists in current cell, pick it up
4. Else continue systematic sweep exploration inside allowed zone

## Yellow robot

Role:

- collect yellow waste
- transform 2 YELLOW into 1 RED
- move RED east and put it down at the z2/z3 frontier

Movement constraint:

- can move in z1 and z2 only

Policy summary:

1. If carrying at least 2 YELLOW, request transform YELLOW -> RED
2. Else if carrying RED, move east toward frontier and put down there
3. Else if YELLOW exists in current cell, pick it up
4. Periodically revisit frontier to capture new incoming YELLOW
5. Otherwise sweep mainly in zone-2 corridor

## Red robot

Role:

- collect red waste
- carry RED east to disposal column
- dispose permanently in disposal zone

Movement constraint:

- can move in all zones (up to z3 max x)

Policy summary:

1. If carrying RED, move east to disposal column and dispose
2. Else if RED exists in current cell, pick it up
3. Periodically revisit z2/z3 frontier for newly produced RED
4. Otherwise sweep inside zone 3

## 5) Action model and rule enforcement

Robots output action dictionaries such as move, pick_up, transform, put_down, dispose. The model validates each action before applying it.

### Supported actions

- move
  - checks bounds
  - checks robot zone constraint (can_move_to)
- pick_up
  - must target waste in same cell
  - waste is removed from grid and added to robot inventory
- transform
  - GREEN -> YELLOW requires at least 2 GREEN in inventory
  - YELLOW -> RED requires at least 2 YELLOW in inventory
  - transformation consumes two items and creates one item
- put_down
  - only allowed at correct frontier and with correct waste type:
    - Green robot puts YELLOW at z1/z2 frontier
    - Yellow robot puts RED at z2/z3 frontier
    - Red robot can put RED only at disposal column
- dispose
  - only valid at disposal column
  - removes one carried waste permanently
  - increments disposed counter

This design ensures robot decisions cannot violate environment constraints.

## 6) Perception and access control

perceive(agent) gives each robot:

- current position
- waste present in current cell
- nearby waste observations
- target frontier (depends on robot type)
- radioactivity level and zone
- disposal column x

Waste visibility/pickability is filtered by robot type and location via an accessibility function. This enforces role correctness:

- Green handles GREEN in z1
- Yellow handles YELLOW at/inside z2 corridor and frontier
- Red handles RED at/inside z3 corridor and frontier

## 7) Exploration strategy (detailed)

Exploration is not random. It is a constrained sweep policy with memory and role-specific priorities.

### 7.1 Shared exploration engine in BaseRobot

All robot types inherit the same movement helpers from BaseRobot:

- can_move_to(position)
  - validates zone limits using each robot's max_zone belief
- _plan_exploration_step(pos)
  - performs a horizontal snake sweep across all reachable columns:
    - move east until blocked by boundary/zone limit
    - when blocked, move one row down, reverse direction to west
    - at bottom row, reverse and move up if needed
- _plan_exploration_step_in_range(pos, min_x, max_x)
  - same snake sweep but inside a corridor (used by Yellow and Red)
- _prefer_unvisited(pos, candidate)
  - if candidate was already visited, tries an unvisited valid neighbor first
  - if all neighbors were visited, avoids immediate backtracking when possible
- _remember_move(pos)
  - stores recent positions to reduce local loops

### 7.2 Internal memory used for exploration

Each robot stores a knowledge dictionary that includes:

- visited: set of all visited cells
- move_history: short rolling history of recent positions
- sweep_dir: current horizontal direction (east or west)
- frontier_check_interval and steps_since_frontier: timers for frontier revisits

This memory transforms exploration from reactive movement to stateful coverage.

### 7.3 Green robot exploration behavior

Green robot priority order:

1. Transform if it has 2 GREEN
2. If carrying YELLOW, move east to z1/z2 frontier and drop
3. If current cell has GREEN, pick it up
4. Otherwise sweep all reachable cells in z1

Because max_zone is z1 end, Green robot can explore broadly in z1 but can never enter z2.

### 7.4 Yellow robot exploration behavior

Yellow robot uses both coverage and handoff-aware behavior:

1. Transform if it has 2 YELLOW
2. If carrying RED, move east to z2/z3 frontier and drop
3. If current cell has YELLOW, pick it up
4. Every N steps (frontier_check_interval), return to z1/z2 frontier to catch newly dropped YELLOW
5. If too far west, move back toward zone 2
6. Otherwise sweep in a constrained corridor (mostly z2)

This prevents Yellow robots from drifting too far from supply points while still exploring.

### 7.5 Red robot exploration behavior

Red robot uses the same pattern as Yellow, shifted east:

1. If carrying RED, move to disposal column and dispose
2. If current cell has RED, pick it up
3. Every N steps, revisit z2/z3 frontier to catch newly dropped RED
4. If west of z3, move east back into z3
5. Otherwise sweep inside z3 corridor

### 7.6 Why this works well

- Sweep gives systematic spatial coverage
- Visited and move history reduce oscillation and wasted moves
- Frontier checks synchronize upstream/downstream robots without direct messaging
- Zone-constrained sweeps enforce safety constraints automatically

Net effect: the system approximates a production line where each stage alternates between local harvesting and frontier synchronization.

## 8) Data, metrics, and observability

The model collects step-wise metrics using Mesa DataCollector:

- waste counts on ground by type
- waste counts carried by robots by type
- cumulative disposed waste
- number of robots carrying inventory by color

run.py uses these metrics to:

- print final summary stats
- generate figures for progression and workload
- export CSV for analysis

server.py provides interactive monitoring with:

- grid visualization of zones/robots/waste
- live inventory panel
- waste distribution chart (ground vs carried)
- disposal trend chart
- sliders for scenario parameters

## 9) Key design choices and rationale

## Choice A: Environment-authoritative action execution

Why:

- avoids invalid state transitions from agent logic bugs
- centralizes constraints and side effects

Impact:

- easier to test invariants (zone limits, disposal rules)
- cleaner separation of concerns

## Choice B: Typed waste transformation pipeline

Why:

- models staged hazardous processing
- creates clear inter-robot dependencies and cooperation dynamics

Impact:

- emergent handoff behavior at frontiers
- measurable bottlenecks by stage

## Choice C: Zone-restricted mobility by robot type

Why:

- reflects risk specialization
- enforces role boundaries without hard-coding path scripts

Impact:

- realistic spatial division of labor
- predictable safety envelope per robot class

## Choice D: Frontier-based handoff instead of direct communication

Why:

- keeps system decentralized
- enables stigmergic coordination through environment state

Impact:

- simpler protocol (drop/pick at borders)
- robust to asynchronous robot schedules

## Choice E: Hybrid exploration (sweep + frontier revisit)

Why:

- pure sweeping can miss newly deposited frontier waste for too long
- pure frontier camping wastes coverage

Impact:

- better throughput across production chain
- reduced idle behavior in downstream robots

## 10) Initialization and scenario behavior notes

The model supports configurable initial waste counts for all three types.

- In model defaults, initial yellow and red are zero.
- In run.py and server.py defaults, initial yellow/red are non-zero.

Interpretation:

- You can run a pure pipeline scenario (only initial GREEN) or a mixed-load scenario (pre-seeded YELLOW/RED).
- Both are valid, but they represent different experiments.

## 11) Code architecture: classes, inheritance, and connections

This section explains how classes are defined and how they collaborate at runtime.

### 11.1 Core class map

- RobotMissionModel (model.py)
  - Subclass of mesa.Model
  - Owns the grid, zone boundaries, disposal definition, metrics, and simulation loop
- BaseRobot (agents.py)
  - Subclass of mesa.Agent
  - Defines shared control loop and exploration utilities
- GreenRobot, YellowRobot, RedRobot (agents.py)
  - Subclasses of BaseRobot
  - Override deliberate(knowledge) for role-specific policy
- Waste, RadioactivityCell, WasteDisposalZone (objects.py)
  - Subclasses of mesa.Agent
  - Passive entities representing physical environment state

### 11.2 Inheritance relationships

- mesa.Agent
  - BaseRobot
    - GreenRobot
    - YellowRobot
    - RedRobot
  - Waste
  - RadioactivityCell
  - WasteDisposalZone

All active robots share one abstract behavior skeleton (BaseRobot), then specialize only decision rules.

### 11.3 Runtime call flow per step

At each model step:

1. RobotMissionModel.step() selects robot agents and executes step_agent() in random order
2. BaseRobot.step_agent() asks model.perceive(self)
3. BaseRobot updates knowledge (position, inventory, observations, visited, timers)
4. Specific robot class runs deliberate(knowledge) and returns an action dict
5. BaseRobot sends action to model.do(self, action)
6. RobotMissionModel.do() dispatches to _do_move/_do_pick_up/_do_transform/_do_put_down/_do_dispose
7. Model validates constraints and mutates environment state if valid
8. DataCollector stores metrics for analysis/plots

This gives clear single responsibility:

- Agents: policy and intent
- Model: rule enforcement and state transitions

### 11.4 How classes are connected through data

- Robot inventory stores Waste instances currently carried
- Waste.carried_by records carrier robot unique_id
- model.perceive builds observations from grid contents and filters accessible waste
- can_move_to uses robot knowledge max_zone to enforce mobility safety
- zone boundaries and disposal column are model-level constants referenced by both perception and actions

