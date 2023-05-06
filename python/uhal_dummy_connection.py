import uhal
import random
import sys
# Creating hardware object to Dymmy Hardware Server UDP though control hub
hw = uhal.getDevice( "dummy" , 'chtcp-2.0://localhost:10203?target=127.0.0.1:50001', f'file://{sys.argv[1]}')

# Creating dictionary with all nodes and respective values read from hardware
d = {}
for node in hw.getNodes():
    d[node] = {'read' : hw.getNode(node).read(), 'written': 0}
hw.dispatch()

# Printing node attributes and writing random value to rw single registers
for key, value in d.items():
    width = f'{hw.getNode(key).getMask():b}'.count('1')
    print(f"{key} = {int(value['read'])}, address: {hw.getNode(key).getAddress():08X}, permission: {hw.getNode(key).getPermission()}, mode: {hw.getNode(key).getMode()}, width: {width}")
    # Check if register is rw, single mode, and a leaf, i.e. empty children nodes
    if hw.getNode(key).getPermission() == uhal.NodePermission(3) and hw.getNode(key).getMode() == uhal.BlockReadWriteMode(0) and not hw.getNode(key).getNodes():
         value['written'] = random.randint(0,2**width-1)
         hw.getNode(key).write(value['written'])
    else:
         value['written'] = 0
hw.dispatch()

# Reading values back and checking against errors
for key, value in d.items():
    value['read'] = hw.getNode(key).read()
hw.dispatch()
for key, value in d.items():
    print(f"{key} => written: {int(value['written'])}, read: {int(value['read'])}")
    # Check if register is rw, single mode, and a leaf, i.e. empty children nodes
    if hw.getNode(key).getPermission() == uhal.NodePermission(3) and hw.getNode(key).getMode() == uhal.BlockReadWriteMode(0) and not hw.getNode(key).getNodes():
        if value['written'] != value['read']:
            raise Exception(f'Value read and written are different for register {key}')
print(f'Simulation using dummy hardware finished with success after checking {len(d)} registers listed in {sys.argv[1]}')