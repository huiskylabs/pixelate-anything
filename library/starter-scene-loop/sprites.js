/* Placeholder sprites: ASCII rows, '.' is transparent, the key maps characters to slots.
   Replace these with your own. ay (anchor y) puts the sprite's base on the ground when blitted at the ground's y. */
def('marker', { k: 'K0', p: 'P0', P: 'P1', m: 'MK' }, `
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
`, { ax: 7, ay: 12 });

def('block', { B: 'B1', b: 'B0' }, `
..BBBBBBBB....
BBBBBBBBBBBBBB
bbbbbbbbbbbbbb
`);
