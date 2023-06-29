# read, write, and mapper methods are based on code from Emily and Greg
from utils import registers_to_node, get_logger, word_mask
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
            mv_int[0] = data
            return True

    def read_node(self):
        read_values = self.read()
        self.logger.debug(f'Reading values from {self.path_name}, read values: {read_values}')
        value = registers_to_node(self.address, self.mask, read_values, self.bus_width, self.logger)
        return value

    # async def write_node(dut, node, value, bus_width):
    #     # Computing the bus mask
    #     bus_mask = self.word_mask(bus_width)
    #     # Reading all the registers associated with the node with the bus mask
    #     read_values = await read(dut, self.address, [bus_mask] * len(self.address))
    #     # Node LSB (can be higher than bus width)
    #     node_lsb = 0
    #     # Empty array of values to be written
    #     write_values = []
    #     logger.debug(f'Reading values from {self.path_name}, read values: {read_values}')
    #     for i, (addr, msk, rdvl) in enumerate(reversed(list(zip(self.address, self.mask, read_values)))):
    #         # Number of bits used by a given node in the current address offset
    #         word_width = int(f'{msk:b}'.count('1'))
    #         # Mask to be used to mask the node value
    #         node_word_mask = word_mask(word_width) << node_lsb
    #         # Masking the node value
    #         node_word_value = (value & node_word_mask) >> node_lsb
    #         # Computing the MSB for current address offset
    #         lsb = f'{{mask:0{bus_width}b}}'.format(mask=msk)[::-1].find('1')
    #         logger.debug(
    #             f'Word width = {word_width}, node_mask = 0x{node_word_mask:x}, node_word_value = {node_word_value}, lsb = {lsb}')
    #         # Computing value to be written not yet masked in order to keep current data in the same address offset
    #         bus_word_value = node_word_value << lsb
    #         # Masking data that should be kept
    #         word_to_keep = rdvl & (bus_mask - msk)
    #         # Computing value to be written and appending to list
    #         combined = bus_word_value | word_to_keep
    #         logger.debug(
    #             f'W:{i} Combining word_to_keep:(0b{{word_to_keep:0{bus_width}b}}, 0x{word_to_keep:x}, {word_to_keep:d}) to bus_word_value: (0b{{bus_word_value:0{bus_width}b}}, 0x{bus_word_value:x}, {bus_word_value:d}), resulting in combined: (0b{{combined:0{bus_width}b}}, 0x{combined:x}, {combined:d})'.format(
    #                 word_to_keep=word_to_keep, bus_word_value=bus_word_value, combined=combined))
    #         write_values.append(combined)
    #         # Incrementing node_lsb
    #         node_lsb += word_width  # incrementing LSB by word width
    #     # Writing combined data back
    #     logger.debug(f'Writing the following values {write_values[::-1]}')
    #     ack = await write(dut, self.address, [bus_mask] * len(self.address), write_values[::-1])
    #     return True
