from common.PLC import IOModule, PLC_State, PLC, Tag
from common.OPCUA_module import OPCUA_IO_Module
from util import clamp
import random

class HeaterPLCState(PLC_State):
    def _create_tags(self):
        # Current room temperature (from sensor)
        # not writable by PLC
        self.current_temperature = Tag("PV", float, 0.0, writable=False)

        # setpoint (set externally)
        self.setpoint = Tag("SP", float, 21.0)

        # heater power (0-100); determined by PLC
        self.heater_power = Tag("Power", int, 0)

        # State for PID controller
        self.Kp = Tag("Kp", float, 4.0)  # Proportional gain
        self.Ki = Tag("Ki", float, 0.4)  # Integral gain
        self.Kd = Tag("Kd", float, 0.0)  # Derivative gain
        self.prev_err = Tag("PrevErr", float, 0.0)  # Previous error for derivative term
        self.i = Tag("Integral", float, 0.0)  # Integral term

class Heater_PLC(PLC):

    def _create_initial_state(self):
        return HeaterPLCState()

    def _control_logic(self, dt: float):
        (u, err, i) = self._pid_controller(self.plc_state.setpoint.get(),
                                           self.plc_state.current_temperature.get(),
                                           self.plc_state.Kp.get(),
                                           self.plc_state.Ki.get(),
                                           self.plc_state.Kd.get(),
                                           self.plc_state.prev_err.get(),
                                           self.plc_state.i.get(),
                                           dt,
                                           0, 100)
        self.plc_state.heater_power.set(int(clamp(u, 0, 100)))
        self.plc_state.prev_err.set(err)
        self.plc_state.i.set(i)



class PhysicalEnvModule(IOModule):
    """
    Module die de koppeling maakt tussen de fysieke omgeving en de PLC.
    Simuleert de werking van sensoren en actuatoren.
    """
    def __init__(self, physical_env):
        self.physical_env = physical_env

    def read_inputs(self, plc_state: HeaterPLCState):
        noise = random.gauss(0, 0.2)  # Simulate sensor noise
        plc_state.current_temperature.set(self.physical_env.room_temperature + noise)

    def write_outputs(self, plc_state: HeaterPLCState):
        self.physical_env.heater_power = plc_state.heater_power.get()

class HeaterOPCUAModule(OPCUA_IO_Module):
    """
    OPC-UA module voor de Heater PLC.
    """
    def _create_node_structure(self, plc_state: HeaterPLCState):
        heater_node = self.add_root_object("HeaterPLC")
        
        self.add_variable_from_tag(heater_node, 
                                   "CurrentTemperature",
                                   plc_state.current_temperature)
        self.add_variable_from_tag(heater_node, 
                                   "HeaterPower",
                                   plc_state.heater_power)
        
        # setpoint kan ingesteld worden via OPC-UA
        self.add_variable_from_tag(heater_node, 
                                   "Setpoint",
                                   plc_state.setpoint, writable=True)
