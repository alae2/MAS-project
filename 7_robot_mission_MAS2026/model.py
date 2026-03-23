"""
Group: 7
Members: 
Date: 
Description: RobotMission Model for Multi-Agent Waste Collection System
"""

import mesa

from agents import GreenRobot, YellowRobot, RedRobot
from objects import Waste, WasteType, RadioactivityCell, WasteDisposalZone


class RobotMissionModel(mesa.Model):
    """
    Model for the robot waste collection mission.
    Defines the environment, robots, waste, and actions.
    """

    def __init__(
        self,
        width=40,
        height=20,
        n_green_robots=5,
        n_yellow_robots=3,
        n_red_robots=2,
        n_initial_green_waste=30,
        n_initial_yellow_waste=0,
        n_initial_red_waste=0,
        max_steps=150,
        seed=None
    ):
        """
        Initialize the RobotMissionModel.
        
        Args:
            width: Grid width
            height: Grid height
            n_green_robots: Number of green robots
            n_yellow_robots: Number of yellow robots
            n_red_robots: Number of red robots
            n_initial_green_waste: Number of initial green waste items in z1
            n_initial_yellow_waste: Number of initial yellow waste items in z2
            n_initial_red_waste: Number of initial red waste items in z3
            max_steps: Maximum number of simulation steps
            seed: Random seed
        """
        super().__init__(seed=seed)
        
        self.width = width
        self.height = height
        self.grid = mesa.space.MultiGrid(width, height, torus=False)
        
        # Define zone boundaries (west to east)
        # z1: (0 to width/3) - low radioactivity
        # z2: (width/3 to 2*width/3) - medium radioactivity
        # z3: (2*width/3 to width) - high radioactivity
        z1_end = width // 3
        z2_end = (2 * width) // 3
        
        self.zone_boundaries = [
            ("z1", (0, z1_end)),          # zone 1: low radioactivity
            ("z2", (z1_end + 1, z2_end)), # zone 2: medium radioactivity
            ("z3", (z2_end + 1, width - 1))  # zone 3: high radioactivity
        ]
        
        # Create radioactivity for each cell based on zone
        self._radioactivity_map = {}
        for x in range(width):
            for y in range(height):
                if x <= z1_end:
                    zone_name = "z1"
                    radioactivity_level = float(self.rng.uniform(0.0, 0.33))
                elif x <= z2_end:
                    zone_name = "z2"
                    radioactivity_level = float(self.rng.uniform(0.34, 0.66))
                else:
                    zone_name = "z3"
                    radioactivity_level = float(self.rng.uniform(0.67, 1.0))

                cell_agent = RadioactivityCell(self, zone_name, radioactivity_level)
                self.grid.place_agent(cell_agent, (x, y))
                self._radioactivity_map[(x, y)] = cell_agent

        # Create a waste disposal zone along the entire easternmost column
        self.disposal_zone_x = width - 1
        self.disposal_zone_cells = set()
        for y in range(height):
            disposal_cell = WasteDisposalZone(self)
            self.grid.place_agent(disposal_cell, (self.disposal_zone_x, y))
            self.disposal_zone_cells.add((self.disposal_zone_x, y))
        
        # Logging and statistics
        self.waste_collected = 0
        self.waste_disposed = 0
        self.steps = 0
        self.max_steps = max_steps
        
        # Data collection
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Green_Waste_Ground": lambda m: self._count_waste(WasteType.GREEN),
                "Green_Waste_Carried": lambda m: self._count_carried_waste(WasteType.GREEN),
                "Yellow_Waste_Ground": lambda m: self._count_waste(WasteType.YELLOW),
                "Yellow_Waste_Carried": lambda m: self._count_carried_waste(WasteType.YELLOW),
                "Red_Waste_Ground": lambda m: self._count_waste(WasteType.RED),
                "Red_Waste_Carried": lambda m: self._count_carried_waste(WasteType.RED),
                "Waste_Disposed": lambda m: m.waste_disposed,
                "Green_Robots_With_Inventory": lambda m: self._count_robots_with_inventory(GreenRobot),
                "Yellow_Robots_With_Inventory": lambda m: self._count_robots_with_inventory(YellowRobot),
                "Red_Robots_With_Inventory": lambda m: self._count_robots_with_inventory(RedRobot),
            }
        )
        
        # Create robots
        for i in range(n_green_robots):
            robot = GreenRobot(self)
            x = self.rng.integers(0, z1_end + 1)
            y = self.rng.integers(0, height)
            self.grid.place_agent(robot, (x, y))
        
        for i in range(n_yellow_robots):
            robot = YellowRobot(self)
            x = self.rng.integers(0, z2_end + 1)
            y = self.rng.integers(0, height)
            self.grid.place_agent(robot, (x, y))
        
        for i in range(n_red_robots):
            robot = RedRobot(self)
            x = self.rng.integers(0, width)
            y = self.rng.integers(0, height)
            self.grid.place_agent(robot, (x, y))
        
        # Create initial green waste in z1
        for i in range(n_initial_green_waste):
            waste = Waste(self, WasteType.GREEN)
            x = self.rng.integers(0, z1_end + 1)
            y = self.rng.integers(0, height)
            self.grid.place_agent(waste, (x, y))

        # Create initial yellow waste in z2
        for i in range(n_initial_yellow_waste):
            waste = Waste(self, WasteType.YELLOW)
            x = self.rng.integers(z1_end + 1, z2_end + 1)
            y = self.rng.integers(0, height)
            self.grid.place_agent(waste, (x, y))

        # Create initial red waste in z3
        for i in range(n_initial_red_waste):
            waste = Waste(self, WasteType.RED)
            x = self.rng.integers(z2_end + 1, width-1)
            y = self.rng.integers(0, height)
            self.grid.place_agent(waste, (x, y))
        
        # Collect initial data
        self.datacollector.collect(self)

    def perceive(self, agent):
        """
        Provide percepts: observations from the agent's current cell and its
        four Von Neumann neighbors.
 
        Percepts contain only dynamic, observable information, what is
        physically present on the grid right now. Static environment constants
        like grid dimensions are given to
        each robot once at __init__ time and stored in their knowledge base;
        they do not need to be re-sent every step.
 
        Returns a dictionary with:
            agent_pos       - current (x, y) position
            waste_here      - list of Waste objects in the current cell that
                              this robot type is allowed to pick up
            agents_here     - list of other robots sharing the current cell
            neighbor_waste  - list of dicts describing accessible waste in
                              adjacent cells: {pos, type, waste_type}
            neighbor_radioactivity - list of dicts describing adjacent cells:
                              {pos, zone, radioactivity}
            radioactivity   - radioactivity level of the current cell [0, 1]
            zone            - zone name of the current cell ("z1"/"z2"/"z3")
            disposal_zone_x - x-coordinate of the disposal column (static but
                              needed by RedRobot at runtime for the dispose check;
                              already stored in knowledge["disposal_x"] so this
                              is redundant, kept for observability/debugging)
            action_failed   - False by default; set to True by _do_* methods
                              when a requested action cannot be executed, so the
                              agent can detect failure on the next step
        """
        current_cell_radioactivity = self._radioactivity_map[agent.pos]
 
        percepts = {
            "agent_pos":      agent.pos,
            "waste_here":     [],
            "agents_here":    [],
            "neighbor_waste": [],
            "neighbor_radioactivity": [],
            "radioactivity":  current_cell_radioactivity.radioactivity_level,
            "zone":           current_cell_radioactivity.zone_name,
            "action_failed":  False,
        }
 
        # What is in the agent's current cell?
        cell_contents = self.grid.get_cell_list_contents([agent.pos])
        for obj in cell_contents:
            if isinstance(obj, Waste) and self._waste_accessible_to_robot(agent, obj.pos, obj.waste_type):
                percepts["waste_here"].append(obj)
            elif isinstance(obj, (GreenRobot, YellowRobot, RedRobot)) and obj != agent:
                percepts["agents_here"].append(obj)
 
        # What is in the four neighboring cells?
        raw_neighbors = [
            (agent.pos[0] + dx, agent.pos[1] + dy)
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]
            if 0 <= agent.pos[0] + dx < self.width
            and 0 <= agent.pos[1] + dy < self.height
        ]
        for neighbor_pos in raw_neighbors:
            neighbor_radioactivity = self._radioactivity_map[neighbor_pos]
            percepts["neighbor_radioactivity"].append({
                "pos": neighbor_pos,
                "zone": neighbor_radioactivity.zone_name,
                "radioactivity": neighbor_radioactivity.radioactivity_level,
            })
            for obj in self.grid.get_cell_list_contents([neighbor_pos]):
                if isinstance(obj, Waste) and self._waste_accessible_to_robot(agent, obj.pos, obj.waste_type):
                    percepts["neighbor_waste"].append({
                        "pos":        neighbor_pos,
                        "type":       "waste",
                        "waste_type": obj.waste_type,
                    })
 
        return percepts

    def _get_radioactivity_at(self, pos):
        """Get zone name and radioactivity level for a position."""
        cell_agent = self._radioactivity_map.get(pos)
        if cell_agent is None:
            return {"zone": None, "level": None}
        return {"zone": cell_agent.zone_name, "level": cell_agent.radioactivity_level}
    
    
    def _waste_accessible_to_robot(self, robot, waste_pos, waste_type):
        """Check if robot can pick up waste at this position based on waste type and location"""
        from agents import GreenRobot, YellowRobot, RedRobot
        
        z1_end = self.width // 3
        z2_end = (2 * self.width) // 3
        x, _ = waste_pos
        
        if isinstance(robot, GreenRobot):
            # Green robots pick up green waste from z1 only
            return waste_type == WasteType.GREEN and x <= z1_end
        
        elif isinstance(robot, YellowRobot):
            # Yellow robots pick yellow waste in z2 and at the z1/z2 frontier
            return waste_type == WasteType.YELLOW and (x == z1_end or (z1_end < x <= z2_end))
        
        elif isinstance(robot, RedRobot):
            # Red robots pick red waste in z3 and at the z2/z3 frontier
            return waste_type == WasteType.RED and (x == z2_end or x > z2_end)
        
        return False

    def do(self, agent, action):
        """
        Execute action from agent. This is the environment's responsibility.
        Checks feasibility and applies consequences.
        
        Args:
            agent: The agent performing action
            action: Action dictionary with action type and parameters
            
        Returns:
            percepts: Updated percepts after action execution
        """
        if action is None:
            return self.perceive(agent)
        
        action_type = action.get("action")
        
        if action_type == "move":
            return self._do_move(agent, action)
        elif action_type == "pick_up":
            return self._do_pick_up(agent, action)
        elif action_type == "transform":
            return self._do_transform(agent, action)
        elif action_type == "put_down":
            return self._do_put_down(agent, action)
        elif action_type == "dispose":
            return self._do_dispose(agent, action)
        else:
            return self.perceive(agent)

    def _do_move(self, agent, action):
        """Execute move action"""
        target_pos = action.get("target_pos")
        
        # Check if move is valid
        if target_pos is None:
            return self.perceive(agent)
        
        x, y = target_pos
        
        # Check bounds
        if not (0 <= x < self.width and 0 <= y < self.height):
            return self.perceive(agent)
        
        # Check zone restrictions
        if not agent.can_move_to(target_pos):
            return self.perceive(agent)
        
        # Execute move
        self.grid.move_agent(agent, target_pos)
        return self.perceive(agent)

    def _do_pick_up(self, agent, action):
        """Execute pick up action"""
        target_waste = action.get("target")
        
        if target_waste is None or target_waste not in agent.model.agents:
            return self.perceive(agent)
        
        # Check if waste is in same cell
        if target_waste.pos != agent.pos:
            return self.perceive(agent)
        
        # Pick up waste
        target_waste.carried_by = agent.unique_id
        agent.inventory.append(target_waste)
        self.grid.remove_agent(target_waste)
        self.waste_collected += 1
        
        return self.perceive(agent)

    def _do_transform(self, agent, action):
        """Execute waste transformation action"""
        from_type = action.get("from_type")
        to_type = action.get("to_type")
        
        if from_type is None or to_type is None:
            return self.perceive(agent)
        
        # Count waste of from_type in inventory
        count = sum(1 for w in agent.inventory if w.waste_type == from_type)
        
        # Green to Yellow: 2 green into 1 yellow
        if from_type == WasteType.GREEN and to_type == WasteType.YELLOW:
            if count >= 2:
                # Remove 2 green wastes from inventory and model
                removed_count = 0
                new_inv = []
                wastes_to_remove = []
                for w in agent.inventory:
                    if w.waste_type == WasteType.GREEN and removed_count < 2:
                        wastes_to_remove.append(w)
                        removed_count += 1
                    else:
                        new_inv.append(w)
                
                # Remove wastes from model
                for waste in wastes_to_remove:
                    self.agents.remove(waste)
                
                agent.inventory = new_inv
                
                # Create 1 yellow waste
                new_waste = Waste(self, WasteType.YELLOW)
                agent.inventory.append(new_waste)
        
        # Yellow to Red: 2 yellow into 1 red
        elif from_type == WasteType.YELLOW and to_type == WasteType.RED:
            if count >= 2:
                # Remove 2 yellow wastes from inventory and model
                removed_count = 0
                new_inv = []
                wastes_to_remove = []
                for w in agent.inventory:
                    if w.waste_type == WasteType.YELLOW and removed_count < 2:
                        wastes_to_remove.append(w)
                        removed_count += 1
                    else:
                        new_inv.append(w)
                
                # Remove wastes from model
                for waste in wastes_to_remove:
                    self.agents.remove(waste)
                
                agent.inventory = new_inv
                
                # Create 1 red waste
                new_waste = Waste(self, WasteType.RED)
                agent.inventory.append(new_waste)
        
        return self.perceive(agent)

    def _do_put_down(self, agent, action):
        """Execute put down action - robot must be at appropriate frontier"""
        from agents import GreenRobot, YellowRobot, RedRobot
        
        if not agent.inventory:
            return self.perceive(agent)
        
        z1_end = self.width // 3
        z2_end = (2 * self.width) // 3
        x, y = agent.pos
        
        # Check if robot is at correct frontier for depositing
        can_deposit = False
        
        if isinstance(agent, GreenRobot):
            # Green robots deposit yellow waste at z1/z2 frontier
            waste = agent.inventory[0]
            if waste.waste_type == WasteType.YELLOW and x == z1_end:
                can_deposit = True
        
        elif isinstance(agent, YellowRobot):
            # Yellow robots deposit red waste at z2/z3 frontier
            waste = agent.inventory[0]
            if waste.waste_type == WasteType.RED and x == z2_end:
                can_deposit = True
        
        elif isinstance(agent, RedRobot):
            # Red robots can only put down at the disposal column
            waste = agent.inventory[0]
            if waste.waste_type == WasteType.RED and x == self.disposal_zone_x:
                can_deposit = True
        
        if not can_deposit:
            return self.perceive(agent)
        
        # Put down the first waste in inventory on the ground
        waste = agent.inventory.pop(0)
        waste.carried_by = None  # Mark as no longer being carried
        self.grid.place_agent(waste, agent.pos)
        
        return self.perceive(agent)

    def _do_dispose(self, agent, action):
        """Execute dispose action (remove waste permanently)"""
        if not agent.inventory:
            return self.perceive(agent)
        
        # Check if agent is at the disposal column
        if agent.pos[0] != self.disposal_zone_x:
            return self.perceive(agent)
        
        # Remove waste from inventory and model
        waste = agent.inventory.pop(0)
        waste.carried_by = None  # Clear the carrier reference
        self.agents.remove(waste)  # Remove from model's agents list
        self.waste_disposed += 1
        
        return self.perceive(agent)

    def step(self):
        """Execute one step of the model"""
        self.steps += 1
        
        # Check if max steps reached
        if self.max_steps is not None and self.steps > self.max_steps:
            return
        
        # Execute all robots in random order
        self.agents.select(lambda agent: isinstance(agent, (GreenRobot, YellowRobot, RedRobot))).shuffle_do("step_agent")
        
        # Collect data
        self.datacollector.collect(self)
        
        # Print step diagnostics
        print(f"Step {self.steps}/{self.max_steps if self.max_steps else 'unlimited'}: "
              f"Green W: {self._count_waste(WasteType.GREEN)} | "
              f"Yellow W: {self._count_waste(WasteType.YELLOW)} | "
              f"Red W: {self._count_waste(WasteType.RED)} | "
              f"Disposed: {self.waste_disposed}")

    def get_zone_for_pos(self, pos):
        """Determine which zone a position belongs to"""
        x, _ = pos
        z1_end = self.width // 3
        z2_end = (2 * self.width) // 3
        
        if x <= z1_end:
            return 1
        elif x <= z2_end:
            return 2
        else:
            return 3
    
    def get_frontier_cells_for_robot(self, robot):
        """Get frontier cells where robot should deposit waste"""
        from agents import GreenRobot, YellowRobot, RedRobot
        
        z1_end = self.width // 3
        z2_end = (2 * self.width) // 3
        
        frontier_cells = []
        
        if isinstance(robot, GreenRobot):
            # Green robots deposit yellow waste at z1/z2 frontier (x = z1_end)
            for y in range(self.height):
                frontier_cells.append((z1_end, y))
        
        elif isinstance(robot, YellowRobot):
            # Yellow robots deposit red waste at z2/z3 frontier (x = z2_end)
            for y in range(self.height):
                frontier_cells.append((z2_end, y))
        
        elif isinstance(robot, RedRobot):
            # Red robots dispose at the disposal column
            for y in range(self.height):
                frontier_cells.append((self.disposal_zone_x, y))

        return frontier_cells
    
    def get_pickup_frontier_for_robot(self, robot):
        """Get cells where robot should pick up waste"""
        from agents import GreenRobot, YellowRobot, RedRobot
        
        z1_end = self.width // 3
        z2_end = (2 * self.width) // 3
        
        pickup_cells = []
        
        if isinstance(robot, GreenRobot):
            # Green robots pick up green waste from z1
            for x in range(0, z1_end + 1):
                for y in range(self.height):
                    pickup_cells.append((x, y))
        
        elif isinstance(robot, YellowRobot):
            # Yellow robots pick up yellow waste from z1/z2 frontier
            for y in range(self.height):
                pickup_cells.append((z1_end, y))
        
        elif isinstance(robot, RedRobot):
            # Red robots pick up red waste from z2/z3 frontier
            for y in range(self.height):
                pickup_cells.append((z2_end, y))
        
        return pickup_cells

    def _count_waste(self, waste_type):
        """Count waste of given type in the environment (on grid, not in inventory/carried)"""
        count = 0
        # Iterate through all grid cells and count waste on the ground
        for x in range(self.width):
            for y in range(self.height):
                cell_contents = self.grid.get_cell_list_contents([(x, y)])
                for obj in cell_contents:
                    if isinstance(obj, Waste) and obj.waste_type == waste_type and obj.carried_by is None:
                        count += 1
        return count

    def _count_carried_waste(self, waste_type):
        """Count waste of given type being carried by robots"""
        count = 0
        for agent in self.agents:
            if isinstance(agent, Waste) and agent.waste_type == waste_type and agent.carried_by is not None:
                count += 1
        return count

    def _count_robots_with_inventory(self, robot_type):
        """Count robots of given type that carry waste"""
        return sum(1 for agent in self.agents 
                  if isinstance(agent, robot_type) and len(agent.inventory) > 0)

    def get_waste_carrier(self, waste):
        """Get the robot carrying a specific waste (by Robot unique_id), or None if on ground"""
        return waste.carried_by
