"""
Group: 7
Members:
Date:
Description: RobotMission Model for Multi-Agent Waste Collection System.

Key changes vs original
-----------------------
1. perceive() is strictly LOCAL — only current cell + 4 neighbours.
   Robots are NEVER told where distant waste is.  They must discover it.

2. RadioactivityAgent markers are placed on every cell at initialisation
   so robots can read their zone from percepts without any global query.

3. WasteDisposalZone markers are placed on the easternmost column (x = width-1).
   RedRobots detect them via percepts ("at_disposal_zone").

4. _waste_accessible_to_robot() checks zone, not exact column — robots can
   pick up waste anywhere in their accessible zone (not only at frontiers).

5. _do_put_down() lets robots drop waste anywhere within their zone.
   Green robots drop in z1, yellow robots drop in z2, red robots dispose at z3.

6. WasteType is imported from agents.py (single source of truth).
   The Waste class lives here; objects.py holds environment markers.
"""

import mesa
from agents import GreenRobot, YellowRobot, RedRobot, WasteType


class Waste(mesa.Agent):
    """Represents a waste object in the environment"""

    def __init__(self, model, waste_type):
        """
        Initialize a Waste object.
        
        Args:
            model: Model instance
            waste_type: WasteType enum
        """
        super().__init__(model)
        self.waste_type = waste_type
        self.collected = False
        self.carried_by = None  # Robot unique_id if being carried, None if on ground

    def __repr__(self):
        if self.carried_by is not None:
            return f"Waste({self.waste_type.value}, carried_by_robot_{self.carried_by})"
        else:
            return f"Waste({self.waste_type.value}, on_ground)"


