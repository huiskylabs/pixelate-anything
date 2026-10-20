"""Placeholder slot maps: ASCII rows, '.' is transparent, the key maps each letter to a palette slot.

Replace these with your own subject. `ay` (anchor y) is the row that stands on the ground when the
map is blitted at the ground's y; `ax` is the column that sits on the given x.
"""

def slot_map(key, rows, ax=0, ay=0):
    rows = rows.strip('\n').split('\n')
    return {'w': len(rows[0]), 'h': len(rows), 'ax': ax, 'ay': ay,
            'px': [[key.get(ch) for ch in row] for row in rows]}

def blit(c, sprite, x, y):
    """draw a slot map into canvas c with its anchor at (x, y); transparent pixels are skipped"""
    for j, row in enumerate(sprite['px']):
        for i, slot in enumerate(row):
            if slot is not None:
                c.put(x - sprite['ax'] + i, y - sprite['ay'] + j, slot)

MARKER = slot_map({'k': 'K0', 'p': 'P0', 'P': 'P1', 'm': 'MK'}, """
kkkkkkkkkkkkkkk
kPPPPPPPPPPPPpk
kPPPPPPPPPPPppk
kPPPPPPPPPPPppk
kPPPPPPPPPPPppk
kPPPPPPmmPPPppk
kPPPPPPmmPPPppk
kPPPPPPPPPPPppk
kPPPPPPPPPPPppk
kPPPPPPPPPPPppk
kPPPPPPPPPPPppk
kpppppppppppppk
kkkkkkkkkkkkkkk
""", ax=7, ay=12)

BLOCK = slot_map({'B': 'B1', 'b': 'B0'}, """
..BBBBBBBB....
BBBBBBBBBBBBBB
bbbbbbbbbbbbbb
""")
