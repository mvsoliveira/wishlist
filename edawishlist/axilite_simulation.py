import os
import yaml
from bigtree import nested_dict_to_tree, preorder_iter, print_tree
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ReadOnly
from cocotb.regression import TestFactory
import random
from operator import attrgetter
import cocotb
import logging
from cocotbext.axi import AxiBus, AxiLiteBus, AxiMaster, AxiLiteMaster, AxiLiteSlave, AxiSlave, AxiResp
from edawishlist.rtl_simulation import read_tree, write_node, read_node
from edawishlist.node import write, word_mask


async def cycle(axi_master, address, mask, read_mode, write_values):
    read_values = []
    # Iterating for one clock cycle more than the number of words in the node because address decoder outputs is registered
    # Also delaying mask for one iteration because the mask is needed in the iteration i+1
    for i, (addr, msk) in enumerate(zip(address, mask)):
        # Write Stage of the clock cycle
        if not read_mode:
            bytes = int(write_values[i]).to_bytes(4, byteorder='little')
            # unpacking write response, user is returned only with AXI and not AXI lite
            (address_resp, length, resp, *user) = await axi_master.write(addr, bytes)
        else:
            # unpacking read response, user is returned only with AXI and not AXI lite
            (address_resp, data, resp, *user) = await axi_master.read(addr, 4)
            integer = int.from_bytes(data, byteorder='little', signed=False)
            read_values.append(integer & msk)
        if resp != AxiResp.OKAY:
            raise Exception(f'AXI transfer with read_mode = {read_mode}, addr= {addr} returned response code {resp}')
    if read_mode:
        return read_values
    else:
        return True


@cocotb.coroutine
async def axlite_test(dut, axi_master, bus_width, logger, nodes, shufle_order):
    # Writing stimullus
    if shufle_order: random.shuffle(nodes)
    for node in nodes:
        path = node.path_name.lower().split('/')
        if node.permission == 'rw':
            logger.info(f'Writing stimulus for {node.path_name}')
            node.stimulus = random.randint(0, 2 ** node.width - 1)
            ack = await write_node(axi_master, node, node.stimulus, bus_width, logger, cycle)

    # Checking stimulus
    if shufle_order: random.shuffle(nodes)
    for node in nodes:
        logger.info(f'Checking node: {node.path_name}, permission: {node.permission}')
        node_value = await read_node(axi_master, node, bus_width, logger, cycle)
        logger.debug(f'Stimulus = {node.stimulus}, actual= {node_value}')
        assert node.stimulus == node_value, f'Actual data for Node {node.path_name} {node_value} is different than applied stimulus {node.stimulus}'


@cocotb.coroutine
async def axi_initialization(axi_master, bus_width, logger, nodes):
    logger.info(
        "Initializing rw registers with zeroes, this is needed because the aurora serial stream output is unknown when unititialized registers values are propagated to the core. This causes soft errors to be detected which ultimately causes a calibration error in aurora during simulation. One can't address this situation in the testbench because the unresolved values are causing the issue inside of the DUT, i.e. the Aurora core. This is not need while running in the target because unknown values are propagated as zeroes or random values within the DUT.")
    bus_mask = word_mask(bus_width)
    for node in nodes:
        if node.permission == 'rw':
            logger.info(f'Initializing node: {node.path_name}, permission: {node.permission}')
            ack = await write(axi_master, node.address, [bus_mask] * len(node.address), [0] * len(node.address), cycle)


@cocotb.coroutine
async def register_test(dut, logger, tree, shufle_order=1):
    """Testing registers"""
    # Configuring clock
    cocotb.start_soon(Clock(dut.S_AXI_ACLK, 2, units="ns").start())
    axilite_master = AxiLiteMaster(AxiLiteBus.from_prefix(dut, "S_AXI"), dut.S_AXI_ACLK, dut.S_AXI_ARESETN,
                                   reset_active_level=False)

    bus_width = len(dut.Bus2IP_Data)
    await cycle_reset(dut.S_AXI_ACLK, dut.S_AXI_ARESETN)
    # Extracting tree of nodes
    nodes = list(preorder_iter(tree, filter_condition=lambda node: node.is_leaf))
    # axlite tester
    await axi_initialization(axilite_master, bus_width, logger, nodes)
    await axlite_test(dut, axilite_master, bus_width, logger, nodes, shufle_order)


async def cycle_reset(clk, rst):
    rst.setimmediatevalue(1)
    await RisingEdge(clk)
    await RisingEdge(clk)
    rst.value = 0
    await RisingEdge(clk)
    await RisingEdge(clk)
    rst.value = 1
    await RisingEdge(clk)
    await RisingEdge(clk)


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    tree = read_tree(logger)
    # Factory of tests
    factory = TestFactory(register_test)
    factory.add_option("shufle_order", [False, True, True, True, True])
    factory.add_option("logger", [logger])
    factory.add_option("tree", [tree])
    factory.generate_tests()
