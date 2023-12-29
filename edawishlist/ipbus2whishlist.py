import json
import xmltodict
import yaml
from bigtree import nested_dict_to_tree, print_tree, preorder_iter, shift_nodes, tree_to_nested_dict
from memory import str2int
from edawishlist.wishlist import HexInt, representer, xml_beautify

default_permission = 'rw'
default_width = 32
default_mask = 2**32-1
maximum_width = 32
propagate_address = True
propagate_mask = True

default_root_attrs = {
    'address_width': 32,
    'address_increment': 4,
    'address_size': 2 ** 16,
    'software_path': '../examples',
    'firmware_path': '../examples',
}

# reading xml to dict string
xml_filename = '../examples/L1CaloGfex.xml'
xml_dict = xmltodict.parse(open(xml_filename, 'rb'))
xml_str = json.dumps(xml_dict)


# manipulating dict string
replacements = {
    '"@address"': '"address"',
    '"@permission"': '"permission"',
    '"@description"': '"description"',
    '"@mask"': '"mask"',
    '"@module"': '"module"',
}
for old, new in replacements.items():
    xml_str = xml_str.replace(old, new)

# generating tree from xml
xml_tree = json.loads(xml_str)['node']
tree = nested_dict_to_tree(xml_tree, name_key='@id', child_key='node')

# copying permission parameter from parents to only tree leaves and assigning default value for leaves without

not_supported_nodes = []
# Iterating though leaves
for leaf in preorder_iter(tree, filter_condition=lambda node: node.is_leaf):
    # copying permission parameter from parents when not defined
    if not hasattr(leaf, 'permission'):
        if hasattr(leaf.parent, 'permission'):
            leaf.permission = leaf.parent.permission
        else:
            # assigning ipbus register permission when parent has no permission defined
            leaf.permission = default_permission
    # copying address parameter from parents when not defined
    if hasattr(leaf, 'address'):
        leaf.address = HexInt(str2int(leaf.address))
    else:
        if hasattr(leaf.parent, 'address'):
            leaf.address = HexInt(str2int(leaf.parent.address))


    # handling mask and computing width if mask is not propagated
    if hasattr(leaf, 'mask'):
        mask = str2int(leaf.mask)
        if not propagate_mask:
            # Computing width based on mask value
            leaf.width = f'{mask:b}'.count('1')
            # deleting mask attribute when defined
            delattr(leaf, 'mask')
        else:
            leaf.mask = HexInt(mask)
    else:
        if propagate_mask:
            leaf.mask = HexInt(default_mask)
        else:
            leaf.width = default_width

    # keeping track of non-supported nodes
    if hasattr(leaf, 'module'): not_supported_nodes.append(leaf.path_name)

# removing non-supported nodes
shift_nodes(tree, not_supported_nodes, [None] * len(not_supported_nodes))

min_address = 2 ** maximum_width - 1
# iterating though all nodes
for node in preorder_iter(tree):
    if hasattr(node, 'address') and not node.is_leaf:
        delattr(node, 'address')
    if hasattr(node, 'address'):
        # finding minimum address to be associated to the root node
        min_address = min(min_address, node.address)
        # removing address when defined, whishlist does not support explicit address yet
        if propagate_address:
            if not node.is_leaf:
                delattr(node, 'address')
        else:
            delattr(node, 'address')
    # deleting permission from branches
    if not node.is_leaf and hasattr(node, 'permission'):
        delattr(node, 'permission')

# Setting minimum address of all nodes as the root address
tree.address = min_address
# Setting default values for
for key, value in default_root_attrs.items():
    setattr(tree, key, value)
print_tree(tree, attr_list=['width', 'length', 'permission', 'mask', 'address'])

# Dumping tree to yaml file
tree_dict = tree_to_nested_dict(tree, all_attrs=True)
with open(xml_filename.replace('xml', 'yaml'), 'w') as file:
    yaml.add_representer(HexInt, representer)
    yaml.dump(tree_dict, file, sort_keys=False)
if not_supported_nodes:
    print(
        f"Warning: Please be aware that the nodes {', '.join(not_supported_nodes)} were removed because ipbus2whislist does not support modules yet.")
