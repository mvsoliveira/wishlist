import logging
from bigtree import yield_tree, Node, nested_dict_to_tree
import os
import yaml


def lsb(n):
    """
    Computes the position of the least significant bit (LSB).
    This is a fast, bitwise operation.
    """
    if n == 0:
        return -1  # Or handle as an error, depending on requirements
    return (n & -n).bit_length() - 1


def word_mask(width):
    """
    Creates a bitmask of a given width.
    """
    return (1 << width) - 1


# Use Python 3.10's int.bit_count() for maximum efficiency.
# Otherwise, bin(n).count('1') is a readable and good alternative.
def popcount(n):
    """
    Counts the number of set bits (1s) in a number.
    """
    return n.bit_count() if hasattr(int, 'bit_count') else bin(n).count('1')


def registers_to_node(address, mask, read_values, bus_width, logger):
    """
    Combines register values into a single node value.
    """
    value = 0
    node_lsb = 0
    # Correct and idiomatic way to iterate over reversed zip object.
    for i, (addr, msk, rdvl) in enumerate(reversed(list(zip(address, mask, read_values)))):
        # Use efficient helper functions for bit manipulation
        word_width = popcount(msk)
        word_lsb = lsb(msk)

        # Use efficient logging format to avoid string formatting overhead
        # when the log level is not DEBUG.
        # logger.debug(
        #     'Shifting up value (0x%x >> %s) from address 0x%x by %s and adding to intermediate sum with value 0x%x. The current word width is %s.',
        #     rdvl, word_lsb, addr, node_lsb, value, word_width
        # )

        value += ((rdvl & msk) >> word_lsb) << node_lsb
        node_lsb += word_width
    return value


def node_to_register(value, address, mask, read_values, bus_width, logger):
    """
    Splits a node value into multiple register values.
    """
    bus_mask = word_mask(bus_width)
    node_lsb = 0
    write_values = []

    # Correct and idiomatic way to iterate over reversed zip object.
    for i, (addr, msk, rdvl) in enumerate(reversed(list(zip(address, mask, read_values)))):
        # Use efficient helper functions for bit manipulation
        word_width = popcount(msk)
        node_word_mask = word_mask(word_width) << node_lsb
        node_word_value = (value & node_word_mask) >> node_lsb
        lsb_pos = lsb(msk)

        # Use efficient logging format
        # logger.debug(
        #     'Word width = %s, node_mask = 0x%x, node_word_value = %s, lsb = %s',
        #     word_width, node_word_mask, node_word_value, lsb_pos
        # )

        bus_word_value = node_word_value << lsb_pos
        word_to_keep = rdvl & (bus_mask - msk)
        combined = bus_word_value | word_to_keep

        # Use efficient logging format for the complex string,
        # moving the f-string formatting logic outside the logger call.
        debug_msg = (
            'W:%s Combining word_to_keep:(0b%s, 0x%x, %s) to bus_word_value: '
            '(0b%s, 0x%x, %s), resulting in combined: (0b%s, 0x%x, %s)'
        )
        # logger.debug(
        #     debug_msg,
        #     i,
        #     format(word_to_keep, f'0{bus_width}b'), word_to_keep, word_to_keep,
        #     format(bus_word_value, f'0{bus_width}b'), bus_word_value, bus_word_value,
        #     format(combined, f'0{bus_width}b'), combined, combined
        # )

        write_values.append(combined)
        node_lsb += word_width
    return write_values[::-1]


def get_logger(name, level, format_string=None):
    """
    Configures and returns a logger.
    """
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    if format_string is None:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    else:
        formatter = logging.Formatter(format_string)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)
    return logger


def read_tree(yaml_file=None, CustomNode=Node):
    """
    Reads a YAML file and converts it to a bigtree tree.
    """
    if yaml_file is None:
        yaml_file = os.getenv("BACKANNOTATED_YAML")

    if not os.path.exists(yaml_file):
        raise FileNotFoundError(f"YAML file not found at: {yaml_file}")

    with open(yaml_file, "r") as stream:
        wishlist_dict = yaml.safe_load(stream)
    return nested_dict_to_tree(wishlist_dict, node_type=CustomNode)


def log_tree(tree, logger):
    """
    Logs the structure of a tree.
    """
    for branch, stem, node in yield_tree(tree):
        attrs = node.describe(exclude_attributes=["name", 'logger', 'bus_width'], exclude_prefix="_")
        attr_str_list = [f"{k}={v}" for k, v in attrs]
        logger.info(f"{branch}{stem}{node.node_name} {attr_str_list}")