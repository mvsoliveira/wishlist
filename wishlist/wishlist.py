import pandas
from bigtree import nested_dict_to_tree, print_tree
import yaml
import logging


class wishlist:
    def __init__(self, wishlist_file):
        self.tree = None
        self.wishlist_file = wishlist_file
        self.read_input_file()
        self.create_tree()

    def read_input_file(self):
        with open(self.wishlist_file, "r") as stream:
            try:
                self.wishlist_dict = yaml.safe_load(stream)
            except yaml.YAMLError:
                logging.exception(f'Error while reading {self.wishlist_file}.')

    def create_tree(self):
        self.tree = nested_dict_to_tree(self.wishlist_dict)
        print_tree(self.tree, attr_list=['width', 'mode'])


if __name__ == '__main__':
    obj = wishlist('../examples/wishlist.yaml')
