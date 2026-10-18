/* Hand-drawn sprites: ASCII rows, '.' is transparent, the key maps characters to slots.
   Light comes from the upper left: lit edges on the left, a dark outline all round.
   ay (anchor y) puts the sprite's base on the ground when blitted at the ground's y. */
def('cabin', { k: 'K0', R: 'R2', r: 'R1', W: 'W2', w: 'W1', d: 'W0', y: 'WL2', Y: 'WL1' }, `
......k......
.....kRk.....
....kRRrk....
...kRRrrrk...
..kRRrrrrrk..
.kRRrrrrrrrk.
kRRrrrrrrrrrk
kkkkkkkkkkkkk
.kWwwwwwwwwk.
.kWwyYwwddwk.
.kWwYYwwddwk.
.kWwwwwwddwk.
.kkkkkkkkkkk.
`, { ax: 6, ay: 12 });

def('pine', { k: 'T0', T: 'T2', t: 'T1', b: 'W0' }, `
....k....
...kTk...
...kTk...
..kTttk..
..kTtTk..
.kTttttk.
..kTttk..
.kTtTttk.
kTttttttk
.kTtttTk.
kTttttttk
kTtTttttk
kkkkkkkkk
....b....
....b....
`, { ax: 4, ay: 14 });

def('moon', { m: 'M0', M: 'M1' }, `
..mmm..
.mMMMm.
mMMMMMm
mMMMMMm
mMMMMmm
.mMMmm.
..mmm..
`);

def('cloud', { C: 'C1', c: 'C0' }, `
.......cCCc.......ccc..
....ccCCCCCCc...cCCCCc.
..cCCCCCCCCCCCccCCCCCCc
ccccccccccccccccccccccc
`);

// twinkle: two frames, picked by frame index in blit
def('twinkle', { n: 'N0', m: 'N1' }, `
.m.
mnm
.m.
---
...
.n.
...
`);
