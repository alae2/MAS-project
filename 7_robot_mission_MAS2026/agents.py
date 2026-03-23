"""
Group: 7
Members:
Date:
Description: Robot Agent classes for Waste Collection MAS.

Key design principles (Step 1 — memory-based navigation):
  - Agents have NO global knowledge of waste positions.
  - Each robot maintains an explored_map of cells it has visited,
    and a known_waste dict of waste positions discovered during exploration.
  - Navigation uses BFS on the explored/frontier graph to reach targets
    or to find the next unvisited cell.
  - Percepts contain ONLY what is locally visible (current cell + 4 neighbours).
"""

import mesa
from collections import deque
from enum import Enum


# ---------------------------------------------------------------------------
# Shared enumerations
# ---------------------------------------------------------------------------

class WasteType(Enum):
    """Enumerate waste types."""
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class RobotType(Enum):
    """Enumerate robot types."""
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


# ---------------------------------------------------------------------------
# Base robot
# ---------------------------------------------------------------------------

class BaseRobot(mesa.Agent):
    """
    Base class for all robot types.

    Internal knowledge base
    -----------------------
    pos          : current position (updated from percepts each step)
    inventory    : list of WasteType enums currently held
    max_zone_x   : maximum x-coordinate this robot may occupy
    explored_map : set of (x, y) positions the robot has visited
    known_waste  : dict {(x,y): WasteType} — waste the robot has seen
    mode         : "explore" | "collect" | "deposit"
    """

    def __init__(self, model, robot_type: RobotType):
        super().__init__(model)
        self.robot_type = robot_type
        self.inventory: list = []  # list of Waste objectsf     

        self.knowledge = {
            "pos": None,
            "inventory": [],           # WasteType enums for quick inspection
            "max_zone_x": None,        # Set by subclass __init__
            "explored_map": set(),     # Cells visited by this robot
            "known_waste": {},         # {pos: WasteType} discovered locally
            "frontier": deque(),       # BFS frontier for exploration
            "mode": "explore",         # Current behavioural mode
        }

    # ------------------------------------------------------------------
    # Main control loop
    # ------------------------------------------------------------------

    def step_agent(self):
        """Percept → update knowledge → deliberate → do."""
        percepts = self.model.perceive(self)

        # --- Update knowledge from local percepts only ---
        self.knowledge["pos"] = self.pos
        self.knowledge["inventory"] = [w.waste_type for w in self.inventory]

        # Mark current cell as explored
        self.knowledge["explored_map"].add(self.pos)

        # Record any waste visible in current cell or immediate neighbours
        for waste_info in percepts.get("waste_here", []):
            self.knowledge["known_waste"][self.pos] = waste_info.waste_type

        for nb in percepts.get("neighbors", []):
            if nb["type"] == "waste":
                self.knowledge["known_waste"][nb["pos"]] = nb["waste_type"]

        # Remove from known_waste if we are standing on a cell that is now empty
        if not percepts.get("waste_here") and self.pos in self.knowledge["known_waste"]:
            del self.knowledge["known_waste"][self.pos]

        # Add unvisited accessible neighbours to the exploration frontier
        self._update_frontier(percepts)

        # --- Deliberate ---
        action = self.deliberate(self.knowledge, percepts)

        # --- Execute ---
        if action:
            self.model.do(self, action)

    # ------------------------------------------------------------------
    # Frontier / BFS helpers
    # ------------------------------------------------------------------

    def _update_frontier(self, percepts):
        """
        Add unvisited, accessible neighbour cells to the frontier queue.
        The frontier drives exploration: the robot pops from it when it
        has nothing more important to do.
        """
        explored = self.knowledge["explored_map"]
        frontier_set = set(self.knowledge["frontier"])

        for nb in percepts.get("neighbors", []):
            nb_pos = nb["pos"]
            if nb_pos not in explored and nb_pos not in frontier_set:
                if self.can_move_to(nb_pos):
                    self.knowledge["frontier"].append(nb_pos)

    def _bfs_next_step(self, target_pos):
        """
        Return the next adjacent step towards target_pos using BFS over
        the robot's explored_map.  Falls back to a greedy Manhattan step
        if BFS cannot find a path (unexplored territory between agent and
        target — the robot will re-route as it explores more).

        Returns (dx, dy) as one of the four cardinal neighbours of self.pos,
        or None if already at target.
        """
        if self.pos == target_pos:
            return None

        explored = self.knowledge["explored_map"]
        start = self.pos
        width = self.model.grid.width
        height = self.model.grid.height
        max_x = self.knowledge["max_zone_x"]

        # BFS
        queue = deque([(start, [])])
        visited = {start}

        while queue:
            current, path = queue.popleft()

            cx, cy = current
            for nx, ny in [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]:
                nb = (nx, ny)
                if nb in visited:
                    continue
                if not (0 <= nx < width and 0 <= ny < height):
                    continue
                if nx > max_x:
                    continue

                new_path = path + [nb]

                if nb == target_pos:
                    return new_path[0] if new_path else None

                # Only traverse explored cells (we know they are passable)
                if nb in explored:
                    visited.add(nb)
                    queue.append((nb, new_path))

        # BFS failed (target not reachable through explored cells yet)
        # → greedy Manhattan step towards target, respecting bounds
        tx, ty = target_pos
        px, py = self.pos
        candidates = []
        if tx > px and px + 1 <= max_x:
            candidates.append((px+1, py))
        if tx < px and px - 1 >= 0:
            candidates.append((px-1, py))
        if ty > py and py + 1 < height:
            candidates.append((px, py+1))
        if ty < py and py - 1 >= 0:
            candidates.append((px, py-1))

        if candidates:
            return min(candidates, key=lambda p: abs(p[0]-tx)+abs(p[1]-ty))
        return None

    # ------------------------------------------------------------------
    # Constraint helper
    # ------------------------------------------------------------------

    def can_move_to(self, position):
        """Return True if position is within this robot's zone limit."""
        x, _ = position
        return x <= self.knowledge["max_zone_x"]

    # ------------------------------------------------------------------
    # Abstract deliberate
    # ------------------------------------------------------------------

    def deliberate(self, knowledge, percepts):
        """
        Choose an action based on knowledge and latest percepts.
        Must be overridden by subclasses.

        Returns an action dict or None.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Green Robot
# ---------------------------------------------------------------------------

class GreenRobot(BaseRobot):
    """
    Operates in z1 only.
    - Collects green waste (picks up 1 at a time, needs 2 total).
    - Transforms 2 green → 1 yellow.
    - Deposits yellow waste anywhere in z1 (green robots leave it for
      yellow robots to pick up; yellow robots can move into z1 to collect).
    """

    def __init__(self, model):
        super().__init__(model, RobotType.GREEN)
        z1_end = model.zone_boundaries[0][1][1]
        self.knowledge["max_zone_x"] = z1_end

    def deliberate(self, knowledge, percepts):
        pos = knowledge["pos"]
        inventory = knowledge["inventory"]
        known_waste = knowledge["known_waste"]
        explored = knowledge["explored_map"]
        frontier = knowledge["frontier"]

        # ---- 1. Transform if we have 2 green ----
        if inventory.count(WasteType.GREEN) >= 2:
            return {
                "action": "transform",
                "from_type": WasteType.GREEN,
                "to_type": WasteType.YELLOW,
            }

        # ---- 2. Deposit yellow waste (put it down anywhere in z1) ----
        if inventory.count(WasteType.YELLOW) >= 1:
            # Put it down immediately — yellow robots can come collect it
            return {"action": "put_down"}

        # ---- 3. Pick up green waste in current cell ----
        for waste in percepts.get("waste_here", []):
            if waste.waste_type == WasteType.GREEN:
                return {"action": "pick_up", "target": waste}

        # ---- 4. Navigate to nearest known green waste ----
        green_targets = [
            p for p, wt in known_waste.items() if wt == WasteType.GREEN
        ]
        if green_targets:
            nearest = min(
                green_targets,
                key=lambda p: abs(p[0]-pos[0]) + abs(p[1]-pos[1])
            )
            next_step = self._bfs_next_step(nearest)
            if next_step and self.can_move_to(next_step):
                return {"action": "move", "target_pos": next_step}

        # ---- 5. Explore: pop from frontier ----
        while frontier:
            target = frontier[0]
            if target in explored:
                frontier.popleft()
                continue
            next_step = self._bfs_next_step(target)
            if next_step and self.can_move_to(next_step):
                return {"action": "move", "target_pos": next_step}
            frontier.popleft()

        # ---- 6. Random walk within z1 as last resort ----
        neighbours = self.model.grid.get_neighborhood(
            pos, moore=False, include_center=False
        )
        valid = [p for p in neighbours if self.can_move_to(p)]
        if valid:
            return {"action": "move", "target_pos": self.random.choice(valid)}

        return None


# ---------------------------------------------------------------------------
# Yellow Robot
# ---------------------------------------------------------------------------

class YellowRobot(BaseRobot):
    """
    Operates in z1 and z2.
    - Collects yellow waste (needs 2).
    - Transforms 2 yellow → 1 red.
    - Deposits red waste anywhere in z2 for red robots to collect.
    """

    def __init__(self, model):
        super().__init__(model, RobotType.YELLOW)
        z2_end = model.zone_boundaries[1][1][1]
        self.knowledge["max_zone_x"] = z2_end

    def deliberate(self, knowledge, percepts):
        pos = knowledge["pos"]
        inventory = knowledge["inventory"]
        known_waste = knowledge["known_waste"]
        explored = knowledge["explored_map"]
        frontier = knowledge["frontier"]

        # ---- 1. Transform if we have 2 yellow ----
        if inventory.count(WasteType.YELLOW) >= 2:
            return {
                "action": "transform",
                "from_type": WasteType.YELLOW,
                "to_type": WasteType.RED,
            }

        # ---- 2. Deposit red waste anywhere in z2 ----
        if inventory.count(WasteType.RED) >= 1:
            z2_start = self.model.zone_boundaries[1][1][0]
            if pos[0] >= z2_start:
                # Already in z2 — deposit here
                return {"action": "put_down"}
            else:
                # Move east to enter z2 first
                next_pos = (pos[0] + 1, pos[1])
                if self.can_move_to(next_pos):
                    return {"action": "move", "target_pos": next_pos}

        # ---- 3. Pick up yellow waste in current cell ----
        for waste in percepts.get("waste_here", []):
            if waste.waste_type == WasteType.YELLOW:
                return {"action": "pick_up", "target": waste}

        # ---- 4. Navigate to nearest known yellow waste ----
        yellow_targets = [
            p for p, wt in known_waste.items() if wt == WasteType.YELLOW
        ]
        if yellow_targets:
            nearest = min(
                yellow_targets,
                key=lambda p: abs(p[0]-pos[0]) + abs(p[1]-pos[1])
            )
            next_step = self._bfs_next_step(nearest)
            if next_step and self.can_move_to(next_step):
                return {"action": "move", "target_pos": next_step}

        # ---- 5. Explore: pop from frontier ----
        while frontier:
            target = frontier[0]
            if target in explored:
                frontier.popleft()
                continue
            next_step = self._bfs_next_step(target)
            if next_step and self.can_move_to(next_step):
                return {"action": "move", "target_pos": next_step}
            frontier.popleft()

        # ---- 6. Random walk as last resort ----
        neighbours = self.model.grid.get_neighborhood(
            pos, moore=False, include_center=False
        )
        valid = [p for p in neighbours if self.can_move_to(p)]
        if valid:
            return {"action": "move", "target_pos": self.random.choice(valid)}

        return None


# ---------------------------------------------------------------------------
# Red Robot
# ---------------------------------------------------------------------------

class RedRobot(BaseRobot):
    """
    Operates in z1, z2, and z3.
    - Collects red waste.
    - Transports it to the WasteDisposalZone (easternmost column, x = width-1).
    - Calls 'dispose' when standing on the disposal zone.
    """

    def __init__(self, model):
        super().__init__(model, RobotType.RED)
        self.knowledge["max_zone_x"] = model.width - 1  # full access

    def deliberate(self, knowledge, percepts):
        pos = knowledge["pos"]
        inventory = knowledge["inventory"]
        known_waste = knowledge["known_waste"]
        explored = knowledge["explored_map"]
        frontier = knowledge["frontier"]

        # ---- 1. Dispose if carrying red waste and at disposal zone ----
        if inventory.count(WasteType.RED) >= 1:
            if percepts.get("at_disposal_zone"):
                return {"action": "dispose"}
            # Move east toward the disposal zone (x = width-1)
            disposal_x = self.model.width - 1
            if pos[0] < disposal_x:
                next_pos = self._bfs_next_step((disposal_x, pos[1]))
                if next_pos:
                    return {"action": "move", "target_pos": next_pos}

        # ---- 2. Pick up red waste in current cell ----
        for waste in percepts.get("waste_here", []):
            if waste.waste_type == WasteType.RED:
                return {"action": "pick_up", "target": waste}

        # ---- 3. Navigate to nearest known red waste ----
        red_targets = [
            p for p, wt in known_waste.items() if wt == WasteType.RED
        ]
        if red_targets:
            nearest = min(
                red_targets,
                key=lambda p: abs(p[0]-pos[0]) + abs(p[1]-pos[1])
            )
            next_step = self._bfs_next_step(nearest)
            if next_step:
                return {"action": "move", "target_pos": next_step}

        # ---- 4. Explore: pop from frontier ----
        while frontier:
            target = frontier[0]
            if target in explored:
                frontier.popleft()
                continue
            next_step = self._bfs_next_step(target)
            if next_step:
                return {"action": "move", "target_pos": next_step}
            frontier.popleft()

        # ---- 5. Random walk as last resort ----
        neighbours = self.model.grid.get_neighborhood(
            pos, moore=False, include_center=False
        )
        if neighbours:
            return {"action": "move", "target_pos": self.random.choice(list(neighbours))}

        return None