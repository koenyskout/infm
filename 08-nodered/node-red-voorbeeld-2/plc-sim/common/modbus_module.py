from abc import abstractmethod
import threading
from typing import Sequence, override
import asyncio

from pymodbus.client.mixin import ModbusClientMixin
from pymodbus import ModbusDeviceIdentification
from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import (
    ModbusServerContext,
    ModbusDeviceContext,
    ModbusSparseDataBlock,
)

from common.PLC import Tag, PLC_State, IOModule

# enum with Modbus data segments
class ModbusSegment:
    COILS = "coils"
    DISCRETE_INPUTS = "discrete_inputs"
    HOLDING_REGISTERS = "holding_registers"
    INPUT_REGISTERS = "input_registers"

class ModbusMap:
    """
    Map PLC tag names to Modbus addresses.
    """
    coils: dict[str, int] = {}            # tag_name -> coil address
    discrete_inputs: dict[str, int] = {}  # tag_name -> discrete input address
    holding_registers: dict[str, int] = {}  # tag_name -> HR address
    input_registers: dict[str, int] = {}    # tag_name -> IR address

    segments = {
        ModbusSegment.COILS: coils,
        ModbusSegment.DISCRETE_INPUTS: discrete_inputs,
        ModbusSegment.HOLDING_REGISTERS: holding_registers,
        ModbusSegment.INPUT_REGISTERS: input_registers,
    }

    def add_coil(self, tag_name: str):
        self.coils[tag_name] = len(self.coils)
    def add_discrete_input(self, tag_name: str):
        self.discrete_inputs[tag_name] = len(self.discrete_inputs)
    def add_holding_register(self, tag_name: str):
        self.holding_registers[tag_name] = len(self.holding_registers)
    def add_input_register(self, tag_name: str):
        self.input_registers[tag_name] = len(self.input_registers)

    def __repr__(self) -> str:
        # return, for each segment, the address and the corresponding tag name (ordered by address)
        result = ["ModbusMap:"]
        for segment_name, segment in [("Coils (co)", self.coils),
                                      ("Discrete Inputs (di)",
                                       self.discrete_inputs),
                                      ("Holding Registers (hr)",
                                       self.holding_registers),
                                      ("Input Registers (ir)", self.input_registers)]:
            result.append(f"  {segment_name}:")
            for tag_name, addr in sorted(segment.items(), key=lambda item: item[1]):
                result.append(f"    {addr}: {tag_name}")
        return "\n".join(result)

    def find(self, tag_name) -> tuple[int, str]:
        for segment_name, segment in self.segments.items():
            if tag_name in segment:
                return (segment[tag_name], segment_name)
        raise KeyError(f"Tag '{tag_name}' not found in ModbusMap")


