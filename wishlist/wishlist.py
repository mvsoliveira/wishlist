import pandas
from bigtree import nested_dict_to_tree, print_tree, findall, prune_tree, find_attrs, postorder_iter
import yaml
import logging
from jinja2 import Environment, FileSystemLoader


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

class wishlist:
    def __init__(self, wishlist_file):
        self.tree = None
        self.wishlist_file = wishlist_file
        self.read_input_file()
        self.write_yaml_file(self.wishlist_dict,'../examples/whishlist_parsed_input.yaml')
        self.create_tree()
        self.generate_vhdl_package_file()

    def read_input_file(self):
        with open(self.wishlist_file, "r") as stream:
            try:
                self.wishlist_dict = yaml.safe_load(stream)
                print(self.wishlist_dict)
            except yaml.YAMLError:
                logging.exception(f'Error while reading {self.wishlist_file}.')

    def write_yaml_file(self, string, filename):
        with open(filename, 'w') as file:
            documents = yaml.dump(string, file)

    def create_tree(self):
        self.tree = nested_dict_to_tree(self.wishlist_dict)
        print_tree(self.tree, attr_list=['width', 'permission'])

    def register_nodes_iter(self):
        return postorder_iter(self.tree, filter_condition=lambda node: node.children == ())

    def hierarchical_nodes_iter(self):
        return postorder_iter(self.tree, filter_condition=lambda node: node.children != ())

    def generate_vhdl_package_file(self):
        environment = Environment(loader=FileSystemLoader("../templates/"))
        environment.globals['attr_in_children'] = attr_in_children
        environment.globals['get_full_name'] = get_full_name

        template = environment.get_template("package.vhdt")
        filename = f"{self.wishlist_dict['firmware_path']}/{self.wishlist_dict['name']}_pkg.vhd"
        content = template.render(self.wishlist_dict,
                                  registers=list(self.register_nodes_iter()),
                                  hierarchies=list(self.hierarchical_nodes_iter())
                                  )
        with open(filename, mode="w") as message:
            message.write(content)


if __name__ == '__main__':
    obj = wishlist('../examples/wishlist.yaml')
