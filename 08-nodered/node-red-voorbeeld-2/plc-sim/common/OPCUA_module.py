from types import NoneType
from abc import abstractmethod
from typing import override

from asyncua.sync import Server, SyncNode
from asyncua import ua

from common.PLC import Tag, PLC_State, IOModule

def _variant_type_from_python_type(typ: type):
    if typ == float:
        return ua.VariantType.Double
    elif typ == bool:
        return ua.VariantType.Boolean
    elif typ == int:
        return ua.VariantType.Int32
    elif typ == str:
        return ua.VariantType.String
    elif typ == NoneType:
        return ua.VariantType.Null
    else:
        raise ValueError(f"Unsupported type for OPC-UA variable: {typ}")


class OPCUAVarFromTag:
    """
    Represents a variable in the OPC-UA server that is linked to a PLC tag.

    The value of the OPC-UA variable is set to the value of the PLC tag when write_output is called.
    A writable variable will update the PLC tag when read_input is called.
    """

    def __init__(self, var: SyncNode, tag: Tag, writable: bool = False):
        self.var = var
        self.tag = tag
        self.writable = writable

    def read_input(self):
        if not self.writable:
            return
        value = self.var.get_value()
        self.tag.set(value)

    def write_output(self):
        value = self.tag.get()
        self.var.set_value(ua.Variant(
            value, _variant_type_from_python_type(self.tag.datatype)))


class OPCUA_IO_Module[PLCState: PLC_State](IOModule[PLCState]):
    """
    Base class for an OPC-UA server IO module.
    """

    def __init__(self, port: int, namespace: str = "http://infm.cs.kuleuven.be/demo", name: str = "OPCUA_Server"):
        self.endpoint = f"opc.tcp://0.0.0.0:{port}/OPCUA"
        self.server = Server()
        self.server.set_server_name(name)
        self.server.set_endpoint(self.endpoint)
        self.namespace: str = self.server.register_namespace(
            namespace)  # type: ignore
        self.objects = self.server.nodes.objects
        self.variables = []

    @abstractmethod
    def _create_node_structure(self, plc_state: PLCState):
        """
        Create OPC UA nodes for the PLC state variables.
        To be implemented by subclasses.
        """
        ...

    @override
    def start_module(self, plc_state):
        self._create_node_structure(plc_state)
        self.server.start()
        print(f"OPC UA server running at {self.endpoint}")

    @override
    def stop_module(self, plc_state):
        self.server.stop()

    @override
    def read_inputs(self, plc_state):
        for var in self.variables:
            var.read_input()

    @override
    def write_outputs(self, plc_state):
        for var in self.variables:
            var.write_output()

    def add_root_object(self, name: str) -> SyncNode:
        return self.objects.add_object(self.namespace, name)

    def add_variable_from_tag(self, object: SyncNode, name: str, tag: Tag, writable: bool = False) -> OPCUAVarFromTag:
        writable = writable and tag.writable
        variant = ua.Variant(
            tag.get(), _variant_type_from_python_type(tag.datatype))
        var = object.add_variable(self.namespace, name, variant)
        if writable:
            var.set_writable()
        result = OPCUAVarFromTag(var, tag, writable)
        self.variables.append(result)
        return result
