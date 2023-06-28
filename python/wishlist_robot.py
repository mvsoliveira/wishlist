import yaml
import os
from bigtree import nested_dict_to_tree, tree_to_nested_dict, print_tree, postorder_iter, preorder_iter, Node
from example_custom_node import CustomNode
def read_tree():
    yaml_file = os.getenv("BACKANNOTATED_YAML")
    with open(yaml_file, "r") as stream:
        wishlist_dict = yaml.safe_load(stream)
    tree = nested_dict_to_tree(wishlist_dict, node_type=CustomNode)
    print('Testing the following register tree:')
    print_tree(tree, all_attrs=True, style='ansi')
    return tree


if __name__ == '__main__':
    tree = read_tree()
    nodes = list(preorder_iter(tree, filter_condition=lambda node: node.is_leaf))
    for node in nodes:
        node.read()

