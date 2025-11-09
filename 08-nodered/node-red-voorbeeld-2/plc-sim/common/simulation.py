import time
from abc import abstractmethod

class SimulatedEntity:
    """
    Abstract base class for all simulated entities.
    Each concrete entity needs to implement these methods.
    """

    @abstractmethod
    def start(self):
        """
        Start the simulation for this entity
        """
        ...

    @abstractmethod
    def stop(self):
        """
        Stop the simulation for this entity
        """
        ...

    @abstractmethod
    def step(self, dt: float):
        """
        Advance entity by the given simulation time
        """
        ...


class SimulationConfig:
    """
    Configuration for a simulation
    """

    def __init__(self, simdt=0.5, simspeed=1.0) -> None:
        # multiplier for simulated time vs. wall-clock time (1.0 = real-time, 2.0 = simulation advances at double time)
        self.simspeed = simspeed
        self.simdt = simdt  # in seconds: simulated time that elapses in each simulation step
        # in seconds: wall-clock time interval between simulation steps
        self.dt = self.simdt / self.simspeed
        if self.dt <= 0.05:
            self.dt = 0.05


class Simulation:
    """
    Manages and runs the simulation of multiple entities
    """

    def __init__(self, config: SimulationConfig):
        self.entities = []
        self.config = config
    
    def add_entity[T: SimulatedEntity](self, entity: T) -> T:
        self.entities.append(entity)
        return entity

    def run(self):
        print("Starting simulation...")
        try:
            for entity in self.entities:
                entity.start()
            while True:
                for entity in self.entities:
                    entity.step(self.config.simdt)
                time.sleep(self.config.dt)
        except KeyboardInterrupt:
            print("Simulation stopped by user.")
        finally:
            for entity in self.entities:
                try:
                    entity.stop()
                except:
                    pass