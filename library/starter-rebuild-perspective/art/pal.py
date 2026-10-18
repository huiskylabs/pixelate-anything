"""The palette: one strict set of slots, each with one role.

S sky (top -> horizon), G ground (far haze, mid, near), J paving joints, A and B the two placeholder
blocks (lit face, shade face, panels on each), K the contact line where a block meets the ground.
Light comes from the left: the faces turned left (toward the left vanishing point) are lit.
Keep values under L 0.7 for the lofi budget; add slots for a new subject, one meaning per slot.
"""
PALETTE = {
    'S0': '#4a6a86', 'S1': '#5c7c92', 'S2': '#6f8e9c',
    'G0': '#7a8e84', 'G1': '#647a68', 'G2': '#506652', 'J0': '#43553f',
    'A0': '#a39176', 'A1': '#6c6e7c', 'A2': '#857560', 'A3': '#565868',
    'B0': '#8f8c86', 'B1': '#5e6474', 'B2': '#76736d', 'B3': '#4c5262',
    'K0': '#2f343a',
}
