from common.simulation import Simulation, SimulationConfig
from physenv import PhysicalEnvironment
from heater_plc import Heater_PLC, HeaterPhysicalEnvModule, HeaterOPCUAModule
from door_plc import Door_PLC, DoorOPCUAModule, DoorPhysicalEnvModule
from oxygen_plc import Oxygen_PLC, OxygenOPCUAModule, OxygenPhysicalEnvModule

def main():
    # configureer simulatie
    simulation_config = SimulationConfig(simdt=0.5, simspeed=1.0)
    simulation = Simulation(simulation_config)

    # voeg fysische omgeving toe aan de simulatie
    physical_system = PhysicalEnvironment()
    simulation.add_entity(physical_system)

    # voeg Heater PLC toe aan de simulatie
    simulation.add_entity(Heater_PLC(modules=[
        HeaterOPCUAModule(port=4840),
        HeaterPhysicalEnvModule(physical_system)
    ]))

    # voeg Door PLC toe aan de simulatie
    simulation.add_entity(Door_PLC(modules=[
        DoorOPCUAModule(port=4841),
        DoorPhysicalEnvModule(physical_system)
    ]))

    # voeg Oxygen PLC toe aan de simulatie
    simulation.add_entity(Oxygen_PLC(modules=[
        OxygenOPCUAModule(port=4842),
        OxygenPhysicalEnvModule(physical_system)
    ]))

    # start simulatie
    simulation.run()


if __name__ == "__main__":
    main()
