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
from cocotbext.axi import AxiBus, AxiLiteBus, AxiMaster, AxiLiteMaster, AxiLiteSlave, AxiSlave


@cocotb.coroutine
async def register_test(dut, logger, tree, shufle_order=1):
    """Testing registers"""
    # Configuring clock
    cocotb.start_soon(Clock(dut.S_AXI_ACLK, 2, units="ns").start())
    axi_master = AxiLiteMaster(AxiLiteBus.from_prefix(dut, "S_AXI"), dut.S_AXI_ACLK, dut.S_AXI_ARESETN,
                           reset_active_level=False)
    await cycle_reset(dut.S_AXI_ACLK, dut.S_AXI_ARESETN)

    print('writing date')
    test_data = bytearray([x % 256 for x in range(10)])
    await axi_master.write(0x04, test_data)
    await axi_master.write(0x70000100, test_data)

    for i in range(10):
        await RisingEdge(dut.S_AXI_ACLK)

async def cycle_reset(clk,rst):
    rst.setimmediatevalue(1)
    await RisingEdge(clk)
    await RisingEdge(clk)
    rst.value = 0
    await RisingEdge(clk)
    await RisingEdge(clk)
    rst.value = 1
    await RisingEdge(clk)
    await RisingEdge(clk)




#if __name__ == '__main__':
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
#tree = read_tree(logger)
tree = None
# Factory of tests
factory = TestFactory(register_test)
factory.add_option("shufle_order", [False])
factory.add_option("logger", [logger])
factory.add_option("tree", [tree])
factory.generate_tests()



