"""
AXI4-Lite simulation helpers for edawishlist.

Mirrors wishbone_simulation.py but drives a cocotbext-axi AxiLiteMaster
instead of a raw wishbone-style bus.  The software layer (wishlist_robot,
xmem.py, etc.) is entirely bus-agnostic: only the node class changes.
"""
import random
import logging
import warnings

import cocotb
from bigtree import Node, preorder_iter
from cocotb._bridge import resume
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotbext.axi import AxiResp

# cocotbext-axi 0.1.28 uses several cocotb 1.x APIs that cocotb 2.0 deprecated
# (Event.set(data), handle.set(), signal.value_change, ...).  Suppress all of
# them until the library is updated.
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module=r"cocotbext\.",
)

from edawishlist.node import read_node, write_node, read_tree
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


async def axilite_register_test(dut, logger, tree, master, clk_period_ns=10):
    """
    Generic read/write stress test for a wishlist AXI4-Lite address decoder.

    Drives all rw leaf nodes with random stimuli, then reads them back and
    asserts the returned value matches.  Read-only (r) registers are skipped
    because their status-struct inputs are not driven by this standalone test.

    The master argument must be a cocotbext-axi AxiLiteMaster already bound to
    the DUT.  The clock is started here; the DUT reset (rst_ni active-low) is
    asserted for 5 cycles before traffic begins.

    Note: axilite_cycle passes *master* as the "dut" argument to read_node /
    write_node — that is intentional, matching the AxiLiteNode convention.
    """
    cocotb.start_soon(Clock(dut.clk_i, clk_period_ns, unit='ns').start(start_high=False))

    dut.rst_ni.value = 0
    for _ in range(5):
        await RisingEdge(dut.clk_i)
    dut.rst_ni.value = 1
    await RisingEdge(dut.clk_i)

    nodes = [n for n in preorder_iter(tree, filter_condition=lambda n: n.is_leaf)
             if n.permission == 'rw']

    for node in random.sample(nodes, len(nodes)):
        node.stimulus = random.randint(0, 2 ** node.width - 1)
        logger.info(f'Writing  {node.path_name} = 0x{node.stimulus:x}')
        await write_node(master, node, node.stimulus, 32, logger, axilite_cycle)

    for node in random.sample(nodes, len(nodes)):
        logger.info(f'Reading  {node.path_name}')
        value = await read_node(master, node, 32, logger, axilite_cycle)
        assert value == node.stimulus, (
            f'{node.path_name}: got 0x{value:x}, expected 0x{node.stimulus:x}')


@cocotb.test()
async def register_test(dut):
    """Read/write stress test for a wishlist AXI4-Lite address decoder.

    Driven by BACKANNOTATED_YAML.  Requires the DUT to have clk_i / rst_ni
    and AXI4-Lite slave ports prefixed with s_axil_ (the naming convention
    used by the address_decoder_axilite.sv.jinja2 template).
    """
    from cocotbext.axi import AxiLiteBus, AxiLiteMaster

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    tree = read_tree(logger)

    master = AxiLiteMaster(
        AxiLiteBus.from_prefix(dut, 's_axil'),
        dut.clk_i,
        dut.rst_ni,
        reset_active_level=0,
    )

    await axilite_register_test(dut, logger, tree, master)
