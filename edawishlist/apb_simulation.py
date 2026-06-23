"""
APB3 simulation helpers for edawishlist.

Provides an apb_cycle() BFM backed by cocotbext-axi ApbMaster and an APBNode
class that mirror the patterns in axilite_simulation.py.  A register_test()
cocotb entry point exercises wishlist-generated APB3 address decoders.

The DUT is expected to use _i/_o port suffixes on the standard APB3 signals:
  pclk_i / preset_ni — clock and active-low reset
  paddr_i  psel_i  penable_i  pwrite_i  pwdata_i  pstrb_i
  prdata_o  pready_o  pslverr_o
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
from cocotbext.axi.apb import ApbBus, ApbMaster

# cocotbext-axi 0.1.28 uses several cocotb 1.x APIs that cocotb 2.0 deprecated.
# Suppress them until the library is updated.
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module=r"cocotbext\.",
)

from edawishlist.node import read_node, write_node, read_tree
from edawishlist.utils import get_logger


class _DutApbBus(ApbBus):
    """ApbBus that maps _i/_o-suffixed DUT ports to standard APB attribute names.

    Passed to ApbMaster so the library drives dut.psel_i, dut.paddr_i, etc.
    without requiring any port-name change in the generated RTL.
    """
    _signals = {
        "paddr":   "paddr_i",
        "psel":    "psel_i",
        "penable": "penable_i",
        "pwrite":  "pwrite_i",
        "pwdata":  "pwdata_i",
        "pstrb":   "pstrb_i",
        "pready":  "pready_o",
        "prdata":  "prdata_o",
    }
    _optional_signals = {
        "pprot":   "pprot_i",
        "pslverr": "pslverr_o",
    }


async def apb_cycle(master, addresses, mask, read_mode, write_values):
    """
    cycle() implementation backed by a cocotbext-axi ApbMaster.

    Matches the contract expected by node.read_node / node.write_node:
        cycle(driver, addresses, mask, read_mode, write_values)

    One APB transaction is issued per word in *addresses*.
    Reads:  returns list[int] (one masked integer per word).
    Writes: returns True.

    Parameters
    ----------
    master       : ApbMaster   — cocotbext.axi bus driver
    addresses    : list[int]   — word-aligned byte addresses
    mask         : list[int]   — per-word read masks
    read_mode    : bool / int  — True → read, False → write
    write_values : list[int] | None  — per-word values (None for reads)
    """
    read_values = []
    for i, addr in enumerate(addresses):
        if read_mode:
            result = await master.read(addr, 4)
            if result.resp != AxiResp.OKAY:
                raise RuntimeError(f'APB read  0x{addr:08X} → {result.resp}')
            integer = int.from_bytes(result.data, 'little')
            read_values.append(integer & mask[i])
        else:
            result = await master.write(
                addr, int(write_values[i]).to_bytes(4, 'little')
            )
            if result.resp != AxiResp.OKAY:
                raise RuntimeError(f'APB write 0x{addr:08X} → {result.resp}')
    return read_values if read_mode else True


class APBNode(Node):
    """
    Node backed by a cocotbext-axi ApbMaster for cocotb simulations.

    Mirrors AxiLiteNode from axilite_simulation.py.  Set the class-level
    'master' attribute to an ApbMaster instance inside the test coroutine:

        from edawishlist.apb_simulation import APBNode

        class my_sim_node(APBNode):
            master = None   # set per-test

        my_sim_node.master = ApbMaster(
            _DutApbBus.from_entity(dut), dut.pclk_i, dut.preset_ni,
            reset_active_level=0,
        )

    Pass the subclass as *base_node* to wishlist_robot and it behaves
    identically to WishboneNode / AxiLiteNode from the software's perspective.
    """
    master    = None
    bus_width = 32

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.logger = get_logger(self.path_name, logging.INFO)

    def read(self):
        return resume(read_node)(
            self.master, self, self.bus_width, self.logger, apb_cycle
        )

    def write(self, value):
        if self.permission != 'rw':
            self.logger.critical(
                f'Attempted write to read-only node {self.path_name}'
            )
            raise PermissionError(f'{self.path_name} is read-only')
        return resume(write_node)(
            self.master, self, value, self.bus_width, self.logger, apb_cycle
        )


async def apb_register_test(dut, logger, tree, master, clk_period_ns=10):
    """
    Generic read/write stress test for a wishlist APB3 address decoder.

    Drives all rw leaf nodes with random stimuli, then reads them back and
    asserts the returned value matches.  Read-only (r) registers are skipped
    because their status-struct inputs are not driven by this standalone test.

    The master argument must be a cocotbext-axi ApbMaster already bound to
    the DUT.  The clock is started here; the DUT reset (preset_ni active-low)
    is asserted for 5 cycles before traffic begins.

    Note: apb_cycle passes *master* as the "dut" argument to read_node /
    write_node — that is intentional, matching the APBNode convention.
    """
    cocotb.start_soon(Clock(dut.pclk_i, clk_period_ns, unit='ns').start(start_high=False))

    dut.preset_ni.value = 0
    for _ in range(5):
        await RisingEdge(dut.pclk_i)
    dut.preset_ni.value = 1
    await RisingEdge(dut.pclk_i)

    nodes = [n for n in preorder_iter(tree, filter_condition=lambda n: n.is_leaf)
             if n.permission == 'rw']

    for node in random.sample(nodes, len(nodes)):
        node.stimulus = random.randint(0, 2 ** node.width - 1)
        logger.info(f'Writing  {node.path_name} = 0x{node.stimulus:x}')
        await write_node(master, node, node.stimulus, 32, logger, apb_cycle)

    for node in random.sample(nodes, len(nodes)):
        logger.info(f'Reading  {node.path_name}')
        value = await read_node(master, node, 32, logger, apb_cycle)
        assert value == node.stimulus, (
            f'{node.path_name}: got 0x{value:x}, expected 0x{node.stimulus:x}')


@cocotb.test()
async def register_test(dut):
    """Read/write stress test for a wishlist APB3 address decoder.

    Driven by BACKANNOTATED_YAML.  Requires the DUT to have pclk_i / preset_ni
    and APB3 slave ports (psel_i, penable_i, pwrite_i, paddr_i, pwdata_i,
    pstrb_i, prdata_o, pready_o, pslverr_o) — the naming convention used by
    the address_decoder_apb.sv.jinja2 template.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    tree = read_tree(logger)

    bus = _DutApbBus.from_entity(dut)
    master = ApbMaster(bus, dut.pclk_i, dut.preset_ni, reset_active_level=0)

    await apb_register_test(dut, logger, tree, master)
