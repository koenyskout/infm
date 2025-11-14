from typing import override

from common.simulation import SimulatedEntity
from util import clamp

class PhysicalEnvironment(SimulatedEntity):
    """
    Simulatie van een fysieke omgeving, bestaande uit een kamer met 4 deuren, een verwarmingselement, en een zuurstofniveau.
    Zonder het verwarmingselement evolueert de kamertemperatuur naar de buitentemperatuur.
    De deuren kunnen geopend en gesloten worden met motoren.
    Het zuurstofniveau wordt beïnvloed door een toevoerklep en het openen van de deuren
    """

    def __init__(self):
        # Heater and temperature
        self.heater_power = 0 # Heater power (0 = off, 100 = full power)
        self.room_temperature = 15.0  # Initial room temperature
        self.exterior_temperature = 5.0

        # Oxygen
        self.o2_concentration = 20.8  # Initial O2 concentration in %
        self.o2_supply_valve = 0.0  # valve state (0 = closed; 100 = open)

        # Door
        self.door_motors = ["off", "off", "off", "off"] # mode of the 4 door motors ("off", "opening", "closing")
        self.door_open = [100.0, 100.0, 100.0, 100.0] # status of the 4 doors (100% = fully open, 0% = fully closed)
        
    @override
    def step(self, dt: float):
        self.step_heater(dt)
        self.step_doors(dt)
        self.step_oxygen(dt)
    
    def step_heater(self, dt: float):
        self.room_temperature -= 0.1 * (self.room_temperature - self.exterior_temperature) * dt
        self.room_temperature += 0.05 * self.heater_power * dt
    
    def step_doors(self, dt: float):
        time_to_open_door = 4.0 # seconds to fully open or close a door
        door_motor_rate = 100.0/time_to_open_door # % per second
        for i in range(len(self.door_open)):
            if self.door_motors[i] == "opening":
                delta = door_motor_rate * dt
            elif self.door_motors[i] == "closing":
                delta = -door_motor_rate * dt
            else: # "off"
                delta = 0.0
            self.door_open[i] = clamp(self.door_open[i] + delta, 0.0, 100.0)

    def step_oxygen(self, dt: float):
        tau = 4.0 # in seconds
        alpha = dt / (dt + tau)
        gain = 0.08 # %O2 per % output
        
        natural_loss = 0.03
        loss_through_doors = 0.3 * sum(self.door_open)/100.0
        consumption_rate = natural_loss + loss_through_doors

        new_o2_concentration = self.o2_concentration + alpha * (gain * self.o2_supply_valve - consumption_rate * self.o2_concentration)
        self.o2_concentration = clamp(new_o2_concentration, 0, 100)
