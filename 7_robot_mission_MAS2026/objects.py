"""
Group: 7
<<<<<<< HEAD
Members:
Date:
Description: Environment entities — Waste, Radioactivity, WasteDisposalZone
"""

import mesa


class Waste(mesa.Agent):
    """
    A piece of waste lying on the grid.
    waste_type is a WasteType enum imported from agents.py.
    carried_by stores the unique_id of the robot carrying this waste,
    or None when it is on the ground.
    """
=======
Members: Ouissal BOUTOUATOU, Alae TAOUDI, Mohammed SBAIHI
Date: March 18, 2026
Description: Passive environment objects for Robot Mission MAS
"""

import mesa
from enum import Enum


class WasteType(Enum):
    """Enumerate waste types."""
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class Waste(mesa.Agent):
    """Represents a waste object in the environment."""
>>>>>>> c29a05001d6440b6e38685de0b52567d978ac6e2

    def __init__(self, model, waste_type):
        super().__init__(model)
        self.waste_type = waste_type
<<<<<<< HEAD
        self.carried_by = None  # unique_id of carrying robot, or None

    def __repr__(self):
        state = f"carried_by_{self.carried_by}" if self.carried_by is not None else "on_ground"
        return f"Waste({self.waste_type.value}, {state})"


class RadioactivityAgent(mesa.Agent):
    """
    Static marker agent placed on every cell of the grid.
    Encodes the radioactive zone (1, 2, or 3) and a normalised
    radioactivity level in [0.0, 1.0].
    Robots read this during percepts to know which zone they are in.
    """

    def __init__(self, model, zone: int, level: float):
        """
        Args:
            zone:  1 = low, 2 = medium, 3 = high radioactivity
            level: float in [0.0, 1.0]
        """
        super().__init__(model)
        self.zone = zone
        self.level = level


class WasteDisposalZone(mesa.Agent):
    """
    Static marker placed on all cells of the easternmost column (x = width-1).
    Red robots detect this via percepts and know they can call 'dispose' here.
    """

    def __init__(self, model):
        super().__init__(model)
=======
        self.collected = False
        self.carried_by = None  # Robot unique_id if being carried, None if on ground

    def __repr__(self):
        if self.carried_by is not None:
            return f"Waste({self.waste_type.value}, carried_by_robot_{self.carried_by})"
        return f"Waste({self.waste_type.value}, on_ground)"


class RadioactivityCell(mesa.Agent):
    """Passive object representing radioactivity in a grid cell."""

    def __init__(self, model, zone_name, radioactivity_level):
        super().__init__(model)
        self.zone_name = zone_name
        self.radioactivity_level = radioactivity_level


class WasteDisposalZone(mesa.Agent):
    """Passive object representing the disposal zone location."""

    def __init__(self, model):
        super().__init__(model)
>>>>>>> c29a05001d6440b6e38685de0b52567d978ac6e2
