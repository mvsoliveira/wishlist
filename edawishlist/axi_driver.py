from edawishlist import mmio
import numpy
import numpy as np
import os

from bigtree import Node
from edawishlist.utils import registers_to_node, node_to_register, get_logger, word_mask
# from node import wishlist_axi_node
import logging
import sys


class device(object):
    def has_capability(self,name):
        if name == 'MEMORY_MAPPED':
            return True
        else:
            return False

    def mmap(self, base_addr, length):
        import mmap

        euid = os.geteuid()
        if euid != 0:
            raise EnvironmentError("Root permissions required.")

        # Align the base address with the pages
        virt_base = base_addr & ~(mmap.PAGESIZE - 1)

        # Calculate base address offset w.r.t the base address
        virt_offset = base_addr - virt_base

        # Open file and mmap
        mmap_file = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
        mem = mmap.mmap(
            mmap_file,
            length + virt_offset,
            mmap.MAP_SHARED,
            mmap.PROT_READ | mmap.PROT_WRITE,
            offset=virt_base,
        )
        os.close(mmap_file)
        array = np.frombuffer(mem, np.uint32, length >> 2, virt_offset)
        return array


class AXIDriver(object):
    def __init__(self, start_address, address_size):
        self.start_address = start_address
        self.address_size = address_size
        self.hw = mmio.MMIO(start_address,address_size << 2,device())

    def read_words(self, address):
        data = []
        for addr in address:
            data.append(self.hw.read(addr))
        return data

    def write_words(self, address, data):
        for i in range(len(address)):
            self.hw.write(address[i], data[i])
        return True

if __name__ == "__main__":

    import time
    import humanreadable as hr

    print('I am starting the test...')
    #offset= 0xA10008AC
    hw = mmio.MMIO(0xA4040000, 0x00010000 << 2, device())

    #0xA10008AC
    N = 1000
    start = time.time()
    wdata = 0x1
    for i in range (N):
        hw.read(0x0)
    end = time.time()
    elapsed = (end-start)/N
    print('MMIO direct access ',hr.Time(f"{elapsed:.10f}", default_unit=hr.Time.Unit.SECOND).to_humanreadable())

    # zfpga = zfpga(log_level=logging.INFO,
    #               name='Z',
    #               yaml_file='/software/lite/zfpga_backannotated.yaml',
    #               base_node=wishlist_axi_node,
    #               sleep=time.sleep)

    # zfpga.robot.tree.axi = AXIDriver(start_address=zfpga.robot.tree.address, address_size=zfpga.robot.tree.address_size)
    # from bigtree import preorder_iter

    # test_rw_0 = list(preorder_iter(zfpga.robot.tree, filter_condition=lambda node: node.is_leaf and 'test_rw(0)' in node.name))[0]
    # start = time.time()
    # wdata = 0x1
    # for i in range(N):
    #     zfpga.robot.tree.axi.read_words([test_rw_0.address[0]])
    # end = time.time()
    # elapsed = (end-start)/N
    # print('AXI driver access', hr.Time(f"{elapsed:.10f}", default_unit=hr.Time.Unit.SECOND).to_humanreadable())





