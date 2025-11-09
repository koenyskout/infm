from typing import override

from common.simulation import SimulatedEntity
from util import clamp

class PhysicalEnvironment(SimulatedEntity):
    """
    Simulatie van een fysieke omgeving, bestaande uit een kamer en een verwarmingselement.
    Zonder het verwarmingselement evolueert de kamertemperatuur naar de buitentemperatuur.
    """

    def __init__(self):
        self.heater_power = 0 # Heater power (0 = off, 100 = full power)
        self.room_temperature = 15.0  # Initial room temperature
        self.exterior_temperature = 5.0
        
    @override
    def step(self, dt: float):
        self.room_temperature -= 0.1 * (self.room_temperature - self.exterior_temperature) * dt
        self.room_temperature += 0.05 * self.heater_power * dt