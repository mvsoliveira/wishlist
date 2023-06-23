#! /usr/bin/env python
# Copyright 2021 Emily Smith and Greg Myers
# Permission is hereby granted, free of charge, to
# any person obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.#
#
# Author: Emily Smith
# Email: emsmith@cern.ch
# Created: 21 Nov 2019
#

import mmap, yaml, struct, os

def LoadRegMap(rmap, registers):
    for r in rmap['nodes']:
        registers[r.get('address')] = r
    return registers

#Load Register Maps
zynq_nodes_map = yaml.safe_load(open(os.path.dirname(os.path.realpath(__file__)) + '/RgstMap_Z.yml', 'r'))
zynq_streaming_map = yaml.safe_load(open(os.path.dirname(os.path.realpath(__file__)) + '/RgstMap_ZS.yml', 'r'))
pfpga_a_map = yaml.safe_load(open(os.path.dirname(os.path.realpath(__file__)) + '/RgstMap_A.yml', 'r'))
pfpga_b_map = yaml.safe_load(open(os.path.dirname(os.path.realpath(__file__)) + '/RgstMap_B.yml', 'r'))
pfpga_c_map = yaml.safe_load(open(os.path.dirname(os.path.realpath(__file__)) + '/RgstMap_C.yml', 'r'))
zynq_simple_map = {r.get('id'): r.get('address') for r in zynq_nodes_map['nodes']}
zynq_map = LoadRegMap(zynq_nodes_map, {})
zs_map = LoadRegMap(zynq_streaming_map, {})
a_map = LoadRegMap(pfpga_a_map, {})
b_map = LoadRegMap(pfpga_b_map, {})
c_map = LoadRegMap(pfpga_c_map, {})

#zynq_simple_map = LoadRegMap('RgstMap_Z.yml', {})
#a_map = LoadRegMap('RgstMap_A.yml', {})
#b_map = LoadRegMap('RgstMap_B.yml', {})

offset_A = 0x00000000
offset_B = 0x20000000
offset_C = 0x40000000
offset_Z = 0x60000000

#Check if Address is Valid
def isValidAddress(rmap, address):
    minaddr = (next(iter(rmap.keys())) >> 24) << 24
    blk = rmap.get(address) if address in rmap else rmap.get(min(rmap.keys(), key = lambda k: abs(k-address)))
    return (address >= minaddr and address <= blk.get('address') + blk.get('size',0))

def mapper(fileno, size, offset):
    index = offset % mmap.ALLOCATIONGRANULARITY
    base = offset - index
    length = 4*size
    maplength = index + length
    mm = mmap.mmap(fileno, maplength, access=mmap.ACCESS_WRITE, offset=base)
    mv = memoryview(mm)
    return (mv[index:], length)

def readZynq(offset, size):
    with open('/dev/mem', 'r+b') as devmem:
        (mv, length) = mapper(devmem.fileno(), size, offset)
        mv_int = mv.cast('I')
        data = mv_int[0]
        devmem.close()
        return data

def writeZynq(offset, size, data):
    if (type(data) != int):
        data = struct.unpack("@I", data)[0]
    with open('/dev/mem', 'w+') as devmem:
        (mv, length) = mapper(devmem.fileno(), size, offset)
        mv_int = mv.cast('I')
        mv_int[0] = data
        return offset

def prepFPGA(rx_ctrl, rx_data, rx_stat, tx_ctrl, tx_data, tx_stat, address, debug=False):

    #These are common to both read and write.
    if (readZynq(tx_stat, 1) & 0x1) != 1:
        print("TX FIFO not ready, no way to fix.")
        return -1
    while (readZynq(rx_stat, 1) & 0x1) != 0:
        print("Ready bit: " + str(readZynq(rx_stat, 1) & 0x1))
        if debug: print("Zynq RX FIFO unexpectedly full, reading FIFO to clear")
        #Toggle to pull next value from FIFO
        writeZynq(rx_ctrl, 1, 0x0)
        writeZynq(rx_ctrl, 1, 0x1)
        #Read data from fifo
        w = readZynq(rx_data, 1)
        if debug: print ("Unexpected word from FIFO is: 0x%08X"  %w)

    #Write SOF data, not used
    writeZynq(tx_data, 1, 0xBEEFCAFE)
    #Write SOF+RDY bits, rising edge used by logic
    writeZynq(tx_ctrl, 1, 0x5)
    writeZynq(tx_ctrl, 1, 0x0)

    if readZynq(tx_stat, 1) != 1:
        print("TX FIFO not ready, no way to fix.")
        return -1

    #Write payload data (address of pFPGA register)
    writeZynq(tx_data, 1, address)

    #Write RDY bit
    writeZynq(tx_ctrl, 1, 0x1)
    writeZynq(tx_ctrl, 1, 0x0)


