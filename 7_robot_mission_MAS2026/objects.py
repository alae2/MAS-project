"""
Group: 7
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

    def __init__(self, model, waste_type):
        super().__init__(model)
        self.waste_type = waste_type
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
