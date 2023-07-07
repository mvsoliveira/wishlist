# read_words, write_words, and mapper methods are based on code from Emily and Greg
from utils import registers_to_node, node_to_register, get_logger, word_mask
from bigtree import Node
import mmap
import logging
import sys


class wishlist_axi_node(Node):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.value = None
        self.logger = get_logger(self.path_name, logging.INFO)
        self.bus_width = 32

    def mapper(self, fileno, size, offset):
        index = offset % mmap.ALLOCATIONGRANULARITY
        base = offset - index
        length = 4 * size
        maplength = index + length
        mm = mmap.mmap(fileno, maplength, access=mmap.ACCESS_WRITE, offset=base)
        mv = memoryview(mm)
        return mv[index:], length

    def read_words(self):
        with open('/dev/mem', 'r+b') as devmem:
            (mv, length) = self.mapper(devmem.fileno(), len(self.address), self.address[0])
            mv_int = mv.cast('I')
            data = list(mv_int)
            devmem.close()
            return data

    def write_words(self, data):
        with open('/dev/mem', 'w+') as devmem:
            (mv, length) = self.mapper(devmem.fileno(), len(self.address), self.address[0])
            mv_int = mv.cast('I')
            for i, v in enumerate(data):
                mv_int[i] = v
            return True

    def read(self):
        read_values = self.read_words()
        self.logger.debug(f'Reading values from address {self.address}, read values: {read_values}')
        value = registers_to_node(self.address, self.mask, read_values, self.bus_width, self.logger)
        return value

    def write(self, value):
        if not self.permission == 'rw':
            self.logger.critical(f'Terminating application while trying to this node. The respective permission is rw, therefore no value can not be written to it!' )
            sys.exit()
        # Reading all the registers associated with the node with the bus mask if any mask bit is 0
        if self.mask != [word_mask(self.bus_width) for _ in range(len(self.mask))]:
            read_values = self.read_words()
        else:
            read_values = [0 for _ in range(len(self.mask))]
        # Writing combined data back
        write_values = node_to_register(value, self.address, self.mask, read_values, self.bus_width, self.logger)
        self.logger.debug(f'Writing the following values {write_values}')
        self.write_words(write_values)
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