class RobotMissionModel(mesa.Model):
    """Orchestrates the grid, agents, waste, and action validation."""

    def __init__(
        self,
        width=40,
        height=20,
        n_green_robots=5,
        n_yellow_robots=3,
        n_red_robots=2,
        n_initial_green_waste=30,
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
            max_steps: Maximum number of simulation steps
            seed: Random seed
        """
        super().__init__(seed=seed)

        self.width = width
        self.height = height
        self.grid = mesa.space.MultiGrid(width, height, torus=False)
        self.max_steps = max_steps
        self.steps = 0
        self.waste_collected = 0
        self.waste_disposed = 0

        # ------------------------------------------------------------------
        # Zone boundaries  (inclusive x ranges)
        # z1: [0,       z1_end]
        # z2: [z1_end+1, z2_end]
        # z3: [z2_end+1, width-1]
        # ------------------------------------------------------------------
        z1_end = width // 3
        z2_end = (2 * width) // 3

        self.zone_boundaries = [
            ("z1", (0, z1_end)),
            ("z2", (z1_end + 1, z2_end)),
            ("z3", (z2_end + 1, width - 1)),
        ]
        
        self.radioactivity = [1, 50, 100]  # Radioactivity levels for zones
        
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
        # ------------------------------------------------------------------
        for _ in range(n_green_robots):
            robot = GreenRobot(self)
            x = int(self.rng.integers(0, z1_end + 1))
            y = int(self.rng.integers(0, height))
            self.grid.place_agent(robot, (x, y))

        for _ in range(n_yellow_robots):
            robot = YellowRobot(self)
            x = int(self.rng.integers(0, z2_end + 1))
            y = int(self.rng.integers(0, height))
            self.grid.place_agent(robot, (x, y))

        for _ in range(n_red_robots):
            robot = RedRobot(self)
            x = int(self.rng.integers(0, width))
            y = int(self.rng.integers(0, height))
            self.grid.place_agent(robot, (x, y))

        # ------------------------------------------------------------------
        # Create initial green waste in z1
        # ------------------------------------------------------------------
        for _ in range(n_initial_green_waste):
            waste = Waste(self, WasteType.GREEN)
            x = int(self.rng.integers(0, z1_end + 1))
            y = int(self.rng.integers(0, height))
            self.grid.place_agent(waste, (x, y))
        
        # Collect initial data
        self.datacollector.collect(self)

    # ======================================================================
    # Perception  (STRICTLY LOCAL — only current cell + cardinal neighbours)
    # ======================================================================

    def perceive(self, agent) -> dict:
        """
        Provide percepts: observations from agent's current cell and neighbors.
        Includes target frontier and closest waste information.
        
        Args:
            agent: The agent perceiving
            
        Returns:
            percepts: Dictionary with observations
        """
        from agents import GreenRobot, YellowRobot, RedRobot
        
        percepts = {
            "agent_pos": agent.pos,
            "waste_here": [],
            "agents_here": [],
            "neighbors": [],
            "target_frontier": None,
            "closest_target_waste": None
        }
        
        # What's in my cell?
        cell_contents = self.grid.get_cell_list_contents([agent.pos])
        for obj in cell_contents:
            if isinstance(obj, Waste) and self._waste_accessible_to_robot(agent, obj.pos, obj.waste_type):
                percepts["waste_here"].append(obj)
            elif isinstance(obj, (GreenRobot, YellowRobot, RedRobot)) and obj is not agent:
                percepts["agents_here"].append(obj)
        
        # What's in neighboring cells?
        neighbors = self.grid.get_neighborhood(
            agent.pos, moore=False, include_center=False
        )
        for neighbor_pos in neighbors:
            neighbor_contents = self.grid.get_cell_list_contents([neighbor_pos])
            for obj in neighbor_contents:
                if isinstance(obj, Waste) and self._waste_accessible_to_robot(agent, obj.pos, obj.waste_type):
                    percepts["neighbors"].append({
                        "pos": neighbor_pos,
                        "type": "waste",
                        "waste_type": obj.waste_type
                    })
        
        # Add target frontier information for navigation
        z1_end = self.width // 3
        z2_end = (2 * self.width) // 3
        
        if isinstance(agent, GreenRobot):
            percepts["target_frontier"] = z1_end
        elif isinstance(agent, YellowRobot):
            percepts["target_frontier"] = z2_end
        elif isinstance(agent, RedRobot):
            percepts["target_frontier"] = self.width - 1
        
        # Find and report closest waste this robot can handle
        closest_waste = self._find_closest_target_waste(agent)
        if closest_waste:
            percepts["closest_target_waste"] = {
                "pos": closest_waste.pos,
                "waste_type": closest_waste.waste_type,
                "distance": self._manhattan_distance(agent.pos, closest_waste.pos)
            }
        
        return percepts
    
    def _manhattan_distance(self, pos1, pos2):
        """Calculate Manhattan distance between two positions"""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
    
    def _find_closest_target_waste(self, robot):
        """Find the closest waste that this robot type can handle"""

        closest_waste = None
        closest_distance = float('inf')
        
        for agent in self.agents:
            # Only consider waste that's on the ground
            if not isinstance(agent, Waste) or agent.pos is None or agent.carried_by is not None:
                continue
            
            if not self._waste_accessible_to_robot(robot, agent.pos, agent.waste_type):
                continue
            
            distance = self._manhattan_distance(robot.pos, agent.pos)
            
            if distance < closest_distance:
                closest_distance = distance
                closest_waste = agent
        
        return closest_waste
    
    def _waste_accessible_to_robot(self, robot, waste_pos, waste_type):
        """Check if robot can pick up waste at this position based on waste type and location"""
        from agents import GreenRobot, YellowRobot, RedRobot, WasteType
        
        z1_end = self.width // 3
        z2_end = (2 * self.width) // 3
        if x <= z1_end:
            return 1
        elif x <= z2_end:
            return 2
        return 3

    def _waste_accessible_to_robot(self, robot, waste_pos, waste_type) -> bool:
        """
        Return True if *robot* can pick up waste of *waste_type* at *waste_pos*.

        Rules (fixed vs original):
          GreenRobot  → picks GREEN waste anywhere in z1
          YellowRobot → picks YELLOW waste anywhere in z1 or z2
          RedRobot    → picks RED waste anywhere in z1, z2, or z3
        """
        zone = self.get_zone_for_pos(waste_pos)

        if isinstance(robot, GreenRobot):
            return waste_type == WasteType.GREEN and zone == 1

        elif isinstance(robot, YellowRobot):
            # Yellow robots pick yellow waste only at z1/z2 frontier where green robots deposit
            return waste_type == WasteType.YELLOW and x == z1_end
        
        elif isinstance(robot, RedRobot):
            # Reds robots pick up red waste from z2/z3 frontier where yellow robots deposit
            return waste_type == WasteType.RED and x == z2_end
        
        return False


    def do(self, agent, action: dict) -> dict:
        """ Validate and execute *action* for *agent*, return fresh percepts.
        """
        if action is None:
            return self.perceive(agent)

        action_type = action.get("action")
        dispatch = {
            "move":      self._do_move,
            "pick_up":   self._do_pick_up,
            "transform": self._do_transform,
            "put_down":  self._do_put_down,
            "dispose":   self._do_dispose,
        }
        handler = dispatch.get(action_type)
        if handler:
            return handler(agent, action)
        return self.perceive(agent)

    # ------------------------------------------------------------------
    # Move
    # ------------------------------------------------------------------

    def _do_move(self, agent, action) -> dict:
        target_pos = action.get("target_pos")
        if target_pos is None:
            return self.perceive(agent)

        x, y = target_pos
        if not (0 <= x < self.width and 0 <= y < self.height):
            return self.perceive(agent)

        if not agent.can_move_to(target_pos):
            return self.perceive(agent)

        self.grid.move_agent(agent, target_pos)
        return self.perceive(agent)

    # ------------------------------------------------------------------
    # Pick up
    # ------------------------------------------------------------------

    def _do_pick_up(self, agent, action) -> dict:
        target_waste = action.get("target")

        if target_waste is None or target_waste not in self.agents:
            return self.perceive(agent)

        # Must be in same cell and on the ground
        if target_waste.pos != agent.pos or target_waste.carried_by is not None:
            return self.perceive(agent)

        # Check robot type / waste type compatibility
        if not self._waste_accessible_to_robot(agent, agent.pos, target_waste.waste_type):
            return self.perceive(agent)

        target_waste.carried_by = agent.unique_id
        agent.inventory.append(target_waste)
        self.grid.remove_agent(target_waste)
        self.waste_collected += 1
        return self.perceive(agent)

    # ------------------------------------------------------------------
    # Transform
    # ------------------------------------------------------------------

    def _do_transform(self, agent, action) -> dict:
        from_type = action.get("from_type")
        to_type = action.get("to_type")

        if from_type is None or to_type is None:
            return self.perceive(agent)

        count = sum(1 for w in agent.inventory if w.waste_type == from_type)

        valid_transforms = [
            (WasteType.GREEN, WasteType.YELLOW, 2, GreenRobot),
            (WasteType.YELLOW, WasteType.RED, 2, YellowRobot),
        ]

        for src, dst, required, robot_cls in valid_transforms:
            if from_type == src and to_type == dst and isinstance(agent, robot_cls):
                if count < required:
                    return self.perceive(agent)

                # Remove the required number of source wastes
                removed = 0
                kept = []
                to_remove = []
                for w in agent.inventory:
                    if w.waste_type == src and removed < required:
                        to_remove.append(w)
                        removed += 1
                    else:
                        kept.append(w)

                for w in to_remove:
                    self.agents.remove(w)

                agent.inventory = kept

                # Add one waste of destination type
                new_waste = Waste(self, dst)
                new_waste.carried_by = agent.unique_id
                agent.inventory.append(new_waste)
                return self.perceive(agent)

        return self.perceive(agent)

    def _do_put_down(self, agent, action):
        """Execute put down action - robot must be at appropriate frontier"""
        from agents import GreenRobot, YellowRobot, RedRobot, WasteType
        
        if not agent.inventory:
            return self.perceive(agent)

        waste = agent.inventory[0]
        zone = self.get_zone_for_pos(agent.pos)

        can_deposit = False

        if isinstance(agent, GreenRobot):
            # Green robots deposit yellow waste in z1
            if waste.waste_type == WasteType.YELLOW and zone == 1:
                can_deposit = True

        elif isinstance(agent, YellowRobot):
            # Yellow robots deposit red waste at z2/z3 frontier
            waste = agent.inventory[0]
            if waste.waste_type == WasteType.RED and x == z2_end:
                can_deposit = True
        
        elif isinstance(agent, RedRobot):
            # Red robots dispose in the waste disposal zone (end of z3, eastmost position)
            waste = agent.inventory[0]
            if waste.waste_type == WasteType.RED and x == self.width - 1:
                can_deposit = True

        if not can_deposit:
            return self.perceive(agent)

        waste = agent.inventory.pop(0)
        waste.carried_by = None
        self.grid.place_agent(waste, agent.pos)
        return self.perceive(agent)

    # ------------------------------------------------------------------
    # Dispose (permanently remove red waste at disposal zone)
    # ------------------------------------------------------------------

    def _do_dispose(self, agent, action) -> dict:
        """Red robot disposes of red waste at the WasteDisposalZone."""
        if not isinstance(agent, RedRobot):
            return self.perceive(agent)

        if not agent.inventory:
            return self.perceive(agent)
        
        # Check if agent is at the disposal zone (eastmost position)
        x, y = agent.pos
        if x != self.width - 1:
            return self.perceive(agent)

        waste = agent.inventory.pop(0)
        waste.carried_by = None
        self.agents.remove(waste)
        self.waste_disposed += 1
        return self.perceive(agent)

    # ======================================================================
    # Simulation step
    # ======================================================================

    def step(self):
        self.steps += 1

        if self.max_steps is not None and self.steps > self.max_steps:
            return

        self.agents.select(
            lambda a: isinstance(a, (GreenRobot, YellowRobot, RedRobot))
        ).shuffle_do("step_agent")

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
            # Red robots dispose at disposal zone 
            for y in range(self.height):
                frontier_cells.append((self.width - 1, y))

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

    def _count_carried_waste(self, waste_type: WasteType) -> int:
        """Count waste of given type currently being carried by a robot."""
        return sum(
            1 for a in self.agents
            if isinstance(a, Waste)
            and a.waste_type == waste_type
            and a.carried_by is not None
        )

    def _count_robots_with_inventory(self, robot_cls) -> int:
        """Count robots of given class that have at least one waste item."""
        return sum(
            1 for a in self.agents
            if isinstance(a, robot_cls) and len(a.inventory) > 0
        )

    def _manhattan_distance(self, pos1, pos2) -> int:
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])