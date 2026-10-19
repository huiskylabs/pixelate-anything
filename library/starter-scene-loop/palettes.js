/* One strict palette per phase. Same slot = same role in every phase.
   S sky (top -> horizon), G ground (edge line, mid, deep), F foreground strip (body, lit edge), K outline, P placeholder (shade, lit),
   B drifting block (shade, lit), N motes, MK the cycled marker (set in sceneDynamic). */
const PALETTES = {
  day: {
    S0: '#4a6a86', S1: '#5c7c92', S2: '#6f8e9c',
    G0: '#80966f', G1: '#668260', G2: '#4f6a50',
    F0: '#2c3a2a', F1: '#6a8660',
    K0: '#2c3a4a', P0: '#7a7f8e', P1: '#8c94a4',
    B0: '#7f93a3', B1: '#869aa9', N0: '#8ea2b2', MK: '#b88f4c'
  },
  night: {
    S0: '#161f33', S1: '#1e2a42', S2: '#2a3a52',
    G0: '#3c5a58', G1: '#2c4647', G2: '#21373a',
    F0: '#0c1316', F1: '#2f4a48',
    K0: '#0e1522', P0: '#47506a', P1: '#6a7490',
    B0: '#2c3b55', B1: '#3d4f6c', N0: '#9fb5c4', MK: '#b88f4c'
  }
};
