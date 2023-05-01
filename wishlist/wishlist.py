import pandas
import pandas as pd
from bigtree import nested_dict_to_tree, print_tree, postorder_iter, preorder_iter, Node, shift_nodes
import yaml
import logging
from jinja2 import Environment, FileSystemLoader
import numpy as np
from memory import memory, get_register_bits_lists
from copy import deepcopy
import re
import json
from report import formatting

def attr_in_family(node, attr, value):
    for n in preorder_iter(node):
        if hasattr(n, attr):
            if value == getattr(n, attr):
                return True
    return False
def attr_in_children(node, attr, value):
    for n in preorder_iter(node.children):
        if hasattr(n, attr):
            if value == getattr(n, attr):
                return True
    return False

def get_full_name(node,direction):
    return node.path_name[1:].replace('/',f'{direction}')

def get_node_names(node,direction):
    names = {}
    if node.is_leaf:
        name = node.path_name[1:].replace('/', '_').lower()
        if node.width > 1:
            names['vector'] = f'std_logic_vector({node.width-1} downto 0)'
        else:
            names['vector'] = f'std_logic'
        names['type_name'] = f'{name}_subtype'
        # full name for address decoder only
        names['full_name'] = node.path_name.replace(f'/{node.root.name}', f'{node.root.name}_{direction}').replace('/', '.').lower()
    else:
        name = node.path_name.replace(f'/{node.root.name}', f'{node.root.name}_{direction}').replace('/', '_').lower()
        names['type_name'] = f'{name}_record_type'

    # defining array and member names
    names['array_name'] = f'{name}_array_type'
    if hasattr(node,'length'):
        names['array'] = f'array ({node.length-1} downto 0) of {names["type_name"]}'
        names['member_name'] = names['array_name']
    else:
        names['array'] = ''
        names['member_name'] = names['type_name']

    return names


