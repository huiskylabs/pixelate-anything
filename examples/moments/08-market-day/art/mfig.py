"""Market Day figures: 13-px 3.3-head iso people as hand-typed slot maps (my own, after studying
references/assets/figures.py iso_person), plus the dog, pigeons and the wedding party.

Each figure is drawn facing 'se' (3/4 toward the viewer, to the right); 'sw' is the mirror.
Keys: h hair, s skin, S skin shade/feature, t shirt, T shirt second (jacket/apron), p pants,
f shoes, d dress, v veil, b bouquet, g gold (brass), k a hard black line, w white, o grey.
A 1 px #000 silhouette is added round every sprite."""
import sys
sys.path.insert(0, '/home/user/pixelate-anything/tools')
from iso import hash2
import mkit

# ---------------------------------------------------------------- bodies (inner art, no outline)
HEAD = {
    'short': ["hhh.", "hsss", "hsss", ".ss."],
    'long':  ["hhhh", "hsss", "hsss", "hss."],
    'bun':   [".hh.", "hhhh", "hsss", ".ss."],
    'cap':   ["TTT.", "TTTT", "hsss", ".ss."],
    'bald':  [".ss.", "ssss", "ssss", ".ss."],
}
# 5 wide from here on; the head sits at columns 0..3 shifted +1 (facing right: face on the right)
TORSO = {
    'tee':    ["ttttt", "ttttt", "ttttt", "sttts"],
    'jacket': ["tTTTt", "tTTTt", "tTTTt", "sTTTs"],
    'apron':  ["ttttt", "tTTTt", "tTTTt", "sTTTs"],
}
LEGS = {
    'stand': [".ppp.", ".p.p.", ".p.p.", ".p.p.", ".f.f."],
    'walk':  [".ppp.", ".p.p.", "p...p", "p...p", "f...f"],
    'stride':[".ppp.", ".pp..", ".p.p.", "p..p.", "f..f."],
    'skirt': [".ttt.", "ttttt", ".s.s.", ".s.s.", ".f.f."],
}

def body(hair='short', torso='tee', legs='stand', arm=None):
    """inner rows (list of strings) for one figure, 5-7 wide, 13 tall.
    arm: None, 'up' (near arm raised: throwing, waving), 'out' (near arm reaching right),
    'both' (both arms up: juggling, cheering)."""
    head = ['.' + r for r in HEAD[hair]]
    rows = [list(r.ljust(7, '.')) for r in head + list(TORSO[torso]) + list(LEGS[legs])]
    if arm in ('up', 'both'):
        for r in range(0, 5):
            rows[r][5] = 's' if r < 3 else 't'
        rows[7][4] = rows[6][4]                 # the hand left the hip
    if arm == 'both':
        rows = [['.'] + r[:6] for r in rows]
        for r in range(0, 5):
            rows[r][0] = 's' if r < 3 else 't'
        rows[7][1] = rows[6][1]
    if arm == 'out':
        rows[6][5] = 't'; rows[6][6] = 's'
        rows[7][4] = rows[6][4]
    return [''.join(r).rstrip('.') or '.' for r in rows]

KID = {
    'stand': ["hhh.", "hss.", ".s..", "ttt.", "ttt.", "p.p.", "f.f."],
    'run':   ["hhh..", "hss..", ".s...", "tttt.", "ttt..", "p..p.", "f...f"],
    'reach': ["hhh.s", "hsss.", ".s.t.", "tttt.", "ttt..", "p.p..", "f.f.."],
}

KEY_BASE = {'h': 'hk', 's': 'skinA', 'S': 'skinAd', 't': 'sky2', 'T': 'plaster2', 'p': 'slate2',
            'f': 'g1', 'd': 'white', 'v': 'g7', 'b': 'rose2', 'g': 'gold', 'G': 'gold2', 'k': 'ol',
            'w': 'white', 'o': 'g4', 'r': 'rose2', 'R': 'rose1', 'q': 'g0', 'y': 'bread2', 'm': 'leaf2',
            'n': 'brown2', 'x': 'fishc', 'c': 'plaster1', 'a': 'g6'}

SHIRTS = ['sky2', 'mint2', 'ochre2', 'cream2', 'plaster2', 'slate2', 'g3', 'brown2', 'terra2', 'leaf2', 'pink2', 'sky1', 'mint1']
PANTS = ['slate2', 'g1', 'g3', 'brown1', 'sky1', 'cream1', 'slate1']
HAIRS = ['hk', 'hb', 'hy', 'hr', 'hk', 'hb', 'g5']
SKINS = ['skinA', 'skinB', 'skinC', 'skinA', 'skinB']

