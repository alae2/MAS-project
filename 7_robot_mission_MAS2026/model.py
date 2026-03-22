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
from objects import RadioactivityAgent, WasteDisposalZone


class Waste(mesa.Agent):
    """Represents a waste item on the grid or in a robot's inventory."""

    def __init__(self, model, waste_type: WasteType):
        super().__init__(model)
        self.waste_type = waste_type
        self.carried_by = None  # unique_id of carrying robot, or None

    def __repr__(self):
        state = f"carried_by_{self.carried_by}" if self.carried_by is not None else "on_ground"
        return f"Waste({self.waste_type.value}, {state})"


class RobotMissionModel(mesa.Model):
    """Orchestrates the grid, agents, waste, and action validation."""

    def __init__(
        self,
        width: int = 40,
        height: int = 20,
        n_green_robots: int = 5,
        n_yellow_robots: int = 3,
        n_red_robots: int = 2,
        n_initial_green_waste: int = 30,
        max_steps: int = None,
        seed: int = None,
    ):
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

        # ------------------------------------------------------------------
        # Place RadioactivityAgent markers on every cell
        # ------------------------------------------------------------------
        for x in range(width):
            for y in range(height):
                if x <= z1_end:
                    zone, level = 1, 0.0
                elif x <= z2_end:
                    zone, level = 2, 0.5
                else:
                    zone, level = 3, 1.0
                marker = RadioactivityAgent(self, zone=zone, level=level)
                self.grid.place_agent(marker, (x, y))

        # ------------------------------------------------------------------
        # Place WasteDisposalZone markers on the easternmost column
        # ------------------------------------------------------------------
        for y in range(height):
            wdz = WasteDisposalZone(self)
            self.grid.place_agent(wdz, (width - 1, y))

        # ------------------------------------------------------------------
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

        # ------------------------------------------------------------------
        # Data collection
        # ------------------------------------------------------------------
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Green_Waste_Ground":            lambda m: m._count_waste(WasteType.GREEN),
                "Green_Waste_Carried":           lambda m: m._count_carried_waste(WasteType.GREEN),
                "Yellow_Waste_Ground":           lambda m: m._count_waste(WasteType.YELLOW),
                "Yellow_Waste_Carried":          lambda m: m._count_carried_waste(WasteType.YELLOW),
                "Red_Waste_Ground":              lambda m: m._count_waste(WasteType.RED),
                "Red_Waste_Carried":             lambda m: m._count_carried_waste(WasteType.RED),
                "Waste_Disposed":                lambda m: m.waste_disposed,
                "Green_Robots_With_Inventory":   lambda m: m._count_robots_with_inventory(GreenRobot),
                "Yellow_Robots_With_Inventory":  lambda m: m._count_robots_with_inventory(YellowRobot),
                "Red_Robots_With_Inventory":     lambda m: m._count_robots_with_inventory(RedRobot),
            }
        )
        self.datacollector.collect(self)

    # ======================================================================
    # Perception  (STRICTLY LOCAL — only current cell + cardinal neighbours)
    # ======================================================================

    def perceive(self, agent) -> dict:
        """
        Return a percept dictionary for *agent* based on what is observable
        from agent's current cell and its four cardinal neighbours ONLY.

        The agent is NEVER told about distant waste.  It must explore to
        discover it.

        Percept keys
        ------------
        agent_pos          : (x, y) — current position
        zone               : int 1/2/3 — radioactive zone of current cell
        radioactivity      : float — level of current cell
        at_disposal_zone   : bool — True if a WasteDisposalZone is here
        waste_here         : list[Waste] — ground waste in current cell
        agents_here        : list[robot] — other robots in current cell
        neighbors          : list[dict] — observable info from adjacent cells
                             each dict: {pos, zone, waste_type (if waste present)}
        """
        percepts = {
            "agent_pos": agent.pos,
            "zone": None,
            "radioactivity": None,
            "at_disposal_zone": False,
            "waste_here": [],
            "agents_here": [],
            "neighbors": [],
        }

        # --- Current cell contents ---
        cell = self.grid.get_cell_list_contents([agent.pos])
        for obj in cell:
            if isinstance(obj, RadioactivityAgent):
                percepts["zone"] = obj.zone
                percepts["radioactivity"] = obj.level
            elif isinstance(obj, WasteDisposalZone):
                percepts["at_disposal_zone"] = True
            elif isinstance(obj, Waste) and obj.carried_by is None:
                percepts["waste_here"].append(obj)
            elif isinstance(obj, (GreenRobot, YellowRobot, RedRobot)) and obj is not agent:
                percepts["agents_here"].append(obj)

        # --- Four cardinal neighbours ---
        nb_positions = self.grid.get_neighborhood(
            agent.pos, moore=False, include_center=False
        )
        for nb_pos in nb_positions:
            nb_info = {"pos": nb_pos, "type": "empty"}
            nb_cell = self.grid.get_cell_list_contents([nb_pos])
            for obj in nb_cell:
                if isinstance(obj, Waste) and obj.carried_by is None:
                    nb_info["type"] = "waste"
                    nb_info["waste_type"] = obj.waste_type
                    break  # report the first waste seen in that cell
            percepts["neighbors"].append(nb_info)

        return percepts

    # ======================================================================
    # Zone helpers
    # ======================================================================

    def get_zone_for_pos(self, pos) -> int:
        x, _ = pos
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
            return waste_type == WasteType.YELLOW and zone in (1, 2)

        elif isinstance(robot, RedRobot):
            return waste_type == WasteType.RED  # all zones accessible

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

    # ------------------------------------------------------------------
    # Put down (deposit waste on the ground)
    # ------------------------------------------------------------------

    def _do_put_down(self, agent, action) -> dict:
        """
        Robot drops the first waste in its inventory onto its current cell.

        Deposit rules (fixed — no longer restricted to exact frontier column):
          GreenRobot  → may deposit yellow waste anywhere in z1
          YellowRobot → may deposit red waste anywhere in z2
          RedRobot    → should use 'dispose' at the disposal zone instead
        """
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
            # Yellow robots deposit red waste in z2
            if waste.waste_type == WasteType.RED and zone == 2:
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

        # Verify agent is actually at the disposal zone
        cell = self.grid.get_cell_list_contents([agent.pos])
        at_disposal = any(isinstance(obj, WasteDisposalZone) for obj in cell)
        if not at_disposal:
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

        print(
            f"Step {self.steps}"
            f"{'/' + str(self.max_steps) if self.max_steps else ''}: "
            f"Green={self._count_waste(WasteType.GREEN)} "
            f"Yellow={self._count_waste(WasteType.YELLOW)} "
            f"Red={self._count_waste(WasteType.RED)} "
            f"Disposed={self.waste_disposed}"
        )

    # ======================================================================
    # Statistics helpers
    # ======================================================================

    def _count_waste(self, waste_type: WasteType) -> int:
        """Count waste of given type lying on the ground (not carried)."""
        return sum(
            1 for a in self.agents
            if isinstance(a, Waste)
            and a.waste_type == waste_type
            and a.carried_by is None
            and a.pos is not None
        )

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