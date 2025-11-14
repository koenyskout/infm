from typing import override
from common.PLC import PLC, IOModule, PLC_State, Tag
from common.OPCUA_module import OPCUA_IO_Module
from physenv import PhysicalEnvironment

class Door_PLC_State(PLC_State):
    """
    PLC State for the Door controller.
    """

    @override
    def _create_tags(self):
        self.door1_opened_sensor = Tag("Door_1_Opened", bool, True, writable=False)
        self.door2_opened_sensor = Tag("Door_2_Opened", bool, True, writable=False)
        self.door3_opened_sensor = Tag("Door_3_Opened", bool, True, writable=False)
        self.door4_opened_sensor = Tag("Door_4_Opened", bool, True, writable=False)

        self.door1_closed_sensor = Tag("Door_1_Closed", bool, False, writable=False)
        self.door2_closed_sensor = Tag("Door_2_Closed", bool, False, writable=False)
        self.door3_closed_sensor = Tag("Door_3_Closed", bool, False, writable=False)
        self.door4_closed_sensor = Tag("Door_4_Closed", bool, False, writable=False)

        self.door1_target = Tag("Door_1_Target", bool, True, writable=True) # True = open, False = closed
        self.door2_target = Tag("Door_2_Target", bool, True, writable=True)
        self.door3_target = Tag("Door_3_Target", bool, True, writable=True)
        self.door4_target = Tag("Door_4_Target", bool, True, writable=True)

        self.door1_motor = Tag("Door_1_Motor", int, 0, writable=True) # 0 = stopped, 1 = closing, 2 = opening
        self.door2_motor = Tag("Door_2_Motor", int, 0, writable=True)
        self.door3_motor = Tag("Door_3_Motor", int, 0, writable=True)
        self.door4_motor = Tag("Door_4_Motor", int, 0, writable=True)
        


class Door_PLC(PLC[Door_PLC_State]):
    """
    A simulated PLC that controls the status of 4 doors (open/closed).
    """

    @override
    def _create_initial_state(self):
        return Door_PLC_State()
    
    def _set_motor(self, motor_tag: Tag, opened_sensor_value: bool, closed_sensor_value: bool, desired_open: bool):
        if opened_sensor_value and closed_sensor_value:
            # error condition, stop the motor
            motor_tag.set(0) # stop
        elif desired_open and not opened_sensor_value:
            # need to open
            motor_tag.set(2) # open
        elif not desired_open and not closed_sensor_value:
            # need to close
            motor_tag.set(1) # close
        else:
            motor_tag.set(0) # stop

    @override
    def _control_logic(self, dt):
        self._set_motor(self.plc_state.door1_motor, self.plc_state.door1_opened_sensor.get(), self.plc_state.door1_closed_sensor.get(), self.plc_state.door1_target.get())
        self._set_motor(self.plc_state.door2_motor, self.plc_state.door2_opened_sensor.get(), self.plc_state.door2_closed_sensor.get(), self.plc_state.door2_target.get())
        self._set_motor(self.plc_state.door3_motor, self.plc_state.door3_opened_sensor.get(), self.plc_state.door3_closed_sensor.get(), self.plc_state.door3_target.get())
        self._set_motor(self.plc_state.door4_motor, self.plc_state.door4_opened_sensor.get(), self.plc_state.door4_closed_sensor.get(), self.plc_state.door4_target.get())

class DoorOPCUAModule(OPCUA_IO_Module[Door_PLC_State]):
    """
    OPC-UA IO module for the Door PLC.
    """
    def __init__(self, port: int, name: str = "Door_OPCUA_Server"):
        super().__init__(port, name=name)
    
    @override
    def _create_node_structure(self, plc_state):
        doors = self.add_root_object("Doors")
        door1 = doors.add_object(self.namespace, "Door_1")
        door2 = doors.add_object(self.namespace, "Door_2")
        door3 = doors.add_object(self.namespace, "Door_3")
        door4 = doors.add_object(self.namespace, "Door_4")

        self.add_variable_from_tag(door1, "Door_1_Opened", plc_state.door1_opened_sensor)
        self.add_variable_from_tag(door1, "Door_1_Closed", plc_state.door1_closed_sensor)
        self.add_variable_from_tag(door1, "Door_1_Target", plc_state.door1_target, writable=True)
        self.add_variable_from_tag(door1, "Door_1_Motor", plc_state.door1_motor)

        self.add_variable_from_tag(door2, "Door_2_Opened", plc_state.door2_opened_sensor)
        self.add_variable_from_tag(door2, "Door_2_Closed", plc_state.door2_closed_sensor)
        self.add_variable_from_tag(door2, "Door_2_Target", plc_state.door2_target, writable=True)
        self.add_variable_from_tag(door2, "Door_2_Motor", plc_state.door2_motor)

        self.add_variable_from_tag(door3, "Door_3_Opened", plc_state.door3_opened_sensor)
        self.add_variable_from_tag(door3, "Door_3_Closed", plc_state.door3_closed_sensor)
        self.add_variable_from_tag(door3, "Door_3_Target", plc_state.door3_target, writable=True)
        self.add_variable_from_tag(door3, "Door_3_Motor", plc_state.door3_motor)

        self.add_variable_from_tag(door4, "Door_4_Opened", plc_state.door4_opened_sensor)
        self.add_variable_from_tag(door4, "Door_4_Closed", plc_state.door4_closed_sensor)
        self.add_variable_from_tag(door4, "Door_4_Target", plc_state.door4_target, writable=True)
        self.add_variable_from_tag(door4, "Door_4_Motor", plc_state.door4_motor)

class DoorPhysicalEnvModule(IOModule[Door_PLC_State]):
    """
    IO module that simulates interaction with the physical environment
    """

    def __init__(self, env: PhysicalEnvironment):
        self.phys_env = env

    @override
    def read_inputs(self, plc_state):
        # read sensors from environment
        plc_state.door1_opened_sensor.set(self.phys_env.door_open[0] >= 100.0)
        plc_state.door2_opened_sensor.set(self.phys_env.door_open[1] >= 100.0)
        plc_state.door3_opened_sensor.set(self.phys_env.door_open[2] >= 100.0)
        plc_state.door4_opened_sensor.set(self.phys_env.door_open[3] >= 100.0)

        plc_state.door1_closed_sensor.set(self.phys_env.door_open[0] <= 0.0)
        plc_state.door2_closed_sensor.set(self.phys_env.door_open[1] <= 0.0)
        plc_state.door3_closed_sensor.set(self.phys_env.door_open[2] <= 0.0)
        plc_state.door4_closed_sensor.set(self.phys_env.door_open[3] <= 0.0)

    @staticmethod
    def to_motor_state(state: int):
        if state == 0:
            return "off"
        elif state == 1:
            return "closing"
        elif state == 2:
            return "opening"
        raise ValueError(f"Unknown motor state: {state}")
    
    @override
    def write_outputs(self, plc_state):
        # make motor commands affect environment
        self.phys_env.door_motors[0] = self.to_motor_state(plc_state.door1_motor.get())
        self.phys_env.door_motors[1] = self.to_motor_state(plc_state.door2_motor.get())
        self.phys_env.door_motors[2] = self.to_motor_state(plc_state.door3_motor.get())
        self.phys_env.door_motors[3] = self.to_motor_state(plc_state.door4_motor.get())


    @override
    def start_module(self, plc_state):
        # no need to do anything
        pass

    @override
    def stop_module(self, plc_state):
        # no need to do anything
        pass