def colours(seed, **over):
    k = dict(KEY_BASE)
    sk = SKINS[int(hash2(seed, 1, 3) * len(SKINS))]
    k['s'] = sk; k['S'] = sk + 'd'
    k['h'] = HAIRS[int(hash2(seed, 2, 3) * len(HAIRS))]
    k['t'] = SHIRTS[int(hash2(seed, 3, 3) * len(SHIRTS))]
    tt = SHIRTS[int(hash2(seed, 4, 3) * len(SHIRTS))]
    k['T'] = tt if tt != k['t'] else 'plaster2'
    k['p'] = PANTS[int(hash2(seed, 5, 3) * len(PANTS))]
    k.update(over)
    return k

def person(seed, pose='stand', facing='se', **over):
    """a townsperson: pose 'stand', 'walk', 'stride', 'up' (arm raised), 'out' (arm reaching),
    'both' (both arms up), 'skirt' (a dress), 'back' (seen from behind)."""
    hair = ['short', 'long', 'bun', 'cap', 'short', 'bald', 'long'][int(hash2(seed, 6, 3) * 7)]
    torso = ['tee', 'jacket', 'tee', 'tee', 'jacket'][int(hash2(seed, 7, 3) * 5)]
    legs = {'walk': 'walk', 'stride': 'stride', 'skirt': 'skirt'}.get(pose, 'stand')
    if pose == 'stand' and hash2(seed, 8, 3) < 0.3:
        legs = 'skirt'
    arm = {'up': 'up', 'out': 'out', 'both': 'both'}.get(pose)
    rows = body(over.pop('hair', hair), over.pop('torso', torso), over.pop('legs', legs), arm)
    if pose == 'back':
        rows = [r.replace('s', 'h') if i < 3 else r for i, r in enumerate(rows)]
    g = mkit.grid_from('\n'.join(rows), colours(seed, **over))
    return mkit.flipx(g) if facing == 'sw' else g

def kid(seed, pose='run', facing='se', **over):
    g = mkit.grid_from('\n'.join(KID[pose]), colours(seed + 77, **over))
    return mkit.flipx(g) if facing == 'sw' else g

# ---------------------------------------------------------------- the wedding (the hero)
BRIDE = """
.vvv..
vhhh..
vhsss.
vhsss.
v.ss..
vdddd.
vddddb
vdddbr
vdddd.
vddddd
ddddddd
ddddddd
ddddddd
"""
GROOM = """
.hhh.
hhsss
hssss
.sss.
qqwqq
qqwqq
qqqqq
sqqqs
.qqq.
.q.q.
.q.q.
.q.q.
.k.k.
"""
BRIDESMAID = """
.hhh.
hhsss
hssss
.sss.
.rrr.
rrrrr
srrrs
.rrr.
rrrrr
rrrrr
rrrrr
.s.s.
.f.f.
"""
THROWER = """
.hhh..s
hhsss.s
hssss.t
.sss..t
ttttttt
ttttt..
ttttt..
sttts..
.ppp...
.p.p...
.p.p...
.p.p...
.f.f...
"""
OFFICIANT = """
.ooo.
oosss
ossss
.sss.
qqqqq
qqwqq
qqqqq
sqqqs
qqqqq
qqqqq
qqqqq
qqqqq
.k.k.
"""

def wedding(name, seed=0, facing='se', **over):
    art = {'bride': BRIDE, 'groom': GROOM, 'maid': BRIDESMAID, 'thrower': THROWER, 'officiant': OFFICIANT}[name]
    k = colours(seed, **over)
    if name == 'bride':
        k.update({'d': 'white', 'v': 'g7', 'b': 'rose2', 'r': 'leaf1'})
    g = mkit.grid_from(art, k)
    return mkit.flipx(g) if facing == 'sw' else g

# ---------------------------------------------------------------- the band
TUBA = """
..ggg...
.gGGGg..
gGqqqGg.
gGqqqGg.
.gGGGg..
..gg.hh.
...ghsss
...gssss
..gg.ss.
.ggttttt
.gGtttt.
..gtttt.
...stts.
...ppp..
...p.p..
...p.p..
...f.f..
"""
TRUMPET = """
.hhh....
hhsss...
hssssggg
.sssg.gG
tttts...
ttttt...
ttttt...
sttts...
.ppp....
.p.p....
p...p...
p...p...
f...f...
"""
DRUM = """
.hhh..
hhsss.
hssss.
.sss..
tttts.
aaaaa.
acaca.
aaaaa.
saaas.
.ppp..
.p.p..
p...p.
f...f.
"""
TROMBONE = """
.hhh.....
hhsss....
hssssGggg
.sssgg..g
tttgs...g
ttttt....
ttttt....
sttts....
.ppp.....
.p.p.....
p...p....
p...p....
f...f....
"""
CYMBAL = """
.hhh..
hhsss.
hssss.
.sssg.
ggtgg.
ttttt.
ttttt.
sttts.
.ppp..
.p.p..
.p.p..
p...p.
f...f.
"""

