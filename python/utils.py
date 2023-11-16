
import logging
from bigtree import yield_tree, Node, nested_dict_to_tree
import os
import yaml


def registers_to_node(address, mask, read_values, bus_width, logger):
    value = 0
    node_lsb = 0
    for i, (addr, msk, rdvl) in enumerate(reversed(list(zip(address, mask, read_values)))):
        word_width = int(f'{msk:b}'.count('1'))
        word_lsb = f'{{mask:0{bus_width}b}}'.format(mask=msk)[::-1].find('1')
        logger.debug(
            f'Shifting up value (0x{rdvl:x} >> {word_lsb}) from address 0x{addr:x} by {node_lsb} and adding to intermediate sum with value 0x{value:x}. The current word width is {word_width}.')
        value += ((rdvl & msk) >> word_lsb) << node_lsb
        node_lsb += word_width  # incrementing LSB by word width
    return value

def node_to_register(value, address, mask, read_values, bus_width, logger):
    # Computing the bus mask
    bus_mask = word_mask(bus_width)
    # Node LSB (can be higher than bus width)
    node_lsb = 0
    # Empty array of values to be written
    write_values = []
    for i, (addr, msk, rdvl) in enumerate(reversed(list(zip(address, mask, read_values)))):
        # Number of bits used by a given node in the current address offset
        word_width = int(f'{msk:b}'.count('1'))
        # Mask to be used to mask the node value
        node_word_mask = word_mask(word_width) << node_lsb
        # Masking the node value
        node_word_value = (value & node_word_mask) >> node_lsb
        # Computing the MSB for current address offset
        lsb = f'{{mask:0{bus_width}b}}'.format(mask=msk)[::-1].find('1')
        logger.debug(
            f'Word width = {word_width}, node_mask = 0x{node_word_mask:x}, node_word_value = {node_word_value}, lsb = {lsb}')
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
        node_lsb += word_width  # incrementing LSB by word width
        # Returning reversed vector, because write values is appended using a for loop in reverse order
        # This way the loop start by the least-significant word. However, the memory mapped allocation places
        # the most significant word first, i.e. at the first address offset of the node
    return write_values[::-1]

def lsb(n):
    return (n & -n).bit_length() - 1
def word_mask(width):
    return (1 << width) - 1


def get_logger(name, level, format=logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')    ):
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    handler.setFormatter(format)
    logger.addHandler(handler)
    logger.setLevel(level)
    return logger

def read_tree(yaml_file=None, CustomNode=Node):
    if yaml_file is None:
        yaml_file  = os.getenv("BACKANNOTATED_YAML")
    with open(yaml_file, "r") as stream:
        wishlist_dict = yaml.safe_load(stream)
    return nested_dict_to_tree(wishlist_dict, node_type=CustomNode)

def log_tree(tree,logger):
    for branch, stem, node in yield_tree(tree):
        attrs = node.describe(exclude_attributes=["name", 'logger', 'bus_width'], exclude_prefix="_")
        attr_str_list = [f"{k}={v}" for k, v in attrs]
        logger.info(f"{branch}{stem}{node.node_name} {attr_str_list}")