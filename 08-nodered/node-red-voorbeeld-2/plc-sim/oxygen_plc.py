import random
from typing import override

from common.PLC import PLC, PLC_State, IOModule, Tag
from common.OPCUA_module import OPCUA_IO_Module
from common.modbus_module import Modbus_IO_Module

from common.mqtt_module import MQTT_IO_Module, MQTTTagMapping
from physenv import PhysicalEnvironment
from util import clamp


class Oxy_PLC_State(PLC_State):
    """
    PLC state specific to the Oxygen controller
    """

    @override
    def _create_tags(self):
        # process variables
        # oxygen process variable from sensor (%)
        self.sensor_O2_PV = Tag("O2_PV", float, 0, writable=False)

        # PLC variables
        self.Output = Tag("Output", int, 0)  # output to valve 0..100 (%)
        self.High_Alarm = Tag("High_Alarm", bool, False)
        self.Low_Alarm = Tag("Low_Alarm", bool, False)

        # externally set variables
        self.ext_O2_SP = Tag("O2_SP", float, 21.0)  # oxygen setpoint (%)
        self.ext_ManualOverride = Tag(
            "ManualOverride", bool, False)  # manual override (bool)
        # manual output 0..100 (%)
        self.ext_Output_Manual = Tag("Output_Manual", int, 10)

        # configuration variables for PID controller
        self.ext_Kp = Tag("Kp", float, 2.8)  # proportional gain
        self.ext_Ki = Tag("Ki", float, 0.23)  # integral gain
        self.ext_Kd = Tag("Kd", float, 2.0)  # derivative gain
        self._i = Tag("i", float, 0.0)  # integral term
        self._prev_err = Tag("prev_err", float, 0.0)  # previous error


class Oxygen_PLC(PLC[Oxy_PLC_State]):
    """
    A simulated PLC that controls the oxygen level in the environment by opening or closing a supply valve.
    Can be manually overridden.
    """

    @override
    def _create_initial_state(self):
        return Oxy_PLC_State()

    @override
    def _control_logic(self, dt):
        # Control
        if not self.plc_state.ext_ManualOverride.get():  # AUTO mode
            (u, err, i) = self._pid_controller(
                setpoint=self.plc_state.ext_O2_SP.get(),
                actual=self.plc_state.sensor_O2_PV.get(),
                Kp=self.plc_state.ext_Kp.get(),
                Ki=self.plc_state.ext_Ki.get(),
                Kd=self.plc_state.ext_Kd.get(),
                prev_err=self.plc_state._prev_err.get(),
                i=self.plc_state._i.get(),
                dt=dt,
                umin=0,
                umax=100
            )
            self.plc_state.Output.set(int(u))
            self.plc_state._i.set(i)
            self.plc_state._prev_err.set(err)
        else:  # MANUAL mode
            self.plc_state.Output.set(clamp(
                self.plc_state.ext_Output_Manual.get(), 0, 100))

        # Set alarm conditions
        self.plc_state.High_Alarm.set(self.plc_state.sensor_O2_PV.get() > 23.5)
        self.plc_state.Low_Alarm.set(self.plc_state.sensor_O2_PV.get() < 19.5)


class OxygenOPCUAModule(OPCUA_IO_Module[Oxy_PLC_State]):
    """
    IO Module with OPC-UA server for the oxygen PLC controller.
    This module links the OPC-UA variables to the PLC state.
    """

    @override
    def _create_node_structure(self, plc_state):
        oxy = self.add_root_object("Oxygen")

        self.add_variable_from_tag(oxy, "O2_PV", plc_state.sensor_O2_PV)
        self.add_variable_from_tag(
            oxy, "O2_SP", plc_state.ext_O2_SP, writable=True)
        self.add_variable_from_tag(
            oxy, "ManualOverride", plc_state.ext_ManualOverride, writable=True)
        self.add_variable_from_tag(oxy, "Output", plc_state.Output)
        self.add_variable_from_tag(
            oxy, "Output_Manual", plc_state.ext_Output_Manual, writable=True)
        self.add_variable_from_tag(oxy, "High_Alarm", plc_state.High_Alarm)
        self.add_variable_from_tag(oxy, "Low_Alarm", plc_state.Low_Alarm)

        self.add_variable_from_tag(oxy, "Kp", plc_state.ext_Kp, writable=True)
        self.add_variable_from_tag(oxy, "Ki", plc_state.ext_Ki, writable=True)
        self.add_variable_from_tag(oxy, "Kd", plc_state.ext_Kd, writable=True)


class OxygenPhysicalEnvModule(IOModule[Oxy_PLC_State]):
    """
    IO module that simulates interaction with the physical environment
    """

    def __init__(self, env: PhysicalEnvironment):
        self.phys_env = env

    @override
    def read_inputs(self, plc_state):
        # read sensors from environment
        noise = random.gauss(0.0, 0.02)
        plc_state.sensor_O2_PV.set(self.phys_env.o2_concentration + noise)

    @override
    def write_outputs(self, plc_state):
        self.phys_env.o2_supply_valve = plc_state.Output.get()

    @override
    def start_module(self, plc_state):
        # no need to do anything
        pass

    @override
    def stop_module(self, plc_state):
        # no need to do anything
        pass


class OxyMQTTModule(MQTT_IO_Module[Oxy_PLC_State]):

    def __init__(self,
                 broker_host: str,
                 broker_port: int,
                 topic_prefix: str = "/PLC/Oxygen",
                 publish_interval: float = 1.0,
                 only_send_changed: bool = True):
        super().__init__(broker_host, broker_port, topic_prefix,
                         publish_interval=publish_interval, only_send_changed=only_send_changed)

    @override
    def _create_mappings(self, plc_state) -> list[MQTTTagMapping]:
        return [
            MQTTTagMapping("/O2_PV", plc_state.sensor_O2_PV),
            MQTTTagMapping("/O2_SP", plc_state.ext_O2_SP, writable=True),
            MQTTTagMapping("/ManualOverride",
                           plc_state.ext_ManualOverride, writable=True),
            MQTTTagMapping("/Output", plc_state.Output),
            MQTTTagMapping("/Output_Manual",
                           plc_state.ext_Output_Manual, writable=True),
            MQTTTagMapping("/High_Alarm", plc_state.High_Alarm),
            MQTTTagMapping("/Low_Alarm", plc_state.Low_Alarm),
        ]