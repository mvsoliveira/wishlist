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


def get_register_bits_lists(address_list, address_bits_lists, width):
    register_current_bit = width - 1
    register_bits_lists = []
    # Iterating through the list of addresses and list of list of address_bits
    for address, address_bits in zip(address_list, address_bits_lists):
        register_bits = []
        # assigning name of the owner for each bit
        for bit in address_bits:
            # keep tracking of the register bit
            register_bits.append(register_current_bit)
            # decrementing current bit
            register_current_bit -= 1
        # keep track of the list of register_bits
        register_bits_lists.append(register_bits)
    return register_bits_lists



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
        self.color = {
            'unallocated' : 'Gainsboro',
            'smart_allocated_rw' : 'Plum',
            'hard_allocated_rw' : 'DeepSkyBlue',
            'smart_allocated_r': 'Gold',
            'hard_allocated_r': 'LightGreen',
        }

        self.space_style = pd.DataFrame(self.get_css_style(allocated=False), index=self.space.index, columns=self.space.columns)
        self.space_styled = pd.DataFrame(None, index=inclusive_range(self.start, self.end, self.increment),
                                  columns=inclusive_range(self.width - 1, 0, -1))

    def get_css_style(self, allocated=True, **kwargs):
        if allocated:
            smart_string = ('hard','smart')[kwargs['smart']]
            color_name = f'{smart_string}_allocated_{kwargs["permission"]}'
        else:
            color_name = 'unallocated'
        return 'border: 1px solid black; background-color: {c:s}'.format(c=self.color[color_name])

    def update_style(self):
        # This is a function that returns the dataframe containing the CSS strings.
        # For some reason it cant be a member of the class otherwise a recursion problem arises
        # and python reaches the maximum of 1000-depth recursion
        get_space_style = lambda df: self.space_style
        self.space_styled = self.space.fillna("").style.apply(get_space_style, axis=None)

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

    def print_debug_space(self):
        print('Debugging information: \n',
              self.space.loc[self.address - 2 * self.increment:self.address + 2 * self.increment, :])

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
                'All elements of the address list should be integer and in the range within the start and end values. Check if the requested width is too large.')


    def allocate_from_width(self, width, name=None, permission=None, smart=True):
        if name is None: name = '__allocated_without_name__'
        if permission is None: permission = '__allocated_without_permission__'
        # checking if requested width fits in current address offset
        if self.bit >= width - 1:
            address_bits_lists = [list(range(self.bit, self.bit - width, -1))]
        elif smart:
            # By convention, if a node cant be fully allocated in the current address, it attempts to allocate it on
            # the next address offset always starting from the MSB. But the address offset is only set in the while loop
            self.set_bit_cursor(self.width-1)
            remainder = width % self.width
            address_bits_lists = [list(inclusive_range(self.width - 1, 0, -1))] * (width // self.width) + \
                         ([list(range(self.width - 1, self.width - remainder - 1, -1))],[])[remainder==0]
        else:
            raise Exception(f'Allocation will not check if the required {width} bits are already in use in the memory-mapped space because the smart mode is off and there are not enough bits for any address offset using address width={self.width} and bit cursor={self.bit} to accomodate the required memory space.')

       # Computing bits lists required starting from the MSB
        while True:
            # List of address offsets to be requested
            # Here, I am just using sequential address values, one day one might evaluate using a different strategy
            # to minimize address decoder combinational logic
            address_list = list(range(self.address, self.address + np.ceil(width/self.width).astype(int)*self.increment, self.increment))
            # Checking if the requested addresses and bits lists are available
            if self.is_available(address_list, address_bits_lists):
                # Filling the memory space with the owner of each memory space bit
                final_address, final_address_bit = self._assign_owner(address_list, address_bits_lists, name, width, permission, smart)
                # moving the cursor to the end of the allocated space and incrementing one bit
                self.set_address_cursor(final_address)
                self.set_bit_cursor(final_address_bit)
                self.bit_increment()
                return address_list, address_bits_lists
            elif smart:
                # If smart mode is on, keep trying to allocate until the end address is reached
                if self.address <= self.end:
                    self.address_increment()
                else:
                    raise Exception('Smart allocation is unable to find the requested memory space and reached the maximum address value')
            else:
                self.print_debug_space()
                raise Exception(f'Allocation is unable to find the requested memory space for {name} with ({width} bits) with address={self.address} and bit={self.bit} cursors with smart mode off. The entire or a subset of the requested memory space is already in use. It wont keep trying because smart mode is off.')

    def _assign_owner(self, address_list, address_bits_lists, name, width, permission, smart):
        # Iterating through the list of addresses and list of list of address_bits
        # address_bits represent the bits in the AXI address signal, i.e. right side of the address decoder assignment for write transactions
        # register_bits represent the bits in the register signal, i.e. left side of the address decoder assignment for write transactions
        register_bits_lists = get_register_bits_lists(address_list, address_bits_lists, width)
        for address, address_bits, register_bits in zip(address_list, address_bits_lists, register_bits_lists):
            # assigning name of the owner for each bit
            for address_bit, register_bit in zip(address_bits, register_bits):
                # If width > 1, add bit index between brackets
                if width > 1:
                    self.space.loc[address, address_bit] = f'{name}({register_bit})'
                # otherwise, just the name
                else:
                    self.space.loc[address, address_bit] = f'{name}'
                # adding a CSS string to each cell
                self.space_style.loc[address, address_bit] = self.get_css_style(permission=permission, smart=smart)
        return address, address_bit


    def address_increment(self):
        self.set_address_cursor(self.address + self.increment)

    def bit_increment(self):
        # If current bit cursor is greater than 0, just decrement the bit cursor
        if self.bit > 0:
            self.set_bit_cursor(self.bit-1)
        # Otherwise, increment the address offset and move the bit cursor to the MSB
        else:
            self.address_increment()
            self.set_bit_cursor(self.width - 1)




if __name__ == '__main__':
    obj = memory(start=0, end=2 ** 7 - 1, width=32, increment=4)
    obj.space.loc[4,6] = 'hi'
    print(obj.allocate_from_width(15, name='hi', permission='rw', smart=False))
    obj.address_increment()
    print(obj.allocate_from_width(5, name='hi2', permission='r', smart=False))
    print(obj.allocate_from_width(200, name='hi3', permission='r' ))
    print(obj.allocate_from_width(5, name='hi4', permission='rw', smart=True))
    obj.update_style()


    print()
