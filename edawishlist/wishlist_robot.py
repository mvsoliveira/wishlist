import os
from bigtree import preorder_iter, find_name
from edawishlist.wishlist_axi_node import wishlist_axi_node
from edawishlist.utils import get_logger, log_tree, read_tree
import logging
import random
import socket
import sys
import time
import pandas as pd
from pathlib import Path
from datetime import datetime
from pytz import timezone


class wishlist_robot(object):
    def __init__(self, yaml_file=None, log_level=logging.INFO):
        self.logger = get_logger('Wishlist Robot', log_level)
        self.logger.info(f'Starting robot in {socket.gethostname()} using the register tree shown below loaded from {os.getenv("BACKANNOTATED_YAML")}')
        self.tree = read_tree(yaml_file,wishlist_axi_node)
        log_tree(self.tree, self.logger)

    def stress_test(self, nodes=None, N=1000, test_only_rw=False):
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

    def launch_online_monitoring(self, monitored_nodes, clear_load_node, time_reference_node, timer_node, display=True, save=True, base_path='/software/tmp'):
        Path(f'{base_path}').mkdir(parents=True, exist_ok=True)
        accumulators_df = pd.DataFrame({'Value': [0] * len(monitored_nodes)},
                                       index=[node.name for node in monitored_nodes])
        i = 0
        save_df_list = []
        while True:
            try:
                # Waiting for reference to reach desired time period
                while timer_node.read() < 500e6:
                    time.sleep(0.1)
                clear_load_node.write(1)
                clear_load_node.write(0)
                time_reference = time_reference_node.read()
                if time_reference == (1 << time_reference_node.width) - 1:
                    self.logger.warning(f'Online monitoring iteration {i} has been discarded because time reference value is saturated.')
                else:
                    now = datetime.now(timezone('Europe/Paris'))
                    save_dict = {'time_reference': time_reference}
                    for node in monitored_nodes:
                        value = node.read()
                        rate = node.convert(value=value, reference=time_reference, parameter="conversion",)
                        if display:
                            representation = node.convert(value=value, rate=rate, parameter="representation")
                            accumulators_df.loc[
                                node.name, 'Value'] = f'{representation}'
                        if save:
                            save_dict[node.name] = rate

                    if display:
                        # Generating string before clearing the screen to avoid flickering
                        #df_str = accumulators_df.loc[['clk' in i for i in accumulators_df.index],:].to_string(col_space=30)
                        df_str = accumulators_df.to_string(col_space=30)
                    if save:
                        save_df = pd.DataFrame(save_dict, index=[now])
                        save_df_list.append(save_df)
                        if not i % 20:
                            save_dfs = pd.concat(save_df_list)
                            now_str = f'{now}'.replace(' ','_')
                            filename = f'{base_path}/online_monitoring_data_{now_str}.pickle'
                            save_dfs.to_pickle(filename)
                            self.logger.info(f'Iteration {i} - saved file {filename} ')
                            save_df_list = []
                    if display:
                        os.system('clear')
                        self.logger.info(f'Iteration {i} - {now} - refresh time: {time_reference * 10e-9} seconds ')
                        print(df_str)
                i += 1
            except KeyboardInterrupt:
                sys.exit()


if __name__ == '__main__':
    robot = wishlist_robot(yaml_file='../firmware/l1calogfex_backannotated.yaml', log_level=logging.INFO)
    nodes = list(preorder_iter(robot.tree, filter_condition=lambda node: node.is_leaf))
    for node in nodes:
        robot.logger.info(f'{node.path_name}: 0x{node.read():x}')
    nodes = list(preorder_iter(robot.tree, filter_condition=lambda node: node.is_leaf and 'test_' in node.name))
    robot.stress_test(nodes, N=10)
    robot.logger.info(f"Init status {find_name(robot.tree,'INIT_STAT').read():08x}")
    monitored_nodes = list(
        preorder_iter(robot.tree, filter_condition=lambda node: (node.is_leaf and node.permission == 'r') and (
                    '/monitoring/' in node.path_name or 'INIT_STAT' in node.name)))
    clear_load_node = find_name(robot.tree, 'clear_load')
    time_reference_node = find_name(robot.tree, 'ps_sys_clk')
    timer_node = find_name(robot.tree, 'ps_sys_clk_no_shadow')
    robot.launch_online_monitoring(monitored_nodes=monitored_nodes,
                                   clear_load_node=clear_load_node,
                                   time_reference_node=time_reference_node,
                                   timer_node=timer_node,
                                   display=False)






