import os
import yaml
from bigtree import nested_dict_to_tree, preorder_iter
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ReadOnly
import random
from operator import attrgetter
import cocotb


def read_tree():
    yaml_file = os.getenv("BACKANNOTATED_YAML")
    with open(yaml_file, "r") as stream:
        wishlist_dict = yaml.safe_load(stream)
    tree = nested_dict_to_tree(wishlist_dict)
    #print_tree(tree, style='ansi')
    return tree


async def cycle(dut,node,read_mode,write_values):
    read_values = []
    # Iterating for one clock cycle more than the number of words in the node because address decoder outputs is registered
    # Also delaying mask for one iteration because the mask is needed in the iteration i+1 
    for i, (addr, mask) in enumerate(zip(node.address+[None],[None]+node.mask)):
        await RisingEdge(dut.clk_i)
        # Write Stage of the clock cycle 
        if i < len(node.address):
           dut.read_i.value = bool(read_mode)
           dut.write_i.value = not(bool(read_mode))
           dut.address_i.value = addr
           if not read_mode:
               dut.data_i = write_values[i]
        else:
           dut.read_i.value = 0
           dut.write_i.value = 0
        # Read stage of the clock cycle
        if read_mode:
            await ReadOnly()
            if i > 0:
                read_values.append(dut.data_o.value.integer & mask)
    if read_mode:
        return read_values
    else:
        return True


async def read(dut,node):
    return await cycle(dut,node,1,None)


async def write(dut,node, write_values):
    return await cycle(dut,node,0,write_values)


@cocotb.test()
async def register_test(dut):
    """Testing registers"""
    # Configuring clock
    clock = Clock(dut.clk_i, 10, units="ns")  # Create a 10ns period clock on port clk
    cocotb.start_soon(clock.start(start_high=False)) # Start the clock. Start it low to avoid issues on the first RisingEdge

    # Initializing control signals
    dut.read_i.value = 0
    dut.write_i.value = 0
    dut.data_i.value = 0
    dut.address_i.value = 0
    
    # Writing stimullus
    tree = read_tree()
    nodes = list(preorder_iter(tree, filter_condition=lambda node: node.is_leaf))
    random.shuffle(nodes)
    for node in nodes:
        node.stimulus = random.randint(0,2**node.width-1)
        path = node.path_name.lower().split('/')
        if node.permission == 'r':
            signal = attrgetter(f"{path[1]}_status_i.{'.'.join(path[2:])}")(dut)
            signal.value = node.stimulus
        else:
            ack = await write(dut,node,[node.stimulus])
            
    # Checking stimulus
    random.shuffle(nodes)
    for node in nodes:
        if node.width == 32:
            actual = await read(dut,node)
            print(node.stimulus,actual[0],node.permission,node.path_name)
            assert node.stimulus == actual[0], f'Actual data for Node {node.path_name} {actual[0]} is different than applied stimulus {node.stimulus}'

