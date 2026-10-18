/* One strict palette per phase. Same slot = same role in every phase.
   S sky (top -> horizon), F far hills, H hill (dark -> lit rim), K outline,
   R roof, W wood, Y warm light, T pine, M moon, C cloud, N pale accents (stars, rain). */
const PALETTES = {
  dusk: {
    S0: '#2a1f4a', S1: '#432a5e', S2: '#6e3864', S3: '#b4555f', S4: '#e0794f',
    F0: '#3b2346',
    H0: '#1b1729', H1: '#2a2340', H2: '#40335a', H3: '#6c4f7a',
    K0: '#120d1c', R1: '#5a2e3f', R2: '#8f4b54', W0: '#24171f', W1: '#452c33', W2: '#6e4a48',
    Y0: '#6a3a2a', Y1: '#c9783a', Y2: '#f9b54a', Y3: '#ffe9a8',
    T0: '#121a22', T1: '#1e302d', T2: '#33503f',
    M0: '#e2a985', M1: '#ffe3c4', C0: '#7d4f72', C1: '#c3848c', N0: '#ffe9c8', N1: '#c98f8a'
  },
  rain: {
    S0: '#0d151e', S1: '#13202c', S2: '#1a2b38', S3: '#223645', S4: '#2d4453',
    F0: '#17232d',
    H0: '#0b1216', H1: '#141f26', H2: '#1f2f37', H3: '#31454e',
    K0: '#080c10', R1: '#28282f', R2: '#3b3c45', W0: '#131315', W1: '#232428', W2: '#35363e',
    Y0: '#5e4a33', Y1: '#a8682f', Y2: '#e8a046', Y3: '#ffd88a',
    T0: '#0a1311', T1: '#12221d', T2: '#1d352b',
    M0: '#46586a', M1: '#7d929a', C0: '#1c2a35', C1: '#2a3b48', N0: '#9cb6c0', N1: '#5c7884'
  }
};
