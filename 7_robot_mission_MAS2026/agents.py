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


from objects import WasteType


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
            "inventory": [],  # Agent's belief about what it carries
            "observations": {},  # Observations from last percepts
            "mode": "explore",   # Current target (waste or zone)
            "sweep_dir": "east", # Exploration sweep direction
            "visited": set(),    # Cells visited by this robot
            "move_history": [],  # Recent moves (pos tuples)
            "frontier_check_interval": model.width+model.height,  # Steps between frontier checks
            "steps_since_frontier": 0,     # Counter for frontier checks
            "frontier_mode": False,
            "frontier_dir": "down",
            "last_action_failed": False,
            "grid_width": model.width,
            "grid_height": model.height,

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

        self.knowledge["visited"].add(self.pos)
        self._remember_move(self.pos)
        self.knowledge["steps_since_frontier"] += 1
        self.knowledge["last_action_failed"] = percepts.get("action_failed", False)

        # Step 3: Deliberate - decide on action
        action = self.deliberate(self.knowledge)

        if action:
            self.model.do(self, action)

    def deliberate(self):
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

        This method must only read from the "knowledge" argument.
        """
        raise NotImplementedError

    def can_move_to(self, position):
        """Check if robot can move to an adjacent position using local radioactivity percepts."""
        observations = self.knowledge.get("observations", {})

        target_zone = None
        for cell in observations.get("neighbor_radioactivity", []):
            if cell.get("pos") == position:
                target_zone = cell.get("zone")
                break

        if target_zone is None:
            return False

        if self.robot_type == RobotType.GREEN:
            return target_zone == "z1"
        if self.robot_type == RobotType.YELLOW:
            return target_zone in ("z1", "z2")
        return target_zone in ("z1", "z2", "z3")

    def _plan_exploration_step(self, pos):
        """Plan a systematic sweep within the accessible zone."""
        width = self.knowledge["grid_width"]
        height = self.knowledge["grid_height"]
        direction = self.knowledge.get("sweep_dir", "east")

        if direction == "east":
            candidate = (pos[0] + 1, pos[1])
            if candidate[0] < width and self.can_move_to(candidate):
                return self._prefer_unvisited(pos, candidate)

            # At eastern boundary, move south if possible, then reverse
            if pos[1] < height - 1:
                self.knowledge["sweep_dir"] = "west"
                return self._prefer_unvisited(pos, (pos[0], pos[1] + 1))

            # At bottom row, move north and reverse
            self.knowledge["sweep_dir"] = "west"
            return self._prefer_unvisited(pos, (pos[0], max(0, pos[1] - 1)))

        candidate = (pos[0] - 1, pos[1])
        if candidate[0] >= 0 and self.can_move_to(candidate):
            return self._prefer_unvisited(pos, candidate)

        # At western boundary, move south if possible, then reverse
        if pos[1] < height - 1:
            self.knowledge["sweep_dir"] = "east"
            return self._prefer_unvisited(pos, (pos[0], pos[1] + 1))

        # At bottom row, move north and reverse
        self.knowledge["sweep_dir"] = "east"
        return self._prefer_unvisited(pos, (pos[0], max(0, pos[1] - 1)))

    def _plan_exploration_step_in_range(self, pos, min_x, max_x):
        """Plan a sweep constrained to a given x-range."""
        width = self.knowledge["grid_width"]
        height = self.knowledge["grid_height"]
        direction = self.knowledge.get("sweep_dir", "east")

        if direction == "east":
            candidate = (pos[0] + 1, pos[1])
            if min_x <= candidate[0] <= max_x and candidate[0] < width:
                return self._prefer_unvisited(pos, candidate)

            if pos[1] < height - 1:
                self.knowledge["sweep_dir"] = "west"
                return self._prefer_unvisited(pos, (pos[0], pos[1] + 1))

            self.knowledge["sweep_dir"] = "west"
            return self._prefer_unvisited(pos, (pos[0], max(0, pos[1] - 1)))

        candidate = (pos[0] - 1, pos[1])
        if min_x <= candidate[0] <= max_x and candidate[0] >= 0:
            return self._prefer_unvisited(pos, candidate)

        if pos[1] < height - 1:
            self.knowledge["sweep_dir"] = "east"
            return self._prefer_unvisited(pos, (pos[0], pos[1] + 1))

        self.knowledge["sweep_dir"] = "east"
        return self._prefer_unvisited(pos, (pos[0], max(0, pos[1] - 1)))

    def _remember_move(self, pos):
        """Track recent positions to avoid short loops."""
        history = self.knowledge["move_history"]
        history.append(pos)
        if len(history) > 20:
            history.pop(0)

    def _prefer_unvisited(self, pos, candidate):
        """Bias exploration toward unvisited cells when available."""
        if candidate not in self.knowledge["visited"]:
            return candidate

        width = self.knowledge["grid_width"]
        height = self.knowledge["grid_height"]

        all_neighbors = [
            (pos[0] + dx, pos[1] + dy)
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]
        ]
        valid_neighbors = [
            s for s in all_neighbors
            if self.can_move_to(s) and 0 <= s[0] < width and 0 <= s[1] < height
        ]
        unvisited = [step for step in valid_neighbors if step not in self.knowledge["visited"]]
        if unvisited:
            return self.random.choice(unvisited)

        # Avoid immediate backtracking when possible
        if len(self.knowledge["move_history"]) >= 2:
            last_pos = self.knowledge["move_history"][-2]
            non_backtrack = [step for step in valid_neighbors if step != last_pos]
            if non_backtrack:
                return self.random.choice(non_backtrack)

        return candidate

    def _find_nearest_waste(self, waste_type):
        """
        Return the position of the nearest accessible neighboring cell
        containing waste of the given type, or None.
        """
        for entry in self.knowledge["observations"].get("neighbor_waste", []):
            if entry.get("type") == "waste" and entry.get("waste_type") == waste_type:
                cell = entry["pos"]
                if self.can_move_to(cell):
                    return cell
        return None

    def _get_neighbor_zone(self, pos, dx, dy):
        """Return zone name for a neighboring offset cell if present in percepts."""
        target = (pos[0] + dx, pos[1] + dy)
        for cell in self.knowledge["observations"].get("neighbor_radioactivity", []):
            if cell.get("pos") == target:
                return cell.get("zone")
        return None

    def _is_frontier_cell(self, pos, left_zone, right_zone, side="either"):
        """Infer whether current cell lies on a frontier using neighboring zone transitions."""
        current_zone = self.knowledge["observations"].get("zone")
        east_zone = self._get_neighbor_zone(pos, 1, 0)
        west_zone = self._get_neighbor_zone(pos, -1, 0)

        on_left_side = current_zone == left_zone and east_zone == right_zone
        on_right_side = current_zone == right_zone and west_zone == left_zone

        if side == "left":
            return on_left_side
        if side == "right":
            return on_right_side
        return on_left_side or on_right_side

    def _frontier_scan(self, pos, frontier_name):
        """
        Handle periodic frontier exploration inferred from perceived zones.
        frontier_name: "z1_z2" or "z2_z3".
        """
        knowledge = self.knowledge
        height = knowledge["grid_height"]
        current_zone = knowledge["observations"].get("zone")

        # Activate frontier mode
        if knowledge["steps_since_frontier"] >= knowledge["frontier_check_interval"]:
            knowledge["frontier_mode"] = True

        if not knowledge["frontier_mode"]:
            return None

        if frontier_name == "z1_z2":
            left_zone, right_zone = "z1", "z2"
        else:
            left_zone, right_zone = "z2", "z3"

        # Keep scan on the left-side frontier column only (handoff column).
        at_frontier = self._is_frontier_cell(pos, left_zone, right_zone, side="left")
        if not at_frontier:
            if current_zone == left_zone:
                return {"action": "move", "target_pos": (pos[0] + 1, pos[1])}
            return {"action": "move", "target_pos": (pos[0] - 1, pos[1])}

        # Scan vertically along frontier
        direction = knowledge["frontier_dir"]

        if direction == "down":
            if pos[1] < height - 1:
                return {"action": "move", "target_pos": (pos[0], pos[1] + 1)}
            knowledge["frontier_dir"] = "up"
        else:
            if pos[1] > 0:
                return {"action": "move", "target_pos": (pos[0], pos[1] - 1)}
            # Finished scanning frontier
            knowledge["frontier_mode"] = False
            knowledge["steps_since_frontier"] = 0
            knowledge["frontier_dir"] = "down"

        return None

class GreenRobot(BaseRobot):
    """
    Green Robot - operates in z1 only.

    Knowledge provided at init:
            grid_width, grid_height  : for navigation

        Task: collect 2 green wastes -> transform to 1 yellow -> deposit at z1/z2 frontier.
