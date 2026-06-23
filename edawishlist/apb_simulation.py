"""
APB3 simulation helpers for edawishlist.

Provides an apb_cycle() BFM and APBNode class that mirror the patterns in
wishbone_simulation.py, and a register_test() cocotb entry point for testing
wishlist-generated APB3 address decoders.

APB3 transaction timing (our decoder):
  - SETUP  (psel=1, penable=0): always_ff captures read data on the rising edge
  - ACCESS (psel=1, penable=1): pready fires combinatorially; prdata is the
    value registered at the SETUP edge

The BFM issues one transaction per bus word and takes 3 clock cycles per
transaction (pre-SETUP → SETUP → ACCESS).
"""
import random
import logging

import cocotb

_log = logging.getLogger(__name__)
from bigtree import Node, preorder_iter
from cocotb._bridge import resume
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ReadOnly

from edawishlist.node import read_node, write_node, read_tree
from edawishlist.utils import get_logger


async def apb_cycle(dut, addresses, mask, read_mode, write_values):
    """
    cycle() implementation backed by raw APB3 signal driving.

    Matches the contract expected by node.read_node / node.write_node:
        cycle(dut, addresses, mask, read_mode, write_values)

    One APB transaction (3 clock cycles) is issued per word in *addresses*.
    Reads:  returns list[int] (one masked integer per word).
    Writes: returns True.

    The DUT must expose: pclk_i, psel_i, penable_i, pwrite_i, paddr_i,
    pwdata_i, pstrb_i, prdata_o, pready_o, pslverr_o.
    """
    read_values = []
    for i, addr in enumerate(addresses):
        # ── pre-SETUP: drive signals that the SETUP posedge will capture ──────
        await RisingEdge(dut.pclk_i)
        dut.psel_i.value    = 1
        dut.penable_i.value = 0
        dut.pwrite_i.value  = 0 if read_mode else 1
        dut.paddr_i.value   = addr
        if not read_mode:
            dut.pwdata_i.value = write_values[i]
            dut.pstrb_i.value  = 0xF

        # ── SETUP posedge ──────────────────────────────────────────────────────
        # always_ff captures rd_data = decode(addr) for reads,
        # or wr_err for write address checks.
        await RisingEdge(dut.pclk_i)
        dut.penable_i.value = 1

        # ── ACCESS posedge ─────────────────────────────────────────────────────
        # pready_o = psel && penable (combinatorial) = 1
        # prdata_o = rd_data registered at SETUP posedge (reads)
        await RisingEdge(dut.pclk_i)

        # Release bus in the active phase, before ReadOnly.  prdata_o = rd_data
        # is a registered signal and stays valid regardless of psel state.
        dut.psel_i.value    = 0
        dut.penable_i.value = 0
        dut.pwrite_i.value  = 0

        # Sample after combinatorial logic settles.
        await ReadOnly()
        if read_mode:
            data = dut.prdata_o.value.to_unsigned() & mask[i]
            read_values.append(data)
            data_str = ' '.join(f'{b:02x}' for b in data.to_bytes(4, 'little'))
            _log.info(f'Read  complete addr: 0x{addr:08x} data: {data_str}')
        else:
            data_str = ' '.join(
                f'{b:02x}' for b in int(write_values[i]).to_bytes(4, 'little')
            )
            _log.info(f'Write complete addr: 0x{addr:08x} data: {data_str}')

    return read_values if read_mode else True


class APBNode(Node):
    """
    Node backed by raw APB3 signal driving for cocotb simulations.

    Mirrors WishboneNode from wishbone_simulation.py.  Set the class-level
    'dut' attribute to the cocotb DUT handle inside the test coroutine:

        from edawishlist.apb_simulation import APBNode

        class my_sim_node(APBNode):
            dut = None   # set per-test

        my_sim_node.dut = dut

    Pass the subclass as *base_node* to wishlist_robot and it behaves
    identically to WishboneNode / AxiLiteNode from the software's perspective.
    """
    dut       = None
    bus_width = 32

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.logger = get_logger(self.path_name, logging.INFO)

    def read(self):
        return resume(read_node)(
            self.dut, self, self.bus_width, self.logger, apb_cycle
        )

    def write(self, value):
        if self.permission != 'rw':
            self.logger.critical(
                f'Attempted write to read-only node {self.path_name}'
            )
            raise PermissionError(f'{self.path_name} is read-only')
        return resume(write_node)(
            self.dut, self, value, self.bus_width, self.logger, apb_cycle
        )


async def apb_register_test(dut, logger, tree, clk_period_ns=10):
    """
    Generic read/write stress test for a wishlist APB3 address decoder.

    Drives all rw leaf nodes with random stimuli, then reads them back and
    asserts the returned value matches.  Read-only (r) registers are skipped
    because their status-struct inputs are not driven by this standalone test.

    The clock is started here; the DUT reset (preset_ni active-low) is
    asserted for 5 cycles before traffic begins.
    """
    cocotb.start_soon(Clock(dut.pclk_i, clk_period_ns, unit='ns').start(start_high=False))

    # Initialise bus to idle
    dut.preset_ni.value = 0
    dut.psel_i.value    = 0
    dut.penable_i.value = 0
    dut.pwrite_i.value  = 0
    dut.paddr_i.value   = 0
    dut.pwdata_i.value  = 0
    dut.pstrb_i.value   = 0

    for _ in range(5):
        await RisingEdge(dut.pclk_i)
    dut.preset_ni.value = 1
    await RisingEdge(dut.pclk_i)

    nodes = [n for n in preorder_iter(tree, filter_condition=lambda n: n.is_leaf)
             if n.permission == 'rw']

    for node in random.sample(nodes, len(nodes)):
        node.stimulus = random.randint(0, 2 ** node.width - 1)
        logger.info(f'Writing  {node.path_name} = 0x{node.stimulus:x}')
        await write_node(dut, node, node.stimulus, 32, logger, apb_cycle)

    for node in random.sample(nodes, len(nodes)):
        logger.info(f'Reading  {node.path_name}')
        value = await read_node(dut, node, 32, logger, apb_cycle)
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

    await apb_register_test(dut, logger, tree)
