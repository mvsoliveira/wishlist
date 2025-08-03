import os
import mmap
import ctypes



class AXIDriver(object):
    def __init__(self, start_address, address_size):
        self.start_address = start_address
        self.address_size = address_size
        # Open /dev/mem with read/write permissions
        fd = os.open("/dev/mem", os.O_RDWR)

        # Memory-map the file (this requires root privileges)
        vaddr = mmap.mmap(fd, self.address_size, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=self.start_address)

        # Cast the memory map to a ctypes pointer (similar to uint32_t* in C++)
        self.mem32 = (ctypes.c_uint32 * (self.address_size // 4)).from_buffer(vaddr)


    def read_words(self, offsets):
        return [self.mem32[off] for off in offsets]

    def write_words(self, offsets, data):
        for offset, value in zip(offsets, data):
            self.mem32[offset] = value

if __name__ == "__main__":

    import time
    import humanreadable as hr

    print('I am starting the test...')
    hw = AXIDriver(start_address=0xA4040000, address_size=0x100000)  # Adjust the start_address and address_size as needed
    #0xA10008AC
    N = 100000
    start = time.time()
    wdata = 0x1
    for i in range (N):
        hw.mem32[0x0]
    end = time.time()
    elapsed = (end-start)/N
    print('Direct access ',hr.Time(f"{elapsed:.10f}", default_unit=hr.Time.Unit.SECOND).to_humanreadable())

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





