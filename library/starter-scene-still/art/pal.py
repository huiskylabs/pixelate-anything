"""The palette: one strict set of slots, each with one role.

S sky (top -> horizon), G ground (edge line, mid, deep), F foreground strip (body, lit edge),
K outline, P placeholder box (shade, lit), B flat block (shade, lit), MK the box's marker.
The sky stays under L 0.7 so the frame meets the lofi value budget; recolour by editing the hexes,
add slots for a new subject, and keep one meaning per slot.
"""
PALETTE = {
    'S0': '#4a6a86', 'S1': '#5c7c92', 'S2': '#6f8e9c',
    'G0': '#80966f', 'G1': '#668260', 'G2': '#4f6a50',
    'F0': '#2c3a2a', 'F1': '#6a8660',
    'K0': '#2c3a4a', 'P0': '#7a7f8e', 'P1': '#8c94a4',
    'B0': '#7f93a3', 'B1': '#869aa9', 'MK': '#b88f4c',
}
