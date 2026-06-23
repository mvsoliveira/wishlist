"""
AXI4-Lite simulation helpers for edawishlist.

Mirrors wishbone_simulation.py but drives a cocotbext-axi AxiLiteMaster
instead of a raw wishbone-style bus.  The software layer (wishlist_robot,
xmem.py, etc.) is entirely bus-agnostic: only the node class changes.
"""
import logging
import warnings

from bigtree import Node
from cocotb._bridge import resume
from cocotbext.axi import AxiResp

# cocotbext-axi 0.1.28 uses several cocotb 1.x APIs that cocotb 2.0 deprecated
# (Event.set(data), handle.set(), signal.value_change, ...).  Suppress all of
# them until the library is updated.
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module=r"cocotbext\.",
)

from edawishlist.node import read_node, write_node
from edawishlist.utils import get_logger


async def axilite_cycle(master, addresses, mask, read_mode, write_values):
    """
    cycle() implementation backed by a cocotbext-axi AxiLiteMaster.

    Matches the contract expected by node.read_node / node.write_node:
        cycle(driver, addresses, mask, read_mode, write_values)

    One AXI4-Lite transaction is issued per word in *addresses*.
    Reads:  returns list[int] (one masked integer per word).
    Writes: returns True.

    Parameters
    ----------
    master       : AxiLiteMaster  — cocotbext.axi bus driver
    addresses    : list[int]      — word-aligned byte addresses
    mask         : list[int]      — per-word read masks
    read_mode    : bool / int     — True → read, False → write
    write_values : list[int] | None  — per-word values (None for reads)
    """
    read_values = []
    for i, addr in enumerate(addresses):
        if read_mode:
            result = await master.read(addr, 4)
            if result.resp != AxiResp.OKAY:
                raise RuntimeError(
                    f'AXI-Lite read  0x{addr:08X} → {result.resp}'
                )
            integer = int.from_bytes(result.data, 'little')
            read_values.append(integer & mask[i])
        else:
            result = await master.write(
                addr, int(write_values[i]).to_bytes(4, 'little')
            )
            if result.resp != AxiResp.OKAY:
                raise RuntimeError(
                    f'AXI-Lite write 0x{addr:08X} → {result.resp}'
                )
    return read_values if read_mode else True


class AxiLiteNode(Node):
    """
    Node backed by a cocotbext-axi AxiLiteMaster for cocotb simulations.

    Mirrors WishboneNode from wishbone_simulation.py.  Set the class-level
    'master' attribute to an AxiLiteMaster instance inside the test coroutine:

        from cocotbext.axi import AxiLiteBus, AxiLiteMaster
        from edawishlist.axilite_simulation import AxiLiteNode

        class my_sim_node(AxiLiteNode):
            master = None   # set per-test

        my_sim_node.master = AxiLiteMaster(
            AxiLiteBus.from_prefix(dut, "pcie"), dut.clk, dut.rst_n,
            reset_active_level=0,
        )

    Pass the subclass as *base_node* to wishlist_robot and it behaves
    identically to WishboneNode from the software's perspective.
    """
    master    = None
    bus_width = 32

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.logger = get_logger(self.path_name, logging.INFO)

    def read(self):
        return resume(read_node)(
            self.master, self, self.bus_width, self.logger, axilite_cycle
        )

    def write(self, value):
        if self.permission != 'rw':
            self.logger.critical(
                f'Attempted write to read-only node {self.path_name}'
            )
            raise PermissionError(f'{self.path_name} is read-only')
        return resume(write_node)(
            self.master, self, value, self.bus_width, self.logger, axilite_cycle
        )
