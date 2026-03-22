"""
Group: 7
Members: 
Date: 
Description: Robot Agent classes for Waste Collection MAS
"""

import mesa
from enum import Enum

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
            "max_zone": None,    # Maximum x-coordinate this robot can reach 
            "observations": {},  # Observations from last percepts
            "mode": "explore",   # Current target (waste or zone)
            "sweep_dir": "east", # Exploration sweep direction
            "visited": set(),    # Cells visited by this robot
            "move_history": [],  # Recent moves (pos tuples)
            "frontier_check_interval": 8,  # Steps between frontier checks
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
        """Check if robot can move to position based on zone restrictions."""
        x, _ = position
        return x <= self.knowledge["max_zone"]

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
        for entry in self.knowledge["observations"].get("neighbors", []):
            if entry.get("type") == "waste" and entry.get("waste_type") == waste_type:
                cell = entry["pos"]
                if self.can_move_to(cell):
                    return cell
        return None

    def _frontier_scan(self, pos, frontier_x):
        """
        Handle periodic frontier exploration.
        Robot moves to frontier then scans entire y-axis.
        """
        knowledge = self.knowledge
        height = knowledge["grid_height"]

        # Activate frontier mode
        if knowledge["steps_since_frontier"] >= knowledge["frontier_check_interval"]:
            knowledge["frontier_mode"] = True

        if not knowledge["frontier_mode"]:
            return None

        # Move toward frontier first
        if pos[0] != frontier_x:
            step = 1 if pos[0] < frontier_x else -1
            return {"action": "move", "target_pos": (pos[0] + step, pos[1])}

        # Scan vertically along frontier
        direction = knowledge["frontier_dir"]

        if direction == "down":
            if pos[1] < height - 1:
                return {"action": "move", "target_pos": (pos[0], pos[1] + 1)}
            else:
                knowledge["frontier_dir"] = "up"

        else:
            if pos[1] > 0:
                return {"action": "move", "target_pos": (pos[0], pos[1] - 1)}
            else:
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
      deposit_frontier         : x-column of the z1/z2 boundary, where
                                 transformed yellow waste must be deposited

    Task: collect 2 green wastes -> transform to 1 yellow -> deposit at deposit_frontier.
    """

    def __init__(self, model):
        super().__init__(model, RobotType.GREEN)
        z1_end = model.zone_boundaries[0][1][1]
        self.knowledge["max_zone"] = z1_end
        self.knowledge["deposit_frontier"] = z1_end

    def deliberate(self, knowledge):
        """Green robot decision logic with intelligent pathfinding"""
        pos = knowledge["pos"]
        inventory = knowledge["inventory"]
        observations = knowledge["observations"]
        deposit_frontier = knowledge["deposit_frontier"]

        # If we have 2 green wastes, transform to yellow
        if inventory.count(WasteType.GREEN) >= 2:
            return {"action": "transform", "from_type": WasteType.GREEN, "to_type": WasteType.YELLOW}
        
        # If we have 1 yellow waste, move toward z1/z2 frontier to deposit (move to the east)
        if inventory.count(WasteType.YELLOW) >= 1:
            if pos[0] < deposit_frontier:
                return {"action": "move", "target_pos": (pos[0] + 1, pos[1])}
            return {"action": "put_down"}

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
      pickup_frontier          - x-column of the z1/z2 boundary, where green
                                 robots deposit yellow waste (scanned periodically)
      deposit_frontier         - x-column of the z2/z3 boundary, where
                                 transformed red waste must be deposited

    Task: collect 2 yellow wastes -> transform to 1 red -> deposit at deposit_frontier.
    """

    def __init__(self, model):
        super().__init__(model, RobotType.YELLOW)
        z1_end = model.zone_boundaries[0][1][1]
        z2_end = model.zone_boundaries[1][1][1]
        self.knowledge["max_zone"] = z2_end
        self.knowledge["pickup_frontier"] = z1_end
        self.knowledge["deposit_frontier"] = z2_end

    def deliberate(self, knowledge):
        """Yellow robot decision logic with intelligent pathfinding"""
        pos = knowledge["pos"]
        inventory = knowledge["inventory"]
        observations = knowledge["observations"]
        pickup_frontier = knowledge["pickup_frontier"]
        deposit_frontier = knowledge["deposit_frontier"]

        # If we have 2 yellow wastes, transform to red
        if inventory.count(WasteType.YELLOW) >= 2:
            return {"action": "transform", "from_type": WasteType.YELLOW, "to_type": WasteType.RED}
        
        # If we have 1 red waste, move toward z3 frontier
        if inventory.count(WasteType.RED) >= 1:
            if pos[0] < deposit_frontier:
                return {"action": "move", "target_pos": (pos[0] + 1, pos[1])}
            return {"action": "put_down"}

        # Look for yellow waste in current cell
        for waste in observations.get("waste_here", []):
            if waste.waste_type == WasteType.YELLOW:
                return {"action": "pick_up", "target": waste}
        # Look for nearby yellow waste
        target_cell = self._find_nearest_waste(WasteType.YELLOW)
        if target_cell:
            return {"action": "move", "target_pos": target_cell}

        # Periodically check the z1/z2 frontier for new yellow waste
        frontier_action = self._frontier_scan(pos, pickup_frontier)
        if frontier_action:
            return frontier_action

        # Return to zone 2 for exploration if too far west
        if pos[0] <= pickup_frontier:
            return {"action": "move", "target_pos": (pos[0] + 1, pos[1])}
        
        # Default: systematic sweep within zone 2
        new_pos = self._plan_exploration_step_in_range(pos, pickup_frontier + 1, deposit_frontier)
        if new_pos:
            return {"action": "move", "target_pos": new_pos}
        
        return None


class RedRobot(BaseRobot):
    """
    Red Robot : operates in z1 + z2 + z3.

    Knowledge provided at init:
      grid_width, grid_height  - for navigation
      pickup_frontier          - x-column of the z2/z3 boundary, where yellow
                                 robots deposit red waste (scanned periodically)
      disposal_x               - x-column of the disposal zone (easternmost column)

    Task: collect 1 red waste -> transport east -> dispose at disposal_x.
    """

    def __init__(self, model):
        super().__init__(model, RobotType.RED)
        z2_end = model.zone_boundaries[1][1][1]
        self.knowledge["max_zone"] = model.width - 1
        self.knowledge["pickup_frontier"] = z2_end
        self.knowledge["disposal_x"] = model.disposal_zone_x

    def deliberate(self, knowledge):
        """Red robot decision logic with intelligent pathfinding"""
        pos = knowledge["pos"]
        inventory = knowledge["inventory"]
        observations = knowledge["observations"]
        pickup_frontier = knowledge["pickup_frontier"]
        disposal_x = knowledge["disposal_x"]
        grid_width = knowledge["grid_width"]

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
        frontier_action = self._frontier_scan(pos, pickup_frontier)
        if frontier_action:
            return frontier_action

        # Return to zone 3 for exploration if too far west
        zone3_min_x = pickup_frontier + 1
        if pos[0] < zone3_min_x:
            return {"action": "move", "target_pos": (pos[0] + 1, pos[1])}
        
        # Default: systematic sweep within zone 3
        new_pos = self._plan_exploration_step_in_range(pos, zone3_min_x, disposal_x - 1)
        if new_pos:
            return {"action": "move", "target_pos": new_pos}
        
        return None
