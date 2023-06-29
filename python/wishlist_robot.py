import yaml
import os
from bigtree import nested_dict_to_tree, tree_to_nested_dict, print_tree, postorder_iter, preorder_iter, Node, \
    yield_tree
from example_custom_node import AXINode as CustomNode
from utils import get_logger, log_tree, read_tree
import logging
import random
import socket
import sys


class wishlist_robot(object):
    def __init__(self):
        self.logger = get_logger('Wishlist Robot', logging.DEBUG)
        self.logger.info(f'Starting robot in {socket.gethostname()} using the register tree shown below loaded from {os.getenv("BACKANNOTATED_YAML")}')
        self.tree = read_tree(CustomNode)
        log_tree(self.tree, self.logger)

    def stress_test(self, nodes=None, N=1000):
        # Testing the entire tree if nodes is not defined
        if nodes is None:
            nodes = self.tree
        # Making sure only leaves and rw registers are tested
        nodes = [n for n in nodes if (n.permission == 'rw' and n.is_leaf)]
        # Testing all nodes N times
        for i in range(N):
            for node in nodes:
                # Generating stimulus
                stimulus = random.randint(0, 2 ** node.width - 1)
                # Writing stimulus
                node.write_node(stimulus)
                # Reading node
                value = node.read_node()
                # Checking read value against stimulus for errors
                if value != stimulus:
                    node.logger.critical(f'node check error at iteration {i}: {value} (0x{value:08x}), expected: {stimulus}')
                    sys.exit()
                node.logger.debug(f'{value} (0x{value:08x}) {stimulus}')
            # Logging status every 100 iterations
            if not i % 100:
                robot.logger.info(f'Stress_test iteration {i+1} out of {N}')


if __name__ == '__main__':
    robot = wishlist_robot()
    nodes = list(preorder_iter(robot.tree, filter_condition=lambda node: node.is_leaf and node.permission == 'rw' and 'PB_' in node.name))
    robot.stress_test(nodes,N=10000)
