# read, write, and mapper methods are based on code from Emily and Greg
import mmap
from bigtree import Node
class CustomNode(Node):
    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)

    def mapper(self, fileno, size, offset):
        index = offset % mmap.ALLOCATIONGRANULARITY
        base = offset - index
        length = 4 * size
        maplength = index + length
        mm = mmap.mmap(fileno, maplength, access=mmap.ACCESS_WRITE, offset=base)
        mv = memoryview(mm)
        return mv[index:], length

    def read(self):
        print(f'read {self.name} at {self.address[0]}')
        # with open('/dev/mem', 'r+b') as devmem:
        #     (mv, length) = self.mapper(devmem.fileno(), len(self.address), self.address[0])
        #     mv_int = mv.cast('I')
        #     data = mv_int[0]
        #     devmem.close()
        #     return data

    def write(self, data):
        print(f'write {data} at {self.address[0]}')
        # with open('/dev/mem', 'w+') as devmem:
        #     (mv, length) = self.mapper(devmem.fileno(), len(self.address), self.address[0])
        #     mv_int = mv.cast('I')
        #     mv_int[0] = data
        #     return self.address[0]