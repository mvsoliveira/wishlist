
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
        value += (rdvl >> word_lsb) << node_lsb
        node_lsb += word_width  # incrementing LSB by word width
    return value


def word_mask(width):
    return (1 << width) - 1


def get_logger(name, level, format=logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')    ):
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    handler.setFormatter(format)
    logger.addHandler(handler)
    logger.setLevel(level)
    return logger

def read_tree(CustomNode=Node):
    yaml_file  = os.getenv("BACKANNOTATED_YAML")
    with open(yaml_file, "r") as stream:
        wishlist_dict = yaml.safe_load(stream)
    return nested_dict_to_tree(wishlist_dict, node_type=CustomNode)

def log_tree(tree,logger):
    for branch, stem, node in yield_tree(tree):
        attrs = node.describe(exclude_attributes=["name", 'logger', 'bus_width'], exclude_prefix="_")
        attr_str_list = [f"{k}={v}" for k, v in attrs]
        logger.info(f"{branch}{stem}{node.node_name} {attr_str_list}")