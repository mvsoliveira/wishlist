# read, write, and mapper methods are based on code from Emily and Greg
from utils import registers_to_node, node_to_register, get_logger
from bigtree import Node
import mmap
import logging

class AXINode(Node):
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

    def read(self):
        with open('/dev/mem', 'r+b') as devmem:
            (mv, length) = self.mapper(devmem.fileno(), len(self.address), self.address[0])
            mv_int = mv.cast('I')
            data = list(mv_int)
            devmem.close()
            return data

    def write(self, data):
        with open('/dev/mem', 'w+') as devmem:
            (mv, length) = self.mapper(devmem.fileno(), len(self.address), self.address[0])
            mv_int = mv.cast('I')
            for i, v in enumerate(data):
                mv_int[i] = v
            return True

    def read_node(self):
        read_values = self.read()
        self.logger.debug(f'Reading values from address {self.address}, read values: {read_values}')
        value = registers_to_node(self.address, self.mask, read_values, self.bus_width, self.logger)
        return value

    def write_node(self, value):
        # Reading all the registers associated with the node with the bus mask
        read_values = self.read()
        # Writing combined data back
        write_values = node_to_register(value, self.address, self.mask, read_values, self.bus_width, self.logger)
        self.logger.debug(f'Writing the following values {write_values[::-1]}')
        self.write(write_values[::-1])
        return True