def readFPGA(FPGA, address, size, out=True, dbug=False):
    rx_ctrl = zynq_simple_map[FPGA+'IPB_RX_CTRL'] #0xA0010038
    rx_data = zynq_simple_map[FPGA+'IPB_RX_DATA'] #0xA0010120
    tx_ctrl = zynq_simple_map[FPGA+'IPB_TX_CTRL'] #0xA0010020
    tx_data = zynq_simple_map[FPGA+'IPB_TX_DATA'] #0xA0010024
    rx_stat = zynq_simple_map[FPGA+'IPB_RX_STAT'] #0xA001011C
    tx_stat = zynq_simple_map[FPGA+'IPB_TX_STAT'] #0xA001011C

    result = []
    for a in range(address, address+size, 1):
        prep_ret = prepFPGA(rx_ctrl, rx_data, rx_stat, tx_ctrl, tx_data, tx_stat, a, debug=dbug)

        if prep_ret == -1 or (readZynq(tx_stat, 1) & 0x1) != 1:
            print("TX FIFO not ready, no way to fix.")
            return -1

        #Write EOF+RDY bits, rising edge used by logic
        writeZynq(tx_ctrl, 1, 0x3)
        writeZynq(tx_ctrl, 1, 0x0)


        #Check RX FIFO is RDY
        w = []
        while (readZynq(rx_stat, 1) & 0x1) != 0:
            #Read data from fifo
            w.append(readZynq(rx_data, 1))
            #Toggle to pull next value from FIFO
            writeZynq(rx_ctrl, 1, 0x0)
            writeZynq(rx_ctrl, 1, 0x1)

        if not w:
            print("No words received from pFPGA.")
            return -1

        #Check that second read word is address on pFPGA
        if( ( w[1] != a) and out):
            print("Second word returned by protocol isn't the address being read, this is a problem.")
            print('Returned: 0x%08X' %w[1])
            print('Address: 0x%08X'  %a)

        result.append(w[2]) # Might need to byteswap here this may be an ironman thing though not sure

        if w and dbug:
            print("First protocol word: 0x%08X" %w[0])
            print("Second protocol word: 0x%08X" %w[1])
            print("Third protcol word: 0x%08X" %w[2])
            print("")

    return result


def writeFPGA(FPGA, address, size, value, dbug=False):
    waddress = int(hex(address),16) + int(hex(0x80000000),16)

    rx_ctrl = zynq_simple_map[FPGA+'IPB_RX_CTRL'] #0xA0010038
    rx_data = zynq_simple_map[FPGA+'IPB_RX_DATA'] #0xA0010120
    tx_ctrl = zynq_simple_map[FPGA+'IPB_TX_CTRL'] #0xA0010020
    tx_data = zynq_simple_map[FPGA+'IPB_TX_DATA'] #0xA0010024
    rx_stat = zynq_simple_map[FPGA+'IPB_RX_STAT'] #0xA001011C
    tx_stat = zynq_simple_map[FPGA+'IPB_TX_STAT'] #0xA001011C

    if size==1 and (type(value) != list):
        list_val = [value]
    else:
        list_val = value

    for wa,v in zip(range(waddress, waddress+size, 1), list_val):
        prep_ret = prepFPGA(rx_ctrl, rx_data, rx_stat, tx_ctrl, tx_data, tx_stat, wa, debug=dbug)


        if prep_ret == -1 or readZynq(tx_stat, 1) != 1:
            print("TX FIFO not ready, no way to fix.")
            return -1

        writeZynq(tx_data, 1, v)
        #Write EOF+RDY bits, rising edge used by logic
        writeZynq(tx_ctrl, 1, 0x3)
        writeZynq(tx_ctrl, 1, 0x0)

    return address

def read(address, size, output=True, debug=False):
    result = []
    if (isValidAddress(zynq_map, address)):
        result = readZynq(address,size)
    elif (isValidAddress(zs_map, address)):
        result = readFPGA('Z', address, size, out=output, dbug=debug)
        b_result = struct.pack('@{}I'.format(len(result)), *result)
    elif (isValidAddress(a_map, address)):
        result = readFPGA('A', address, size, out=output, dbug=debug)
        b_result = struct.pack('@{}I'.format(len(result)), *result)
    elif (isValidAddress(b_map, address)):
        result = readFPGA('B', address, size, out=output, dbug=debug)
        b_result = struct.pack('@{}I'.format(len(result)), *result)
    elif (isValidAddress(c_map, address)):
        result = readFPGA('C', address, size, out=output, dbug=debug)
        b_result = struct.pack('@{}I'.format(len(result)), *result)
    else:
        result = [None]

    if output:
        if (result != [None]):
                print('Read ' + str(size) + ' words at address 0x%08X:' %address)
                if (type(result) == list):
                    for i in result: print('0x%08X' %i)
                else:
                    print('0x%08X' %result)
        else:
                print("Sorry, that FPGA is not readable right now.")

    if(type(result) == list and len(result) == 1):
        return result[0]
    else:
        return result


def write(address, size, value, output=True, readback=True, debug=False):
    if (isValidAddress(zynq_map, address)):
        result = writeZynq(address, size, value)
        if readback: rdbk = read(address, size, output=False)
    elif (isValidAddress(zs_map, address)):
        result = writeFPGA('Z', address, size, value, dbug=debug)
        if readback: rdbk = read(address,size, output=False, debug=debug)
    elif (isValidAddress(a_map, address)):
        result = writeFPGA('A', address, size, value, dbug=debug)
        if readback: rdbk = read(address,size, output=False, debug=debug)
    elif (isValidAddress(b_map, address)):
        result = writeFPGA('B', address, size, value, dbug=debug)
        if readback: rdbk = read(address, size, output=False, debug=debug)
    elif (isValidAddress(c_map, address)):
        result = writeFPGA('C', address, size, value, dbug=debug)
        if readback: rdbk = read(address, size, output=False, debug=debug)
    else:
        rdbk = None
        result = None

    if output:
        if (address != None and result != None):
            print('Wrote ' + str(size) + ' words at address 0x%08X' %address)
            if readback:
                print('Readback ' + str(size) + ' words at address 0x%08X:' %address)
                if (type(rdbk) == list):
                    for r in rdbk: print('0x%08X' %r)
                else:
                    print('0x%08X' %rdbk)
        else:
            print("Sorry, that FPGA is not writeable right now.")

    #return result
