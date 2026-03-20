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
            "max_zone": None,  # Maximum zone this robot can reach
            "observations": {},  # Observations from last percepts
            "target": None,  # Current target (waste or zone)
            "mode": "explore",  # Current behavioral mode
            "sweep_dir": "east",  # Exploration sweep direction
            "visited": set(),  # Cells visited by this robot
            "move_history": [],  # Recent moves (pos tuples)
            "frontier_check_interval": 8,  # Steps between frontier checks
            "steps_since_frontier": 0,  # Counter for frontier checks
            "frontier_mode": False,
            "frontier_dir": "down"
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
        
        # Step 3: Deliberate - decide on action
        action = self.deliberate(self.knowledge)
        
        # Step 4: Execute action via model
        if action:
            self.model.do(self, action)

    def deliberate(self, knowledge):
        """
        Reasoning process. Only receives knowledge, returns action.
        Must be overridden by subclasses.
        
        Args:
            knowledge: Agent's knowledge base
            
        Returns:
            action: Dictionary with action type and parameters
        """
        raise NotImplementedError

    def can_move_to(self, position):
        """Check if robot can move to position based on zone restrictions"""
        x, y = position
        max_zone_x = self.knowledge["max_zone"]
        return x <= max_zone_x

    def _plan_exploration_step(self, pos):
        """Plan a systematic sweep within the accessible zone."""
        width = self.model.grid.width
        height = self.model.grid.height
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
        """Plan a sweep constrained to an x-range."""
        width = self.model.grid.width
        height = self.model.grid.height
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

        neighbors = self.model.grid.get_neighborhood(
            pos, moore=False, include_center=False
        )
        valid_neighbors = [
            step for step in neighbors
            if self.can_move_to(step)
            and 0 <= step[0] < self.model.grid.width
            and 0 <= step[1] < self.model.grid.height
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

    def _find_nearest_waste(self, pos, waste_type):
        """
        Look in neighboring cells for the nearest waste of a specific type.
        Returns the position of the target cell or None.
        """
        neighbors = self.model.grid.get_neighborhood(
            pos, moore=False, include_center=False
        )

        for cell in neighbors:
            cell_contents = self.model.grid.get_cell_list_contents(cell)
            for obj in cell_contents:
                if hasattr(obj, "waste_type") and obj.waste_type == waste_type:
                    if self.can_move_to(cell):
                        return cell

        return None

    def _frontier_scan(self, pos, frontier_x):
        """
        Handle periodic frontier exploration.
        Robot moves to frontier then scans entire y-axis.
        """
        knowledge = self.knowledge
        height = self.model.grid.height

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
    Green Robot:
    - Picks up 2 green wastes
    - Transforms 2 green into 1 yellow
    - Transports yellow waste to z2 (z1 only, cannot exceed)
    """

    def __init__(self, model):
        super().__init__(model, RobotType.GREEN)
        # max_zone is the maximum x coordinate allowed for this robot
        self.knowledge["max_zone"] = model.zone_boundaries[0][1][1]  # Max x of z1

    def deliberate(self, knowledge):
        """Green robot decision logic with intelligent pathfinding"""
        pos = knowledge["pos"]
        inventory = knowledge["inventory"]
        observations = knowledge["observations"]
        
        # If we have 2 green wastes, transform to yellow
        if inventory.count(WasteType.GREEN) >= 2:
            return {"action": "transform", "from_type": WasteType.GREEN, "to_type": WasteType.YELLOW}
        
        # If we have 1 yellow waste, move toward z1/z2 frontier to deposit (move to the east)
        if inventory.count(WasteType.YELLOW) >= 1:
            target_frontier = observations.get("target_frontier")
            if target_frontier and pos[0] < target_frontier:
                new_x = pos[0] + 1
                new_pos = (new_x, pos[1])
                return {"action": "move", "target_pos": new_pos}
            else:
                # At frontier, deposit the yellow waste
                return {"action": "put_down"}
        
        # Look for green waste in current cell
        if "waste_here" in observations and observations["waste_here"]:
            for waste in observations["waste_here"]:
                if waste.waste_type == WasteType.GREEN:
                    return {"action": "pick_up", "target": waste}
        
        # Look for nearby green waste
        target_cell = self._find_nearest_waste(pos, WasteType.GREEN)
        if target_cell:
            return {"action": "move", "target_pos": target_cell}
                
        # Default: systematic sweep within accessible zones
        new_pos = self._plan_exploration_step(pos)
        if new_pos:
            return {"action": "move", "target_pos": new_pos}
        
        return None


class YellowRobot(BaseRobot):
    """
    Yellow Robot:
    - Picks up 2 yellow wastes
    - Transforms 2 yellow into 1 red
    - Transports red waste to z3 (z1 and z2 access, cannot exceed)
    """

    def __init__(self, model):
        super().__init__(model, RobotType.YELLOW)
        # max_zone is the maximum x coordinate allowed for this robot
        self.knowledge["max_zone"] = model.zone_boundaries[1][1][1]  # Max x of z2

    def deliberate(self, knowledge):
        """Yellow robot decision logic with intelligent pathfinding"""
        pos = knowledge["pos"]
        inventory = knowledge["inventory"]
        observations = knowledge["observations"]
        z1_end = self.model.width // 3
        z2_end = (2 * self.model.width) // 3
        
        # If we have 2 yellow wastes, transform to red
        if inventory.count(WasteType.YELLOW) >= 2:
            return {"action": "transform", "from_type": WasteType.YELLOW, "to_type": WasteType.RED}
        
        # If we have 1 red waste, move toward z3 frontier
        if inventory.count(WasteType.RED) >= 1:
            target_frontier = observations.get("target_frontier")
            if target_frontier and pos[0] < target_frontier:
                new_x = pos[0] + 1
                new_pos = (new_x, pos[1])
                return {"action": "move", "target_pos": new_pos}
            else:
                # At frontier, try to deposit
                return {"action": "put_down"}
        
        # Look for yellow waste in current cell
        if "waste_here" in observations and observations["waste_here"]:
            for waste in observations["waste_here"]:
                if waste.waste_type == WasteType.YELLOW:
                    return {"action": "pick_up", "target": waste}
        
        # Look for nearby yellow waste
        target_cell = self._find_nearest_waste(pos, WasteType.YELLOW)
        if target_cell:
            return {"action": "move", "target_pos": target_cell}

        # Periodically check the z1/z2 frontier for new yellow waste
        frontier_action = self._frontier_scan(pos, z1_end)
        if frontier_action:
            return frontier_action

        # Return to zone 2 for exploration if too far west
        if pos[0] <= z1_end:
            return {"action": "move", "target_pos": (pos[0] + 1, pos[1])}
        
        # Default: systematic sweep within zone 2
        new_pos = self._plan_exploration_step_in_range(pos, z1_end + 1, z2_end)
        if new_pos:
            return {"action": "move", "target_pos": new_pos}
        
        return None


class RedRobot(BaseRobot):
    """
    Red Robot:
    - Picks up 1 red waste
    - Transports to z3 and disposes (all zones access)
    """

    def __init__(self, model):
        super().__init__(model, RobotType.RED)
        # max_zone is the maximum x coordinate allowed for this robot
        self.knowledge["max_zone"] = model.zone_boundaries[2][1][1]  # Max x of z3

    def deliberate(self, knowledge):
        """Red robot decision logic with intelligent pathfinding"""
        pos = knowledge["pos"]
        inventory = knowledge["inventory"]
        observations = knowledge["observations"]
        z2_end = (2 * self.model.width) // 3
        zone3_min_x = z2_end + 1
        
        # If we have 1 red waste, move toward disposal zone and dispose
        if inventory.count(WasteType.RED) >= 1:
            disposal_zone_x = observations.get("disposal_zone_x")
            if disposal_zone_x is not None:
                if pos[0] == disposal_zone_x:
                    return {"action": "dispose"}
                new_pos = (pos[0] + 1, pos[1])
                if 0 <= new_pos[0] < self.model.grid.width:
                    return {"action": "move", "target_pos": new_pos}
        
        # Look for red waste in current cell
        if "waste_here" in observations and observations["waste_here"]:
            for waste in observations["waste_here"]:
                if waste.waste_type == WasteType.RED:
                    return {"action": "pick_up", "target": waste}
                
        # Look for nearby red waste        
        target_cell = self._find_nearest_waste(pos, WasteType.RED)
        if target_cell:
            return {"action": "move", "target_pos": target_cell}

        # Periodically check the z2/z3 frontier for new red waste
        frontier_action = self._frontier_scan(pos, z2_end)
        if frontier_action:
            return frontier_action

        # Return to zone 3 for exploration if too far west
        if pos[0] < zone3_min_x:
            return {"action": "move", "target_pos": (pos[0] + 1, pos[1])}
        
        # Default: systematic sweep within zone 3
        new_pos = self._plan_exploration_step_in_range(pos, zone3_min_x, self.model.width - 1)
        if new_pos:
            return {"action": "move", "target_pos": new_pos}
        
        return None
