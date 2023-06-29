import yaml
import os
from bigtree import nested_dict_to_tree, tree_to_nested_dict, print_tree, postorder_iter, preorder_iter, Node, \
    yield_tree
from example_custom_node import AXINode as CustomNode
from utils import get_logger, log_tree, read_tree
import logging
import random
import socket


class wishlist_robot(object):
    def __init__(self):
        self.logger = get_logger('Wishlist Robot', logging.INFO)
        self.logger.info(f'Starting robot in {socket.gethostname()} using the register tree shown below loaded from {os.getenv("BACKANNOTATED_YAML")}')
        self.tree = read_tree(CustomNode)
        log_tree(self.tree, self.logger)

    def stress_test(self, nodes=None, N=100):
        if nodes is None:
            nodes = self.tree
        # Making sure only leaves and rw registers are tested
        nodes = [n for n in nodes if (n.permission == 'rw' and n.is_leaf)]
        for i in range(N):
            for node in nodes:
                node.stimulus = random.randint(0, 2 ** node.width - 1)
                node.write(node.stimulus)
                value = node.read_node()
                if value != node.stimulus:
                    node.logger.error('register error: {node.path_name}: {value} (0x{value:08x}) {node.stimulus}')
                node.logger.debug(f'{value} (0x{value:08x}) {node.stimulus}')
            robot.logger.info(f'stress_test {i+1} out of {N}')


if __name__ == '__main__':
    robot = wishlist_robot()
    nodes = list(preorder_iter(robot.tree, filter_condition=lambda node: node.is_leaf and node.permission == 'rw' and 'PB_' in node.name))
    robot.stress_test(nodes)
