"""
Group: 7
Members: 
Date: 
Description: Robot Agent classes for Waste Collection MAS
"""

import mesa
from enum import Enum


class WasteType(Enum):
    """Enumerate waste types"""
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


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
            "mode": "explore"  # Current behavioral mode
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
            if target_frontier and pos[0] < target_frontier[0]:
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
        
        # Use environment guidance: move toward closest green waste
        closest_waste = observations.get("closest_target_waste")
        if closest_waste:
            target_pos = closest_waste["pos"]
            if target_pos[0] < pos[0]:
                new_pos = (pos[0] - 1, pos[1])
            elif target_pos[0] > pos[0]:
                new_pos = (pos[0] + 1, pos[1])
            elif target_pos[1] < pos[1]:
                new_pos = (pos[0], pos[1] - 1)
            elif target_pos[1] > pos[1]:
                new_pos = (pos[0], pos[1] + 1)
            else:
                new_pos = pos
            
            # Check if move is valid
            if self.can_move_to(new_pos) and (0 <= new_pos[0] < self.model.grid.width and 0 <= new_pos[1] < self.model.grid.height):
                return {"action": "move", "target_pos": new_pos}
    
        # Default: random exploration within accessible zones
        possible_steps = self.model.grid.get_neighborhood(
            pos, moore=False, include_center=False
        )
        valid_steps = [step for step in possible_steps 
                      if self.can_move_to(step)]
        
        if valid_steps:
            new_pos = self.random.choice(valid_steps)
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
        
        # If we have 2 yellow wastes, transform to red
        if inventory.count(WasteType.YELLOW) >= 2:
            return {"action": "transform", "from_type": WasteType.YELLOW, "to_type": WasteType.RED}
        
        # If we have 1 red waste, move toward z3 frontier
        if inventory.count(WasteType.RED) >= 1:
            target_frontier = observations.get("target_frontier")
            if target_frontier and pos[0] < target_frontier[0]:
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
        
        # Use environment guidance: move toward closest yellow waste
        closest_waste = observations.get("closest_target_waste")
        if closest_waste:
            target_pos = closest_waste["pos"]
            if target_pos[0] < pos[0]:
                new_pos = (pos[0] - 1, pos[1])
            elif target_pos[0] > pos[0]:
                new_pos = (pos[0] + 1, pos[1])
            elif target_pos[1] < pos[1]:
                new_pos = (pos[0], pos[1] - 1)
            elif target_pos[1] > pos[1]:
                new_pos = (pos[0], pos[1] + 1)
            else:
                new_pos = pos
            
            # Check if move is valid
            if self.can_move_to(new_pos) and (0 <= new_pos[0] < self.model.grid.width and 0 <= new_pos[1] < self.model.grid.height):
                return {"action": "move", "target_pos": new_pos}
        
        # Default: random exploration within accessible zones
        possible_steps = self.model.grid.get_neighborhood(
            pos, moore=False, include_center=False
        )
        valid_steps = [step for step in possible_steps 
                      if self.can_move_to(step)]
        
        if valid_steps:
            new_pos = self.random.choice(valid_steps)
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
        
        # If we have 1 red waste, move toward z3 and dispose
        if inventory.count(WasteType.RED) >= 1:
            target_frontier = observations.get("target_frontier")
            if target_frontier and pos[0] < target_frontier[0]:
                # Move toward disposal zone in z3
                new_pos = (pos[0] + 1, pos[1])
                return {"action": "move", "target_pos": new_pos}
            else:
                # In z3, dispose the waste
                return {"action": "dispose"}
        
        # Look for red waste in current cell
        if "waste_here" in observations and observations["waste_here"]:
            for waste in observations["waste_here"]:
                if waste.waste_type == WasteType.RED:
                    return {"action": "pick_up", "target": waste}
        
        # Use environment guidance: move toward closest red waste
        closest_waste = observations.get("closest_target_waste")
        if closest_waste:
            target_pos = closest_waste["pos"]
            if target_pos[0] < pos[0]:
                new_pos = (pos[0] - 1, pos[1])
            elif target_pos[0] > pos[0]:
                new_pos = (pos[0] + 1, pos[1])
            elif target_pos[1] < pos[1]:
                new_pos = (pos[0], pos[1] - 1)
            elif target_pos[1] > pos[1]:
                new_pos = (pos[0], pos[1] + 1)
            else:
                new_pos = pos
            
            # Check if move is valid
            if 0 <= new_pos[0] < self.model.grid.width and 0 <= new_pos[1] < self.model.grid.height:
                return {"action": "move", "target_pos": new_pos}
        
        # Default: random exploration
        possible_steps = self.model.grid.get_neighborhood(
            pos, moore=False, include_center=False
        )
        
        if possible_steps:
            new_pos = self.random.choice(possible_steps)
            return {"action": "move", "target_pos": new_pos}
        
        return None