def band(name, seed=0, facing='se'):
    """a bandsman in the uniform: red cap and tunic, dark trousers, 1 px gold buttons; brass gold."""
    art = {'tuba': TUBA, 'trumpet': TRUMPET, 'drum': DRUM, 'trombone': TROMBONE, 'cymbal': CYMBAL,
           'major': BODY_MAJOR}[name]
    rows = [r for r in art.strip('\n').splitlines() if r.strip()]
    rows = [r.strip() for r in rows]
    # the cap: the first hair row becomes the red cap
    for i, r in enumerate(rows):
        if 'h' in r:
            rows[i] = r.replace('h', 'T')
            break
    # gold buttons down the tunic's centre (1 px glints)
    done = 0
    for i, r in enumerate(rows):
        if 't' in r and done < 2 and r.count('t') >= 3:
            js = [j for j, c in enumerate(r) if c == 't']
            j = js[len(js) // 2]
            rows[i] = r[:j] + 'y' + r[j + 1:]
            done += 1
    k = colours(seed, t='tunic', T='tunic', p='g1', y='gold')
    g = mkit.grid_from('\n'.join(rows), k)
    return mkit.flipx(g) if facing == 'sw' else g

BODY_MAJOR = """
.....g
.hhh.G
hhsss.s
hssss.t
.sss..t
ttttttt
ttttt..
ttttt..
sttts..
.ppp...
.p.p...
p...p..
p...p..
f...f..
"""

ACCORDION = """
.hhh..
hhsss.
hssss.
.sss..
tqaqat
taqaqt
sqaqas
.ppp..
.p.p..
.p.p..
.p.p..
.f.f..
"""

UMBRELLA = """
..ccc..
.ccccc.
ccccccc
...p...
...p...
"""

HAT = """
.y.
qqq
"""

def accordionist(seed=0, facing='se'):
    k = colours(seed, t='leaf1', a='g6', q='g1')
    g = mkit.grid_from(ACCORDION, k)
    return mkit.flipx(g) if facing == 'sw' else g

def umbrella(paint='mint2'):
    return mkit.grid_from(UMBRELLA, {'c': paint, 'p': 'g1'})

def hat():
    return mkit.grid_from(HAT, {'y': 'gold', 'q': 'g1'})

# ---------------------------------------------------------------- stories
JUGGLER = """
y...m.r
.......
.s.hhh.s
.shhsss.s
..thssss.t
..ttsss.t
...ttTTt
...TTTT.
...tTTt.
...ppp..
...p.p..
...p.p..
...p.p..
...f.f..
"""
VENDOR_MELON = """
.hhh....
hhsss...
hssssmm.
.sssmmmm
ttttsmm.
tTTTt...
tTTTt...
sTTTs...
.ppp....
.p.p....
.p.p....
.p.p....
.f.f....
"""
FISHMONGER = """
.hhh..s
hhsss.s
hssss.t
.sss..t
tTTTttt
tTTTt..
tTTTt..
sTTTs..
.ppp...
.p.p...
.p.p...
.p.p...
.f.f...
"""
WAITER = """
.....aaa
.hhh.ss.
hhsss.s.
hssss.t.
.sss..t.
qqwqqtt.
qqwqq...
qqqqq...
sqqqs...
.qqq....
.q.q....
.q.q....
.k.k....
"""
SITTER = """
.hhh.
hhsss
hssss
.sss.
ttttt
ttttt
sttts
pppp.
pp.pp
f..ff
"""

def story(name, seed=0, facing='se', **over):
    art = {'juggler': JUGGLER, 'melon': VENDOR_MELON, 'fishmonger': FISHMONGER, 'waiter': WAITER, 'sitter': SITTER}[name]
    k = colours(seed, **over)
    if name in ('melon', 'fishmonger'):
        k['T'] = 'plaster2'
    if name == 'juggler':
        k.update({'t': 'mint2', 'T': 'ochre2', 'y': 'bread2', 'm': 'leaf2', 'r': 'sky2'})
    g = mkit.grid_from(art, k)
    return mkit.flipx(g) if facing == 'sw' else g

# ---------------------------------------------------------------- animals
DOG = """
.......nn..
nn....nnnSx
.nnnnnnnn.x
.nnnnnnn...
.n.n..n.n..
.n.n..n.n..
"""
DOG_KEY = {'n': 'brown2', 'S': 'g0', 'x': 'fishc'}
PIGEON_SIT = """
.oo.
oooo
.oo.
"""
PIGEON_UP = """
o...o
oo.oo
.ooo.
"""
PIGEON_DOWN = """
.ooo.
oo.oo
o...o
"""
PIGEON_GLIDE = """
oo.oo.
.oooo.
..o...
"""

def dog(facing='se'):
    g = mkit.grid_from(DOG, DOG_KEY)
    return mkit.flipx(g) if facing == 'sw' else g

def pigeon(kind='sit', facing='se', shade='g4'):
    art = {'sit': PIGEON_SIT, 'up': PIGEON_UP, 'down': PIGEON_DOWN, 'glide': PIGEON_GLIDE}[kind]
    g = mkit.grid_from(art, {'o': shade})
    return mkit.flipx(g) if facing == 'sw' else g
