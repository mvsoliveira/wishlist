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
from node import read_tree, read_node, write_node


async def cycle(dut, address, mask, read_mode, write_values):
    read_values = []
    # Iterating for one clock cycle more than the number of words in the node because address decoder outputs is registered
    # Also delaying mask for one iteration because the mask is needed in the iteration i+1 
    for i, (addr, msk) in enumerate(zip(address+[None],[None]+mask)):
        await RisingEdge(dut.clk_i)
        # Write Stage of the clock cycle 
        if i < len(address):
           dut.read_i.value = bool(read_mode)
           dut.write_i.value = not(bool(read_mode))
           dut.address_i.value = addr
           if not read_mode:
               dut.data_i.value = write_values[i]
        else:
           dut.read_i.value = 0
           dut.write_i.value = 0
        # Read stage of the clock cycle
        if read_mode:
            await ReadOnly()
            if i > 0:
                read_values.append(dut.data_o.value.integer & msk)
    if read_mode:
        return read_values
    else:
        return True


@cocotb.coroutine
async def register_test(dut, logger, tree, shufle_order=1):
    """Testing registers"""
    # Configuring clock
    clock = Clock(dut.clk_i, 10, units="ns")  # Create a 10ns period clock on port clk
    cocotb.start_soon(clock.start(start_high=False)) # Start the clock. Start it low to avoid issues on the first RisingEdge

    # Initializing contr78ol signals
    dut.read_i.value = 0
    dut.write_i.value = 0
    dut.data_i.value = 0
    dut.address_i.value = 0
    bus_width = len(dut.data_i)

    # Extracting tree of nodes
    nodes = list(preorder_iter(tree, filter_condition=lambda node: node.is_leaf))

    # Writing stimullus
    if shufle_order: random.shuffle(nodes)
    for node in nodes:
        logger.info(f'Writing stimulus for {node.path_name}')
        node.stimulus = random.randint(0,2**node.width-1)
        path = node.path_name.lower().split('/')
        if node.permission == 'r':
            signal = attrgetter(f"{path[1]}_status_i.{'.'.join(path[2:])}")(dut)
            signal.value = node.stimulus
        else:
            ack = await write_node(dut,node,node.stimulus, bus_width, logger, cycle)

    # Checking stimulus
    if shufle_order: random.shuffle(nodes)
    for node in nodes:
        logger.info(f'Checking node: {node.path_name}, permission: {node.permission}')
        node_value = await read_node(dut, node, bus_width, logger, cycle)
        logger.debug(f'Stimulus = {node.stimulus}, actual= {node_value}')
        assert node.stimulus == node_value, f'Actual data for Node {node.path_name} {node_value} is different than applied stimulus {node.stimulus}'




#if __name__ == '__main__':
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
tree = read_tree(logger)
# Factory of tests
factory = TestFactory(register_test)
factory.add_option("shufle_order", [False, True, True, True, True])
factory.add_option("logger", [logger])
factory.add_option("tree", [tree])
factory.generate_tests()



