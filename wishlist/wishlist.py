import pandas
import pandas as pd
from bigtree import nested_dict_to_tree, print_tree, postorder_iter, preorder_iter
import yaml
import logging
from jinja2 import Environment, FileSystemLoader
import numpy as np
from memory import memory, get_register_bits_lists
import json

def attr_in_family(node, attr, value):
    for n in (node,) + node.children:
        if hasattr(n, attr):
            if value in getattr(n, attr):
                return True
    return False
def attr_in_children(node, attr, value):
    for n in node.children:
        if hasattr(n, attr):
            if value == getattr(n, attr):
                return True
    return False

def get_full_name(node):
    return node.path_name[1:].replace('/','_')

class wishlist(memory):
    def __init__(self, wishlist_file):
        self.tree = None
        self.wishlist_file = wishlist_file
        self.read_input_file()
        self.write_yaml_file(self.wishlist_dict,'../examples/whishlist_parsed_input.yaml')
        self.create_tree()
        self.computing_width()
        print_tree(self.tree, attr_list=['address', 'mask', 'width', 'length', 'permission'])
        self.set_jinja_environment()
        self.generate_vhdl_package_file()
        # starting memory object
        super().__init__(start=self.tree.address, end=self.tree.address + self.tree.address_size - 1,
                         width=self.tree.address_width, increment=self.tree.address_increment)
        # Allocation
        self.address_decoder_list = []
        for node in self.register_nodes_iter():
            self.allocate(node)
        pd.concat(self.address_decoder_list).to_html('address_decoder.htm')
        self.update_style()
        self.save_space_styled()

    def read_input_file(self):
        with open(self.wishlist_file, "r") as stream:
            try:
                self.wishlist_dict = yaml.safe_load(stream)
            except yaml.YAMLError:
                logging.exception(f'Error while reading {self.wishlist_file}.')

    def write_yaml_file(self, dictionary, filename):
        with open(filename, 'w') as file:
            yaml.dump(dictionary, file)

    def create_tree(self):
        self.tree = nested_dict_to_tree(self.wishlist_dict)

    def register_nodes_iter(self):
        return preorder_iter(self.tree, filter_condition=lambda node: node.is_leaf)

    def hierarchical_nodes_iter(self):
        return postorder_iter(self.tree, filter_condition=lambda node: not node.is_leaf)

    def computing_width(self):
        for node in self.register_nodes_iter():
            if hasattr(node, 'mask'):
                mask_str = f'{node.mask:b}'
                diff = np.diff([int(s) for s in mask_str])
                if len(diff[diff != 0]) > 1:
                    raise Exception(f'The specified mask=0b{mask_str} for node {node.path_name} is asserted high in a non-contiguous bit interval. Currently, whishlist does not suport this use case, i.e. all the mask bits asserted high have to be grouped together.')
                width = int(mask_str.count('1'))
                if hasattr(node, 'width'):
                    if node.width != width:
                        raise Exception(f'Both mask and width have been defined for {node.path_name}. However the width computed from the mask={width} is different than the specified width={node.width}.')
                else:
                    node.width = width
            elif not hasattr(node, 'width'):
                raise Exception(
                    f'Node {node.path_name} has no width or mask specified. One of them is required, and if both are defined, the mask value gets priority over the width as it enforces the bit position in the address offset. Nevertheless, the provided width is still checked against the provided mask for consistency checking.')


    def allocate(self, node):
        if hasattr(node,'address'):
            smart = False
            if hasattr(node, 'mask'):
                msb = self.tree.address_width-1-f'{{mask:0{self.tree.address_width}b}}'.format(mask=node.mask).find('1')
                self.set_bit_cursor(msb)
            else:
                if self.address != node.address:
                    self.set_bit_cursor(self.tree.address_width-1)
            self.set_address_cursor(node.address)
        else:
            smart = True
        # Allocating
        address_list, address_bits_lists = self.allocate_from_width(width=node.width, name=node.path_name, permission=node.permission, smart=smart)
        # creating respective dataframe and appending to the address_decoder_list
        self.address_decoder_list.append(pd.DataFrame({
            'name': [node.path_name]*len(address_list),
            'permission': [node.permission]*len(address_list),
            'address_list': address_list,
            'address_bits_lists': address_bits_lists,
            'register_bits_lists': get_register_bits_lists(address_list, address_bits_lists, node.width),
        }))



    def set_jinja_environment(self):
        self.environment = Environment(loader=FileSystemLoader("../templates/"))
        self.environment.globals['attr_in_children'] = attr_in_children
        self.environment.globals['attr_in_family'] = attr_in_family
        self.environment.globals['get_full_name'] = get_full_name

    def generate_vhdl_package_file(self):
        template = self.environment.get_template("vhdl_package.jinja2")
        filename = f"{self.wishlist_dict['firmware_path']}/{self.wishlist_dict['name']}_pkg.vhd"
        content = template.render(self.wishlist_dict,
                                  registers=list(self.register_nodes_iter()),
                                  hierarchies=list(self.hierarchical_nodes_iter())
                                  )
        with open(filename, mode="w") as message:
            message.write(content)



if __name__ == '__main__':
    obj = wishlist('../examples/L1CaloGfex.yaml')
