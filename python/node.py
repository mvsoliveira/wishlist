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

def read_tree(logger):
    yaml_file = os.getenv("BACKANNOTATED_YAML")
    with open(yaml_file, "r") as stream:
        wishlist_dict = yaml.safe_load(stream)
    tree = nested_dict_to_tree(wishlist_dict)
    logger.info('Testing the following register tree:')
    print_tree(tree, all_attrs=True, style='ansi')
    return tree

async def read(dut,address, mask, cycle):
    return await cycle(dut, address, mask, 1, None)


async def write(dut,address, mask, write_values, cycle):
    return await cycle(dut,address, mask, 0, write_values)


async def read_node(dut, node, bus_width, logger, cycle):
    read_values = await read(dut, node.address, node.mask, cycle)
    value = 0
    node_lsb = 0
    logger.debug(f'Reading values from {node.path_name}, read values: {read_values}')
    for i, (addr, msk, rdvl) in enumerate(reversed(list(zip(node.address, node.mask, read_values)))):
        word_width = int(f'{msk:b}'.count('1'))
        word_lsb = f'{{mask:0{bus_width}b}}'.format(mask=msk)[::-1].find('1')
        logger.debug(
            f'Shifting up value (0x{rdvl:x} >> {word_lsb}) from address 0x{addr:x} by {node_lsb} and adding to intermediate sum with value 0x{value:x}. The current word width is {word_width}.')
        value += (rdvl >> word_lsb) << node_lsb
        node_lsb += word_width # incrementing LSB by word width
    return value

def word_mask(width):
    return (1 << width)-1

async def write_node(dut, node, value, bus_width, logger, cycle):
    # Computing the bus mask
    bus_mask = word_mask(bus_width)
    # Reading all the registers associated with the node with the bus mask
    read_values = await read(dut, node.address, [bus_mask]*len(node.address), cycle)
    # Node LSB (can be higher than bus width)
    node_lsb = 0
    # Empty array of values to be written
    write_values = []
    logger.debug(f'Reading values from {node.path_name}, read values: {read_values}')
    for i, (addr, msk, rdvl) in enumerate(reversed(list(zip(node.address, node.mask, read_values)))):
        # Number of bits used by a given node in the current address offset
        word_width = int(f'{msk:b}'.count('1'))
        # Mask to be used to mask the node value
        node_word_mask = word_mask(word_width) << node_lsb
        # Masking the node value
        node_word_value = (value & node_word_mask) >> node_lsb
        # Computing the MSB for current address offset
        lsb = f'{{mask:0{bus_width}b}}'.format(mask=msk)[::-1].find('1')
        logger.debug(f'Word width = {word_width}, node_mask = 0x{node_word_mask:x}, node_word_value = {node_word_value}, lsb = {lsb}')
        # Computing value to be written not yet masked in order to keep current data in the same address offset
        bus_word_value = node_word_value << lsb
        # Masking data that should be kept
        word_to_keep = rdvl & (bus_mask - msk)
        # Computing value to be written and appending to list
        combined = bus_word_value | word_to_keep
        logger.debug(
            f'W:{i} Combining word_to_keep:(0b{{word_to_keep:0{bus_width}b}}, 0x{word_to_keep:x}, {word_to_keep:d}) to bus_word_value: (0b{{bus_word_value:0{bus_width}b}}, 0x{bus_word_value:x}, {bus_word_value:d}), resulting in combined: (0b{{combined:0{bus_width}b}}, 0x{combined:x}, {combined:d})'.format(
                word_to_keep=word_to_keep, bus_word_value=bus_word_value, combined=combined))
        write_values.append(combined)
        # Incrementing node_lsb
        node_lsb += word_width # incrementing LSB by word width
    # Writing combined data back
    logger.debug(f'Writing the following values {write_values[::-1]}')
    ack = await write(dut, node.address, [bus_mask]*len(node.address), write_values[::-1], cycle)
    return True