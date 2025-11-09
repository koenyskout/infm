from common.simulation import Simulation, SimulationConfig
from physenv import PhysicalEnvironment
from heater_plc import Heater_PLC, PhysicalEnvModule, HeaterOPCUAModule

def main():
    # configureer simulatie
    simulation_config = SimulationConfig(simdt=0.5, simspeed=1.0)
    simulation = Simulation(simulation_config)

    # voeg fysische omgeving toe aan de simulatie
    physical_system = PhysicalEnvironment()
    simulation.add_entity(physical_system)

    # voeg PLC toe aan de simulatie
    simulation.add_entity(Heater_PLC(modules=[
        HeaterOPCUAModule(port=4840),
        PhysicalEnvModule(physical_system)
    ]))

    # start simulatie
    simulation.run()


if __name__ == "__main__":
    main()