>>>>>>> c29a05001d6440b6e38685de0b52567d978ac6e2
    """

    def __init__(self, model):
        super().__init__(model, RobotType.GREEN)


    def deliberate(self, knowledge, percepts):
        pos = knowledge["pos"]
        inventory = knowledge["inventory"]

        observations = knowledge["observations"]

        # If we have 2 green wastes, transform to yellow
        if inventory.count(WasteType.GREEN) >= 2:
            return {"action": "transform", "from_type": WasteType.GREEN, "to_type": WasteType.YELLOW}
        
        # If we have 1 yellow waste, infer z1/z2 frontier from zone transition and deposit there
        if inventory.count(WasteType.YELLOW) >= 1:
            if self._is_frontier_cell(pos, "z1", "z2", side="left"):
                return {"action": "put_down"}
            if self.can_move_to((pos[0] + 1, pos[1])):
                return {"action": "move", "target_pos": (pos[0] + 1, pos[1])}
            return None

        # Pick up green waste in current cell
        for waste in observations.get("waste_here", []):
            if waste.waste_type == WasteType.GREEN:
                return {"action": "pick_up", "target": waste}

        # Move toward green waste in a neighboring cell
        target_cell = self._find_nearest_waste(WasteType.GREEN)
        if target_cell:
            return {"action": "move", "target_pos": target_cell}
                
        # Default: systematic sweep within accessible zones
        new_pos = self._plan_exploration_step(pos)
        if new_pos:
            return {"action": "move", "target_pos": new_pos}
        
        return None


# ---------------------------------------------------------------------------
# Yellow Robot
# ---------------------------------------------------------------------------

class YellowRobot(BaseRobot):
    """

    """

    def __init__(self, model):
        super().__init__(model, RobotType.YELLOW)


    def deliberate(self, knowledge, percepts):
        pos = knowledge["pos"]
        inventory = knowledge["inventory"]

        observations = knowledge["observations"]
        current_zone = observations.get("zone")

        # If we have 2 yellow wastes, transform to red
        if inventory.count(WasteType.YELLOW) >= 2:
            return {"action": "transform", "from_type": WasteType.YELLOW, "to_type": WasteType.RED}
        
        # If we have 1 red waste, infer z2/z3 frontier from zone transition and deposit there
        if inventory.count(WasteType.RED) >= 1:
            if self._is_frontier_cell(pos, "z2", "z3", side="left"):
                return {"action": "put_down"}
            if self.can_move_to((pos[0] + 1, pos[1])):
                return {"action": "move", "target_pos": (pos[0] + 1, pos[1])}
            return None

        # Look for yellow waste in current cell
        for waste in observations.get("waste_here", []):
            if waste.waste_type == WasteType.YELLOW:
                return {"action": "pick_up", "target": waste}
        # Look for nearby yellow waste
        target_cell = self._find_nearest_waste(WasteType.YELLOW)
        if target_cell:
            return {"action": "move", "target_pos": target_cell}

        # Periodically check the z1/z2 frontier for new yellow waste
        frontier_action = self._frontier_scan(pos, "z1_z2")
        if frontier_action:
            return frontier_action

        # Return to zone 2 for exploration if too far west
        if current_zone == "z1":
            return {"action": "move", "target_pos": (pos[0] + 1, pos[1])}
        
        # Default: systematic sweep within zone 2
        new_pos = self._plan_exploration_step(pos)
        if new_pos:
            return {"action": "move", "target_pos": new_pos}
        return None


# ---------------------------------------------------------------------------
# Red Robot
# ---------------------------------------------------------------------------

class RedRobot(BaseRobot):


    def __init__(self, model):
        super().__init__(model, RobotType.RED)


    def deliberate(self, knowledge, percepts):
        pos = knowledge["pos"]
        inventory = knowledge["inventory"]

        observations = knowledge["observations"]
        disposal_x = knowledge["disposal_x"]
        grid_width = knowledge["grid_width"]
        current_zone = observations.get("zone")

        # If we have 1 red waste, move toward disposal zone and dispose
        if inventory.count(WasteType.RED) >= 1:
            if pos[0] == disposal_x:
                return {"action": "dispose"}
            if pos[0] + 1 < grid_width:
                return {"action": "move", "target_pos": (pos[0] + 1, pos[1])}

        # Look for red waste in current cell
        for waste in observations.get("waste_here", []):
            if waste.waste_type == WasteType.RED:
                return {"action": "pick_up", "target": waste}

        # Look for nearby red waste        
        target_cell = self._find_nearest_waste(WasteType.RED)
        if target_cell:
            return {"action": "move", "target_pos": target_cell}

        # Periodically check the z2/z3 frontier for new red waste
        frontier_action = self._frontier_scan(pos, "z2_z3")
        if frontier_action:
            return frontier_action

        # Return to zone 3 for exploration if too far west
        if current_zone in ("z1", "z2"):
            return {"action": "move", "target_pos": (pos[0] + 1, pos[1])}
        
        # Default: systematic sweep within zone 3
        new_pos = self._plan_exploration_step_in_range(pos, 0, disposal_x - 1)
        if new_pos:
            return {"action": "move", "target_pos": new_pos}
        
        return None

