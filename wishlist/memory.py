import pandas as pd
import numpy as np


def str2int(v):
    if isinstance(v, list):
        return [str2int(i) for i in v]
    elif isinstance(v, str):
        if v.startswith('0x'):
            return int(v, 16)
        else:
            return int(v, 10)
    else:
        raise Exception('The input needs to be a string or a list of string')


def str_range2list(string):
    return bounds2list(str2int(string.split(':')))


def bounds2list(bounds):
    if len(bounds != 2):
        raise Exception('Each range string should contain only two integer values')
    return list(inclusive_range(*bounds, increment=1))


def inclusive_range(start, end, increment=1):
    if start <= end:
        return range(start, end + 1, increment)
    else:
        return range(start, end - 1, increment)


def check_list(list_of, dtype=int):
    if isinstance(list_of, list):
        if all(isinstance(elem, dtype) for elem in list_of):
            return True
        else:
            raise Exception(f'All elements of the list should be of type {dtype.__name__}')
    else:
        raise Exception('The input should be a list')


def check_list_of_list(list_of_lists, type):
    return all(check_list(elem, type) for elem in list_of_lists)



class memory:
    def __init__(self, start=0, end=2 ** 32 - 1, width=32, increment=1):
        self.start = start
        self.end = end
        self.width = width
        self.increment = increment
        self.address = self.start
        self.set_address_cursor(self.start)
        self.bit = self.width-1
        self.space = pd.DataFrame(None, index=inclusive_range(self.start, self.end, self.increment),
                                  columns=inclusive_range(self.width - 1, 0, -1))

    def set_address_cursor(self, address):
        if self.start <= address <= self.end:
            if not (address - self.start) % self.increment:
                self.address = address
            else:
                raise Exception(
                    "The address offset with respect to the start address is not a multiple of the increment value")
        else:
            raise Exception("The address is not within the start and end values")

    def set_bit_cursor(self, bit):
        if 0 <= bit <= self.width - 1:
            self.bit = bit
        else:
            raise Exception("The bit is not in the range 0 <= bit <= width-1")

    def _is_row_available(self, address, bits):
        return self.space.loc[address, bits].dropna().empty

    def _is_available(self, address_list, bits_list):
        return all([self._is_row_available(address, bits) for address, bits in zip(address_list, bits_list)])

    def is_available(self, address_list, bits_list):
        if check_list(address_list, int) and all([address in self.space.index for address in address_list]):
            if check_list_of_list(bits_list, int) and all(
                    [item in self.space.columns for sublist in bits_list for item in sublist]):
                if len(address_list) == len(bits_list):
                    return self._is_available(address_list, bits_list)
                else:
                    raise Exception('The list of address should have the same length as the list of bit list')
            else:
                raise Exception(
                    'All elements of the bits list should be integer and in the range 0 <= bit <= width-1')
        else:
            raise Exception(
                'All elements of the address list should be integer and in the range within the start and end values')

    def allocate_from_width(self, width, smart=True):
        # checking if requested width fits in current address offset
        if self.bit >= width - 1:
            bits_lists = [list(range(self.bit, self.bit - width, -1))]
        elif smart:
            # By convention, if a node cant be fully allocated in the current address, it attempts to allocate it on
            # the next address offset always starting from the MSB.
            self.set_bit_cursor(self.width-1)
            remainder = width % self.width
            bits_lists = [list(inclusive_range(self.width - 1, 0, -1))] * (width // self.width) + \
                         ([list(range(self.width - 1, self.width - remainder - 1, -1))],[])[remainder==0]
        else:
            raise Exception(
                f'Allocation is unable to find the requested memory space ({width} bits)  in the current address offset. It wont keep trying because smart mode is off.')

       # Computing bits lists required starting from the MSB
        while True:
            # list of address offsets to be requested
            address_list = list(range(self.address, self.address + np.ceil(width/self.width).astype(int)*self.increment, self.increment))
            # Checking if the requested addresses and bits lists are available
            if self.is_available(address_list, bits_lists):
                return address_list, bits_lists
            elif smart:
                # If smart mode is on, keep trying to allocate until the end address is reached
                if self.address <= self.end:
                    self.address_increment()
                else:
                    raise Exception('Smart allocation is unable to find the requested memory space')
            else:
                raise Exception('Allocation is unable to find the requested memory space ({width} bits) with smart mode off. Maybe a requested address offset is already in use.')




    def address_increment(self):
        self.set_address_cursor(self.address + self.increment)




if __name__ == '__main__':
    obj = memory(start=0, end=2 ** 5 - 1, width=16, increment=4)
    obj.space.loc[8,6] = 'hi'
    print(obj.allocate_from_width(32))

    print()