class wishlist(memory):
    def __init__(self, wishlist_file):
        self.tree = None
        self.wishlist_file = wishlist_file
        self.read_input_file()
        self.write_yaml_file(self.wishlist_dict,'../examples/whishlist_parsed_input.yaml')
        self.create_tree()
        self.computing_width()
        self.set_jinja_environment()
        self.generate_vhdl_package_file()
        # starting memory object
        super().__init__(start=self.tree.address, end=self.tree.address + self.tree.address_size - 1,
                         width=self.tree.address_width, increment=self.tree.address_increment)
        self.flattening()
        print_tree(self.tree, attr_list=['address', 'mask', 'width', 'length', 'permission', 'description'])
        # Allocation
        self.address_decoder_list = []
        for node in self.register_nodes_iter():
            self.allocate(node)
        self.address_decoder = pd.concat(self.address_decoder_list)
        self.address_decoder.to_html(f"{self.wishlist_dict['firmware_path']}/{self.wishlist_dict['name'].lower()}_address_decoder.htm")
        self.generate_vhdl_address_decoder_file()
        # dropping unused address offsets and resetting the space_style
        self.space = self.space.dropna(how='all')
        self.space_style = self.space_style.loc[self.space.index,:]
        # formatting space and its style
        self.space, self.space_style = formatting(self.space, self.space_style, self.wishlist_dict)
        # creating styler object
        self.update_style()
        # Rendering styler object
        self.space_styled.hide(axis="index").to_html(buf=f"{self.wishlist_dict['firmware_path']}/{self.wishlist_dict['name'].lower()}_address_space.htm")

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
        for node in preorder_iter(self.tree):
            if re.match('^(?!.*__)[a-zA-Z][\w]*[^_]$', node.name) is None:
                raise ValueError(f'Node name {node.name} in {node.path_name} is not a valid VHDL indentifier. Please cheange the name.')

    def flattening(self):
        # Flattening tree
        finished = False
        while not finished:
            finished = True
            for node in preorder_iter(self.tree):
                if hasattr(node,'length'):
                    for i in range(node.length):
                        children = deepcopy(node.children)
                        attributes = {}
                        if hasattr(node,'description'):
                            attributes['description'] = f'Instance {i}; {node.description}'
                        if hasattr(node, 'address'):
                            if i == 0:
                                attributes['address'] = node.address
                        if hasattr(node, 'mask'):
                            attributes['mask'] = node.mask
                        if hasattr(node, 'width'):
                            attributes['width'] = node.width
                        if hasattr(node, 'permission'):
                            attributes['permission'] = node.permission
                        a = Node(f'{node.name}({i})', parent=node.parent, children=list(children), **attributes)
                    shift_nodes(self.tree, [node.path_name[1:]], [None])
                    finished = False
                    break
                    #print_tree(self.tree, attr_list=['address', 'mask', 'width', 'length', 'permission'])

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
                    raise ValueError(
                        f'The specified mask=0b{mask_str} for node {node.path_name} is asserted high in a non-contiguous bit interval\n.'
                        f'Currently, whishlist does not suport this use case, i.e. all the mask bits asserted high have to be grouped together.'
                    )
                width = int(mask_str.count('1'))
                if hasattr(node, 'width'):
                    if node.width != width:
                        raise ValueError(f'Both mask and width have been defined for {node.path_name}. However the width computed from the mask={width} is different than the specified width={node.width}.')
                else:
                    node.width = width
            elif not hasattr(node, 'width'):
                raise ValueError(
                    f'Node {node.path_name} has no width or mask specified. One of them is required, and if both are defined,'
                    f'the mask value gets priority over the width as it enforces the bit position in the address offset.\n'
                    f'Nevertheless, the provided width is still checked against the provided mask for consistency checking.'
                )


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
        direction = {
            'rw': 'control',
            'r': 'status',
        }
        self.address_decoder_list.append(pd.DataFrame({
            'name': [node.path_name]*len(address_list),
            'permission': [node.permission]*len(address_list),
            'address': address_list,
            'address_bits_lists': address_bits_lists,
            'register_bits_lists': get_register_bits_lists(address_list, address_bits_lists, node.width),
            'vhdl_member_name': [get_node_names(node, direction=direction[node.permission])['full_name']]*len(address_list)
        }))

    def get_address_string(self, address):
        return f'{{address:0{np.ceil(self.tree.address_width/4).astype(int)}X}}'.format(address=address)
    def get_vhdl_bit_string(self, bits, side):
        if len(bits) == 1 and side == 'signal':
            return ''
        elif len(bits) == 1 and side == 'address':
            return f'({bits[0]})'
        else:
            return f'({bits[0]} downto {bits[-1]})'

    # def get_signal_name(self, name, permission):
    #     direction_dict = {'r': 'status_int', 'rw': 'control_int'}
    #     return name.replace(f'/{self.tree.name}/', f'{self.tree.name}_{direction_dict[permission]}/').replace('/', '.').lower()



    def set_jinja_environment(self):
        self.environment = Environment(loader=FileSystemLoader("../templates/"))
        self.environment.globals['attr_in_children'] = attr_in_children
        self.environment.globals['attr_in_family'] = attr_in_family
        self.environment.globals['get_full_name'] = get_full_name
        self.environment.globals['get_node_names'] = get_node_names

    def generate_vhdl_package_file(self):
        template = self.environment.get_template("vhdl_package.jinja2")
        filename = f"{self.wishlist_dict['firmware_path']}/{self.wishlist_dict['name'].lower()}_pkg.vhd"
        content = template.render(self.wishlist_dict,
                                  registers=list(self.register_nodes_iter()),
                                  hierarchies=list(self.hierarchical_nodes_iter()),
                                  )
        with open(filename, mode="w") as message:
            message.write(content)

    def generate_vhdl_address_decoder_file(self):
        template = self.environment.get_template("vhdl_address_decoder.jinja2")
        filename = f"{self.wishlist_dict['firmware_path']}/{self.wishlist_dict['name'].lower()}_address_decoder.vhd"
        content = template.render(self.wishlist_dict,
                                  registers=list(self.register_nodes_iter()),
                                  hierarchies=list(self.hierarchical_nodes_iter()),
                                  address_decoder=self.address_decoder,
                                  np=np,
                                  get_address_string=self.get_address_string,
                                  get_vhdl_bit_string=self.get_vhdl_bit_string,
                                  # get_signal_name = self.get_signal_name,

                                  )
        with open(filename, mode="w") as message:
            message.write(content)

if __name__ == '__main__':
    obj = wishlist('../examples/L1CaloGfex.yaml')