class Modbus_IO_Module[PLCState: PLC_State](IOModule[PLCState]):
    """
    Base class for a Modbus TCP server IO module.
    """

    def __init__(self, port: int = 5020):
        self.port = port
        self.block_size = 100

        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._server_task: asyncio.Task | None = None
        self._started_evt = threading.Event()

    def _make_device(self):
        self.di = ModbusSparseDataBlock()  # discrete inputs (RO): 1 bit switches, sensors
        self.co = ModbusSparseDataBlock()  # coils (RW): 1 bit outputs, relays
        self.ir = ModbusSparseDataBlock()  # input registers (RO): measurements
        self.hr = ModbusSparseDataBlock()  # holding registers (RW): configuration

        # initialize to 0
        self.di.setValues(0, [0] * self.block_size)
        self.co.setValues(0, [0] * self.block_size)
        self.ir.setValues(0, [0] * self.block_size)
        self.hr.setValues(0, [0] * self.block_size)

        # Build a device context and register the 4 function-code groups
        dev = ModbusDeviceContext()
        dev.register(function_code=1, func_code="co", datablock=self.co)
        dev.register(function_code=2, func_code="di", datablock=self.di)
        dev.register(function_code=3, func_code="hr", datablock=self.hr)
        dev.register(function_code=4, func_code="ir", datablock=self.ir)
        return dev

    @abstractmethod
    def _create_mapping(self, plc_state: PLCState) -> ModbusMap:
        """
        Create the Modbus mapping for this module, based on the PLC state.
        """
        result = ModbusMap()
        for tag in plc_state.tags():
            if tag.datatype == bool:
                if tag.writable:
                    result.add_coil(tag.name)
                else:
                    result.add_discrete_input(tag.name)
            elif tag.datatype == int:
                if tag.writable:
                    result.add_holding_register(tag.name)
                else:
                    result.add_input_register(tag.name)
            elif tag.datatype == float:
                if tag.writable:
                    result.add_holding_register(tag.name)
                    result.add_holding_register(tag.name + "_hi")
                else:
                    result.add_input_register(tag.name)
                    result.add_input_register(tag.name + "_hi")
        print(result)
        return result
        ...

    @override
    def start_module(self, plc_state: PLCState):
        devices = {1: self._make_device()}
        context = ModbusServerContext(devices=devices, single=False)

        identity = ModbusDeviceIdentification()
        identity.VendorName = "ExampleCorp"
        identity.ProductName = "PyModbus 3.11 Async Server"
        identity.MajorMinorRevision = "1.0"

        if self._thread and self._thread.is_alive():
            return

        self.mapping = self._create_mapping(plc_state)

        self._started_evt.clear()

        def thread_main():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            async def run_server():
                await StartAsyncTcpServer(
                    context=context,
                    identity=identity,
                    address=("0.0.0.0", self.port),
                )

            # start server as a task, then flip the started event
            self._server_task = self._loop.create_task(run_server())
            self._loop.call_soon(self._started_evt.set)

            try:
                self._loop.run_forever()
            finally:
                # cleanup
                if self._server_task and not self._server_task.done():
                    self._server_task.cancel()
                    try:
                        self._loop.run_until_complete(self._server_task)
                    except Exception:
                        pass
                pending = asyncio.all_tasks(
                    loop=self._loop)  # type: ignore[arg-type]
                for t in pending:
                    t.cancel()
                try:
                    self._loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True))
                except Exception:
                    pass
                self._loop.close()

        self._thread = threading.Thread(
            target=thread_main, name="ModbusIOModule", daemon=True)
        self._thread.start()
        self._started_evt.wait(timeout=5.0)
        if not self._started_evt.is_set():
            raise RuntimeError("Failed to start Modbus server thread")
        
        self.write_outputs(plc_state)
        print(f"Modbus server started on port {self.port}")
      


    @override
    def stop_module(self, plc_state: PLCState):
        if not self._loop or not self._thread:
            return

        def stop_loop():
            if self._server_task and not self._server_task.done():
                self._server_task.cancel()

            async def _grace():
                await asyncio.sleep(0)
                self._loop.stop()  # type: ignore[union-attr]
            asyncio.create_task(_grace())

        self._loop.call_soon_threadsafe(stop_loop)
        self._thread.join(timeout=5.0)

        self._loop = None
        self._thread = None
        self._server_task = None
        self._started_evt.clear()

    def _get_block_by_name(self, block_name: str) -> ModbusSparseDataBlock:
        if block_name == ModbusSegment.COILS:
            return self.co
        elif block_name == ModbusSegment.DISCRETE_INPUTS:
            return self.di
        elif block_name == ModbusSegment.HOLDING_REGISTERS:
            return self.hr
        elif block_name == ModbusSegment.INPUT_REGISTERS:
            return self.ir
        else:
            raise ValueError(f"Unknown Modbus block name: {block_name}")
        
    @override
    def read_inputs(self, plc_state: PLCState):
        # Update PLC state based on (writable) modbus values
        for tag in plc_state.tags():
            # only process writable tags
            if not tag.writable:
                continue
            
            (addr, block_name) = self.mapping.find(tag.name)
            block = self._get_block_by_name(block_name)

            if tag.datatype == bool:
                bit = self._get_bits(block, addr, 1)[0]
                tag.set(bool(bit))
            # integer: single int from a holding/input register
            elif tag.datatype == int:
                regs = self._get_regs(block, addr, ModbusClientMixin.DATATYPE.INT16.value[1])
                val = ModbusClientMixin.convert_from_registers(regs, ModbusClientMixin.DATATYPE.INT16)
                tag.set(val)
            # float: two registers from holding/input registers
            elif tag.datatype == float:
                regs = self._get_regs(block, addr, ModbusClientMixin.DATATYPE.FLOAT32.value[1])
                val = ModbusClientMixin.convert_from_registers(regs, ModbusClientMixin.DATATYPE.FLOAT32)
                tag.set(val)

    @override
    def write_outputs(self, plc_state: PLCState):
        # Update modbus blocks based on PLC state

        for tag in plc_state.tags():
            (addr, block_name) = self.mapping.find(tag.name)
            block = self._get_block_by_name(block_name)

            # discrete: single bool to a coil/discrete input
            if tag.datatype == bool:
                regs = ModbusClientMixin.convert_to_registers([tag.get()], ModbusClientMixin.DATATYPE.BITS)
                self._set_regs(block, addr, regs)
            # integer: single int to a holding/input register
            elif tag.datatype == int:
                regs = ModbusClientMixin.convert_to_registers(tag.get(), ModbusClientMixin.DATATYPE.INT16)
                self._set_regs(block, addr, regs)
            # float: two registers to holding/input registers
            elif tag.datatype == float:
                # split float into multiple registers
                regs = ModbusClientMixin.convert_to_registers(tag.get(), ModbusClientMixin.DATATYPE.FLOAT32)
                self._set_regs(block, addr, regs)

    def _run_on_loop(self, fn, *args, **kwargs):
        if not self._loop:
            raise RuntimeError("Modbus server loop not running")
        done = threading.Event()
        err: list[BaseException | None] = [None]
        result: list[object | None] = [None]

        def runner():
            try:
                result[0] = fn(*args, **kwargs)
            except BaseException as e:
                err[0] = e
            finally:
                done.set()

        self._loop.call_soon_threadsafe(runner)
        done.wait(timeout=5.0)
        if err[0]:
            raise err[0]
        return result[0]

    def _set_bits(self, block: ModbusSparseDataBlock, addr: int, vals: Sequence[int | bool]):
        self._run_on_loop(block.setValues, addr+1, list(map(int, vals)))

    def _set_regs(self, block: ModbusSparseDataBlock, addr: int, vals: Sequence[int]):
        self._run_on_loop(block.setValues, addr+1, list(vals))

    def _get_bits(self, block: ModbusSparseDataBlock, addr: int, count: int) -> list[int]:
        return self._run_on_loop(block.getValues, addr+1, count) # type: ignore[return-value]

    def _get_regs(self, block: ModbusSparseDataBlock, addr: int, count: int) -> list[int]:
        return self._run_on_loop(block.getValues, addr+1, count) # type: ignore[return-value]
