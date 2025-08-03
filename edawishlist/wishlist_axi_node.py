from edawishlist.utils import registers_to_node, node_to_register, get_logger, word_mask
from bigtree import Node
import logging
import sys
from edawishlist.axi_driver import AXIDriver


class wishlist_axi_node(Node):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.value = None
        # Using None for the format string is a more robust way to handle the get_logger function
        self.logger = get_logger(self.path_name, logging.INFO)
        self.bus_width = 32
        if self.is_root:
            self.axi = AXIDriver(start_address=self.address, address_size=self.address_size)


    def read(self):
        read_values = self.root.axi.read_words(self.offset)
        # Use efficient logging format
        #self.logger.debug('Reading values from address 0x%x, offset %s, read values: %s', self.address, self.offset, read_values)
        value = registers_to_node(self.offset, self.mask, read_values, self.bus_width, self.logger)
        return value

    def write(self, value):
        # Correctly check for read-write permission
        if self.permission != 'rw':
            # Provide a clear, direct, and non-contradictory error message
            self.logger.critical(
                f'Terminating application: Attempted to write to node "{self.path_name}" which has permission "{self.permission}", not "rw".'
            )
            sys.exit(1) # Use a non-zero exit code for errors

        # Use an efficient and Pythonic check to see if a read-modify-write is needed
        # The all() function short-circuits, avoiding list creation.
        bus_mask_val = word_mask(self.bus_width)
        if not all(m == bus_mask_val for m in self.mask):
            read_values = self.root.axi.read_words(self.offset)
        else:
            read_values = [0] * len(self.mask) # A more efficient way to create a list of zeros

        # Writing combined data back
        write_values = node_to_register(value, self.offset, self.mask, read_values, self.bus_width, self.logger)
        # Use efficient logging format
        #self.logger.debug('Writing the following values %s', write_values)
        self.root.axi.write_words(self.offset, write_values)
        return True

    def convert(self, value, parameter, **kwargs):
        if hasattr(self, parameter):
            if value == (1 << self.width) -1:
                self.logger.warning('Attempted conversion returned -1 because read value is saturated (reached maximum value due overflow protection)')
                return -1
            else:
                return eval(getattr(self, parameter))
        else:
            return value
