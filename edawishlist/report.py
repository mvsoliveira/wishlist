import re
import pandas as pd
from bigtree import preorder_iter
from edawishlist.memory import inclusive_range


def _strip_bit_index(value):
    """'/Design/reg(35)' -> '/Design/reg', '/Design/reg' -> '/Design/reg'"""
    return re.sub(r'\(\d+\)$', '', str(value))


def _parse_style(style_str):
    """Extract (permission, is_smart) from the CSS string stored in space_style."""
    s = str(style_str)
    if 'Plum'       in s: return 'rw', True
    if 'DeepSkyBlue' in s: return 'rw', False
    if 'Gold'        in s: return 'r',  True
    if 'LightGreen'  in s: return 'r',  False
    return None, None


def build_address_map(space, space_style, wishlist_dict, tree=None):
    """
    Convert the raw memory-space DataFrame into a list of rows suitable
    for the address_space.html.jinja2 template.

    Parameters
    ----------
    space       : pd.DataFrame  — columns are bit integers [width-1 .. 0],
                                  values are register path strings or NaN
    space_style : pd.DataFrame  — same shape, values are CSS strings
    wishlist_dict : dict        — top-level YAML dict (name, description, …)
    tree        : bigtree Node  — optional; used to look up descriptions

    Returns
    -------
    dict with keys: design_name, description, address_width, bit_headers, rows
    """
    width = wishlist_dict['address_width']
    addr_hex_digits = width // 4

    # Build lookup: path_name -> {description, permission}
    node_info = {}
    if tree is not None:
        for node in preorder_iter(tree, filter_condition=lambda n: n.is_leaf):
            node_info[node.path_name] = {
                'description': getattr(node, 'description', ''),
                'permission':  getattr(node, 'permission',  ''),
            }

    rows = []
    for address, row in space.iterrows():
        cells = []
        bit = width - 1        # start from MSB
        while bit >= 0:
            cell_val  = row[bit]
            style_val = space_style.loc[address, bit]

            if pd.isna(cell_val):
                # Extend run of unused bits
                colspan = 1
                while bit - colspan >= 0 and pd.isna(row[bit - colspan]):
                    colspan += 1
                cells.append({
                    'label':       '',
                    'full_path':   '',
                    'description': '',
                    'permission':  '',
                    'bit_high':    bit,
                    'bit_low':     bit - colspan + 1,
                    'colspan':     colspan,
                    'is_unused':   True,
                    'is_smart':    False,
                })
            else:
                # Group consecutive bits belonging to the same register
                owner_key = _strip_bit_index(cell_val)
                colspan = 1
                while (bit - colspan >= 0
                       and not pd.isna(row[bit - colspan])
                       and _strip_bit_index(row[bit - colspan]) == owner_key):
                    colspan += 1

                permission, is_smart = _parse_style(style_val)
                info = node_info.get(owner_key, {'description': '', 'permission': permission or ''})
                label = owner_key.split('/')[-1]

                cells.append({
                    'label':       label,
                    'full_path':   owner_key,
                    'description': info.get('description', ''),
                    'permission':  info.get('permission', permission or ''),
                    'bit_high':    bit,
                    'bit_low':     bit - colspan + 1,
                    'colspan':     colspan,
                    'is_unused':   False,
                    'is_smart':    is_smart,
                })

            bit -= colspan

        rows.append({
            'address': f"0x{address:0{addr_hex_digits}X}",
            'cells':   cells,
        })

    return {
        'design_name':   wishlist_dict['name'],
        'description':   wishlist_dict.get('description', ''),
        'address_width': width,
        'bit_headers':   list(range(width - 1, -1, -1)),
        'rows':          rows,
    }
