import os
from bigtree import preorder_iter
from wishlist_axi_node import wishlist_axi_node
from utils import get_logger, log_tree, read_tree
import logging
import random
import socket
import sys
import time


class wishlist_robot(object):
    def __init__(self, log_level=logging.INFO):
        self.logger = get_logger('Wishlist Robot', log_level)
        self.logger.info(f'Starting robot in {socket.gethostname()} using the register tree shown below loaded from {os.getenv("BACKANNOTATED_YAML")}')
        self.tree = read_tree(wishlist_axi_node)
        log_tree(self.tree, self.logger)

    def stress_test(self, nodes=None, N=1000, test_only_rw=True):
        start_time = time.time()
        # Testing the entire tree if nodes is not defined
        if nodes is None:
            nodes = self.tree
        # Making sure only leaves and rw registers are tested
        if test_only_rw:
            nodes = [n for n in nodes if (n.permission == 'rw' and n.is_leaf)]
        for node in nodes:
            self.logger.info(f'Running stress test with node {node.path_name}')
        # Testing all nodes N times
        for i in range(1,N+1):
            # Shuffling nodes (not in-place) order before writing, in-place (random.shuffle) shuffling was causing problems during writing
            nodes = random.sample(nodes, len(nodes))
            for node in nodes:
                # Generating stimulus and writing if register permission is rw
                if node.permission == 'rw':
                    node.stimulus = random.randint(0, 2 ** node.width - 1)
                # Writing stimulus
                node.write(node.stimulus)
            # Shuffling nodes order before reading
            nodes = random.sample(nodes, len(nodes))
            for node in nodes:
                # Reading node
                value = node.read()
                # Checking read value against stimulus for errors
                if value != node.stimulus:
                    node.logger.critical(f'node check error at iteration {i}: {value} (0x{value:08x}), expected: {node.stimulus}')
                    sys.exit()
                node.logger.debug(f'Read value is {value} (0x{value:08x})and stimulus is  {node.stimulus}')
            # Logging status every 100 iterations
            if not i % 1000:
                self.logger.info(f'Stress test iteration {i} out of {N} elapsed {time.time() - start_time} seconds')
        self.logger.info(f'Stress test with {N} iteration finished in {time.time() - start_time} seconds without errors')



if __name__ == '__main__':
    robot = wishlist_robot(log_level=logging.INFO)
    nodes = list(preorder_iter(robot.tree, filter_condition=lambda node: node.is_leaf and 'test_' in node.name))
    robot.stress_test(nodes, N=1000, test_only_rw=False)
