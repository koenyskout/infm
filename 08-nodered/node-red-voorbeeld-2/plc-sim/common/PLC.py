from abc import abstractmethod
from typing import override
from collections.abc import Sequence

from common.simulation import SimulatedEntity
from util import clamp


class Tag[T]:
    def __init__(self, name: str, datatype: type[T], initial_value: T, writable=True) -> None:
        self.name = name
        self.datatype = datatype
        self.value = initial_value
        self.writable = writable

    def get(self) -> T:
        return self.value

    def set(self, value: T) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Tag({self.name}: {self.datatype.__name__} ({'RW' if self.writable else 'R'}) = {self.value})"


class PLC_State:
    """
    Abstract base class for the internal state of a PLC (process variables, controller outputs, alarms, ...)
    """

    def __init__(self):
        self._create_tags()
        # assert no duplicate tag names
        self._check_unique_tag_names()

    def _check_unique_tag_names(self):
        tag_names = [tag.name for tag in self.tags()]
        if len(tag_names) != len(set(tag_names)):
            raise ValueError("Duplicate tag names found")
        
    @abstractmethod
    def _create_tags(self):
        """
        Create the tags for the PLC state.
        To be implemented by concrete subclasses.
        """
        ...

    def tags(self) -> list[Tag]:
        """
        Get all tags defined in this PLC state.
        """
        return [value for value in self.__dict__.values() if isinstance(value, Tag)]

    def get_tag(self, name: str) -> Tag:
        """
        Get a tag by its name.
        Raises KeyError if no such tag exists.
        """
        for tag in self.tags():
            if tag.name == name:
                return tag
        raise KeyError(f"No tag with name '{name}' found.")
    
    def __getitem__(self, name: str) -> Tag:
        return self.get_tag(name)

    def __repr__(self) -> str:
        result = [self.__class__.__name__]
        for tag in self.tags():
            result.append(f"- {tag}")
        return "\n".join(result)


class IOModule[PLCState: PLC_State]:
    """
    A module that models an I/O interface for the PLC (e.g., interaction with sensors/actuators, OPC UA server, ...)
    """

    @abstractmethod
    def start_module(self, plc_state: PLCState):
        """
        Start the IO module and initialize with given PLC state
        """
        ...

    @abstractmethod
    def stop_module(self, plc_state: PLCState):
        """
        Stop the IO module
        """
        ...

    @abstractmethod
    def read_inputs(self, plc_state: PLCState):
        """
        Update PLC state with input values provided by this module
        """
        ...

    @abstractmethod
    def write_outputs(self, plc_state: PLCState):
        """
        Update outputs based on PLC state
        """
        ...


class PLC[PLCState: PLC_State](SimulatedEntity):
    """
    Represents a generic PLC (Programmable Logic Controller).
    A PLC is a simulated entity.
    """

    def __init__(self, modules: Sequence[IOModule[PLCState]]):
        self.modules = modules
        self.plc_state = self._create_initial_state()

    @override
    def start(self):
        for module in self.modules:
            module.start_module(self.plc_state)

    @override
    def stop(self):
        for module in self.modules:
            module.stop_module(self.plc_state)

    @override
    def step(self, dt: float):
        # Read from modules
        self._input_scan()

        # Update internal state by executing control logic
        self._control_logic(dt)

        # Let modules write outputs
        self._output_update()

    def _input_scan(self):
        """
        Update PLC state by scanning input from all modules
        """
        for module in self.modules:
            module.read_inputs(self.plc_state)

    def _output_update(self):
        """
        Output PLC state to all modules
        """
        for module in self.modules:
            module.write_outputs(self.plc_state)

    @abstractmethod
    def _create_initial_state(self) -> PLCState:
        """
        Create the initial PLC state.
        To be implemented by concrete subclasses.
        """
        ...

    @abstractmethod
    def _control_logic(self, dt: float):
        """
        Execute the control logic to update the internal PLC state.
        To be implemented by concrete subclasses.

        Parameters:
        dt: elapsed (simulation) time since last time control logic was ran
        """
        ...


    @staticmethod
    def _pid_controller(setpoint: float, actual: float, Kp: float, Ki: float, Kd: float, prev_err: float, i: float, dt: float, umin: float, umax: float):
        """
        Simple PID controller implementation.
        Returns (u, err, i) where u is the control output, err is the current error, and i is the updated integral term.
        :param setpoint: desired setpoint
        :param actual: actual process variable
        :param Kp: proportional gain
        :param Ki: integral gain
        :param Kd: derivative gain
        :param prev_err: previous error
        :param i: current integral term
        :param dt: time step
        :param umin: minimum output
        :param umax: maximum output
        """
        err = setpoint - actual 
        d_err = (err - prev_err) / dt
        u = Kp * err + Ki * i + Kd * d_err
        if not (u >= umax and err > 0) and not (u <= umin and err < 0):
        # prevent integral windup
            i += err * dt
        u = clamp(u, umin, umax)
        return u, err, i