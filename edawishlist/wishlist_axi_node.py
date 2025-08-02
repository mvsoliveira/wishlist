# read_words, write_words, and mapper methods are based on code from Emily and Greg
from edawishlist.utils import registers_to_node, node_to_register, get_logger, word_mask
from bigtree import Node
import mmap
import logging
import sys
from edawishlist.axi_driver import AXIDriver


class wishlist_axi_node(Node):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.value = None
        self.logger = get_logger(self.path_name, logging.INFO)
        self.bus_width = 32
        if self.is_root:
            self.axi = AXIDriver(start_address=self.address, address_size=self.address_size)


    def read(self):
        read_values = self.root.axi.read_words(self.offset)
        self.logger.debug(f'Reading values from address {self.address}, offset {self.offset}, read values: {read_values}')
        value = registers_to_node(self.offset, self.mask, read_values, self.bus_width, self.logger)
        return value

    def write(self, value):
        if not self.permission == 'rw':
            self.logger.critical(f'Terminating application while trying to this node. The respective permission is rw, therefore no value can not be written to it!' )
            sys.exit()
        # Reading all the registers associated with the node with the bus mask if any mask bit is 0
        if self.mask != [word_mask(self.bus_width) for _ in range(len(self.mask))]:
            read_values = self.root.axi.read_words(self.offset)
        else:
            read_values = [0 for _ in range(len(self.mask))]
        # Writing combined data back
        write_values = node_to_register(value, self.offset, self.mask, read_values, self.bus_width, self.logger)
        self.logger.debug(f'Writing the following values {write_values}')
        self.root.axi.write_words(self.offset,write_values)
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
