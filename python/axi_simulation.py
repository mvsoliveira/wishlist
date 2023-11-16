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


@cocotb.coroutine
async def register_test(dut, logger, tree, shufle_order=1):
    """Testing registers"""
    # Configuring clock
    clock = Clock(dut.clk_i, 10, units="ns")  # Create a 10ns period clock on port clk
    cocotb.start_soon(clock.start(start_high=False)) # Start the clock. Start it low to avoid issues on the first RisingEdge




#if __name__ == '__main__':
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
#tree = read_tree(logger)
tree = None
# Factory of tests
factory = TestFactory(register_test)
factory.add_option("shufle_order", [False, True, True, True, True])
factory.add_option("logger", [logger])
factory.add_option("tree", [tree])
factory.generate_tests()



