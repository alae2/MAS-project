"""
Group: 7
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

    def __init__(self, model, waste_type):
        super().__init__(model)
        self.waste_type = waste_type
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
