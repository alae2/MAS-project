"""
Group: 7
Members: 
Date: 
Description: Robot Agent classes for Waste Collection MAS
"""

import mesa
from enum import Enum
from collections import deque

from objects import WasteType


class RobotType(Enum):
    """Enumerate robot types"""
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class BaseRobot(mesa.Agent):
    """Base class for all robot types"""

    def __init__(self, model, robot_type):
        """
        Initialize a robot agent.
        
        Args:
            model: Model instance
            robot_type: RobotType enum
        """
        super().__init__(model)
        self.robot_type = robot_type
        self.inventory = []  # List of waste objects
        
        # Knowledge base: agent's internal beliefs and observations
        self.knowledge = {
            "pos": None,
            "inventory": [],  # Agent's belief about what it carries
            "exploration_mode": getattr(model, "exploration_mode", "sweep"),
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

    def step_agent(self):
        """
        Execute one step of the agent control loop:
        1. Update knowledge with percepts from environment
        2. Deliberate to choose action
        3. Execute action via model.do()
        """
        # Step 1: Percepts - get information from environment
        percepts = self.model.perceive(self)
        
        # Step 2: Update knowledge with percepts
        self.knowledge["pos"] = self.pos
        self.knowledge["observations"] = percepts
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
        Reasoning process. Only receives knowledge, returns action.
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
        mode = self.knowledge.get("exploration_mode", "sweep")
        if mode == "random":
            return self._plan_random_step(pos)
        if mode == "bfs":
            return self._plan_bfs_frontier_step(
                pos, min_x=0, max_x=self.knowledge["grid_width"] - 1
            )

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
        mode = self.knowledge.get("exploration_mode", "sweep")
        if mode == "random":
            return self._plan_random_step_in_range(pos, min_x, max_x)
        if mode == "bfs":
            return self._plan_bfs_frontier_step(pos, min_x=min_x, max_x=max_x)

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

    def _plan_random_step(self, pos):
        """Pick one valid neighboring move uniformly at random."""
        width = self.knowledge["grid_width"]
        height = self.knowledge["grid_height"]

        candidates = [
            (pos[0] + dx, pos[1] + dy)
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]
        ]
        valid = [
            c for c in candidates
            if 0 <= c[0] < width and 0 <= c[1] < height and self.can_move_to(c)
        ]
        if not valid:
            return None
        return self.random.choice(valid)

    def _plan_random_step_in_range(self, pos, min_x, max_x):
        """Pick one valid neighboring move uniformly at random within an x-range."""
        width = self.knowledge["grid_width"]
        height = self.knowledge["grid_height"]

        candidates = [
            (pos[0] + dx, pos[1] + dy)
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]
        ]
        valid = [
            c for c in candidates
            if 0 <= c[0] < width and 0 <= c[1] < height
            and min_x <= c[0] <= max_x and self.can_move_to(c)
        ]
        if not valid:
            return None
        return self.random.choice(valid)

    def _plan_bfs_frontier_step(self, pos, min_x, max_x):
        """
        Frontier-based BFS exploration.

        Computes the set of frontier cells, unvisited cells reachable
        from any visited cell, then runs BFS from `pos` to find the
        nearest one. Returns the first step along that path, or None
        when every reachable cell has already been visited.
        """
        visited = self.knowledge["visited"]
        width   = self.knowledge["grid_width"]
        height  = self.knowledge["grid_height"]

        # 1. Build the frontier set
        # A frontier cell is: unvisited, within x-range, and adjacent to
        # at least one visited cell (so it is "known to exist").
        frontier = set()
        for vx, vy in visited:
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = vx + dx, vy + dy
                candidate = (nx, ny)
                if (
                    0 <= nx < width
                    and 0 <= ny < height
                    and min_x <= nx <= max_x
                    and candidate not in visited
                ):
                    frontier.add(candidate)

        if not frontier:
            return None  # Entire accessible area has been visited

        # 2. BFS from current position to nearest frontier cell
        queue    = deque()
        queue.append((pos, [pos]))   # (current_node, path_so_far)
        seen     = {pos}

        while queue:
            current, path = queue.popleft()

            if current in frontier:
                # path[0] is pos itself; path[1] is the first move
                if len(path) >= 2:
                    return path[1]
                return current   # already adjacent, move directly

            cx, cy = current
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nxt = (cx + dx, cy + dy)
                if (
                    nxt not in seen
                    and 0 <= nxt[0] < width
                    and 0 <= nxt[1] < height
                    and min_x <= nxt[0] <= max_x
                    and self.can_move_to(nxt)
                ):
                    seen.add(nxt)
                    queue.append((nxt, path + [nxt]))

        # 3. No path found, fall back to a random valid neighbor
        neighbors = [
            (pos[0] + dx, pos[1] + dy)
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]
        ]
        valid = [
            n for n in neighbors
            if 0 <= n[0] < width
            and 0 <= n[1] < height
            and min_x <= n[0] <= max_x
            and self.can_move_to(n)
        ]
        return self.random.choice(valid) if valid else None

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
    """

    def __init__(self, model):
        super().__init__(model, RobotType.GREEN)

    def deliberate(self, knowledge):
        """Green robot decision logic with intelligent pathfinding"""
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


class YellowRobot(BaseRobot):
    """
    Yellow Robot : operates in z1 + z2.

    Knowledge provided at init:
            grid_width, grid_height  - for navigation

        Task: collect 2 yellow wastes -> transform to 1 red -> deposit at z2/z3 frontier.
    """

    def __init__(self, model):
        super().__init__(model, RobotType.YELLOW)

    def deliberate(self, knowledge):
        """Yellow robot decision logic with intelligent pathfinding"""
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


class RedRobot(BaseRobot):
    """
    Red Robot : operates in z1 + z2 + z3.

    Knowledge provided at init:
      grid_width, grid_height  - for navigation
      disposal_x               - x-column of the disposal zone (easternmost column)

    Task: collect 1 red waste -> transport east -> dispose at disposal_x.
    """

    def __init__(self, model):
        super().__init__(model, RobotType.RED)
        self.knowledge["disposal_x"] = model.disposal_zone_x

    def deliberate(self, knowledge):
        """Red robot decision logic with intelligent pathfinding"""
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
