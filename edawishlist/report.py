import os
from itertools import cycle
import pandas as pd
from edawishlist.memory import inclusive_range

def index_string_difference(s1,s2):
    # s1 should be the smaller string
    diffs = [i for i,(a,b)  in enumerate(zip(cycle([*s1]),[*s2])) if a != b]
    if any(diffs):
        return diffs[0]
    else:
        return 0

def diff_string(common, register):
    return register[index_string_difference(common,register):]

def formatting(space, space_style, wishlist_dict, sep='.'):
    # Finding common names
    for index, row in space.iterrows():
        # removing unused bits, removing first / and replacing remaining with desited separator
        row = row.dropna().str.replace('/','',n=1).str.replace('/',sep)
        if any(row):
            common = os.path.commonprefix(list(row.values)).split('(')[0]
            space.loc[index,'Common name'] = common
            for bit in row.index:
                space.loc[index,bit] = diff_string(common, row[bit])
    # Adding hexadecimal address offset
    space['Address'] = space.index.map(lambda x: f"0x{{0:0{wishlist_dict['address_width']//4}X}}".format(x))
    # Changing the order of the columns
    space = space[['Address', 'Common name'] + list(inclusive_range(wishlist_dict['address_width']-1,0,-1))]
    space_style['Address'] = 'border: 1px solid black; background-color: AliceBlue'
    space_style['Common name'] = 'border: 1px solid black; background-color: FloralWhite'
    return space, space_style










