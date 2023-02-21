import xmltodict
from bigtree import nested_dict_to_tree, print_tree, postorder_iter, preorder_iter, shift_nodes, tree_to_nested_dict
import json
import yaml

default_permission = 'rw'
default_width = 32
maximum_width = 32

default_root_attrs = {
'address_width': 32,
'address_increment': 4,
'address_size': 2**16,
'software_path': '../examples',
'firmware_path': '../examples',
}

# reading xml to dict string
xml_filename = '../examples/L1CaloGfex.xml'
xml_dict = xmltodict.parse(open(xml_filename, 'rb'))
xml_str = json.dumps(xml_dict)

# manipulating dict string
replacements = {'"node"': '"children"',
                '"@id"': '"name"',
                '"@address"': '"address"',
                '"@permission"': '"permission"',
                '"@description"': '"description"',
                '"@mask"': '"mask"',
                '"@module"': '"module"',
                }
for old,new in replacements.items():
    xml_str = xml_str.replace(old, new)

# generating tree from xml
xml_tree = json.loads(xml_str)['children']
tree = nested_dict_to_tree(xml_tree)
print_tree(tree, attr_list=['width', 'length', 'permission'])

# copying permission parameter from parents to only tree leaves and assigning default value for leaves without
str2int = lambda v : int(v,16) if v.startswith('0x') else int(v,10)
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
    # defining width based on mask
    if hasattr(leaf, 'mask'):
        mask = str2int(leaf.mask)
        mask_str = f'{mask:b}'
        leaf.width = mask_str.count('1')
    else:
        # assigning default width value when mask is not defined
        leaf.width = default_width
    if hasattr(leaf, 'mask'): delattr(leaf, 'mask')
    if hasattr(leaf, 'module'): not_supported_nodes.append(leaf.path_name)


# removing non-supported nodes
shift_nodes(tree,not_supported_nodes, [None]*len(not_supported_nodes))


min_address = 2**maximum_width-1
# iterating though all nodes
for node in preorder_iter(tree):
    if hasattr(node,'address'):
        # finding minimum address to be associated to the root node
        min_address = min(min_address,str2int(node.address))
        # removing address when defined, whishlist does not support explicit address yet
        delattr(node, 'address')
    # deleting permission from branches
    if not node.is_leaf and hasattr(node, 'permission'):
        delattr(node, 'permission')

# Setting minimum address of all nodes as the root address
tree.address = min_address
# Setting default values for
for key,value in default_root_attrs.items():
    setattr(tree,key,value)
print_tree(tree, attr_list=['width', 'length', 'permission', 'mask', 'address'])

tree_dict = tree_to_nested_dict(tree, all_attrs=True)
with open(xml_filename.replace('xml','yaml'), 'w') as file:
    yaml.dump(tree_dict, file, sort_keys=False)

print()