"""The bog-ferrier, 16x24, pivot at the feet (8, 23).

One base drawing (FRONT) holds every part, each part typed with its own characters so code can
lift it: the pole (P p O), the lantern (N g G Q n), the body. Every other frame comes from it:

  back   = the base mirrored and relit (lit and shade tones swap so the light stays upper left),
           with the face and beard rows overwritten by hair and the coat's back.
  side   = typed on the same row plan (hat 1-7, face 8-10, beard 11-12, coat 13-19, legs 20-23)
           so the same part moves animate it; its stride legs are a 4-pose cycle.
  idle   = 3 frames: base; out-breath (hat, face and shoulders sink 1 px, the lantern swings
           1 px); the lantern swings back and its flame flickers (Q <-> G).
  walk   = 4 frames: contact, passing (body up 1 px, a boot lifted, the lantern lags), contact,
           passing (other boot).
"""
from mire_kit import grid_from, copy, over
from artlib import Grid

W, H = 16, 24
AX, AY = 8, 23

KEY = {
    'o': 'ol', 'e': 'ol',
    'H': 'reed2', 'h': 'reed1', 'd': 'reed0',
    'F': 'skin1', 'f': 'skin0',
    'S': 'mist2', 's': 'mist1', 'm': 'mist0',
    'C': 'coat2', 'c': 'coat1', 'k': 'coat0', 'K': 'coat0',
    'b': 'peat0', 'Y': 'gold2',
    'W': 'peat2', 'w': 'peat1', 'v': 'peat0',
    'P': 'wood2', 'p': 'wood0', 'O': 'ol',
    'N': 'ol', 'g': 'gold1', 'G': 'gold2', 'Q': 'flame', 'n': 'gold0',
}
POLE = set('PpO')
LANTERN = set('NgGQn')
RELIGHT = {'C': 'k', 'k': 'C', 'H': 'd', 'd': 'H', 'W': 'v', 'v': 'W', 'P': 'p', 'p': 'P',
           'F': 'f', 'f': 'F'}

FRONT = """
.OO.............
.Pp...oooo......
.Pp..oHHhdo.....
.Pp.ooHhhddo....
.PpoHHHhhhddo...
.PoHHhhhhhhddo..
.Pohhhhhhhdddo..
.Ppoooooooooo...
.Pp..offfffo....
.Pp..oFeFefo....
.Pp..oFSSSfo....
.Pp.oCSSSskko...
.PpoCCCSsckko...
.PoCCoCccckkko..
.oFFoCCccckoFfo.
.oFfobbbYbbo.N..
.PpoCCccKckNngnN
.PpoCCccKckNQQGN
.PpoCCccKckNQQGN
.PpoCCccKckNnnnN
.Pp.oWwoWvo.NNN.
.Pp.oWwoWvo.....
.PpoWwvoWwvo....
.Ppooooooooo....
"""

# rows of the back view typed over the relit mirror ('.' keeps what is there)
BACK_OVER = {
    8:  "....owwwwwo.....",
    9:  "....oWwwwvo.....",
    10: "....oWwwvvo.....",
    11: "...oCCCcckko....",
    12: "...oCCCcKckko...",
    13: "....oCccKcko....",
    15: "....obbbbbbo....",
}

SIDE = """
.OO.............
.Pp.............
.Pp....oooo.....
.Pp...oHHhdo....
.Pp.ooHHhhddoo..
.PoHHHhhhhhhddo.
.Pohhhhhhhhdddo.
.Pp.oooooooooo..
.Pp....offFFo...
.Pp....offFeo...
.Pp....ofSSSFo..
.Pp...oCSSSso...
.Pp..oCCcSsko...
.Pp..oCCcckkoo..
.Pp..oCCcckFFoN.
.Pp..obbbYboNgN.
.Pp..oCCcKcNngnN
.Pp..oCCcKcNQQGN
.Pp..oCCcKcNQQGN
.Pp..oCCcKcNnnnN
.Pp...oWwvo.NNN.
.Pp...oWwvo.....
.Pp...oWwvvo....
.Pp...oooooo....
"""

# side stride: rows 20-23 for contact (near leg forward), passing, contact (far leg forward), passing
SIDE_LEGS = [
    ["......oWvo......",
     ".....oWoovo.....",
     "....oWwo.ovvo...",
     "....oooo..oooo.."],
    ["......oWwvo.....",
     "......oWovo.....",
     "......oWvwo.....",
     "......oooooo...."],
    ["......ovWo......",
     ".....ovooWo.....",
     "....ovvo.oWwo...",
     "....oooo..oooo.."],
    ["......ovWwo.....",
     "......ovoWo.....",
     "......ovoWwo....",
     "......ooooooo..."],
]


def chars(art):
    return grid_from(art, {c: c for c in KEY})


def base(view):
    if view == 'front':
        return chars(FRONT)
    if view == 'side':
        return chars(SIDE)
    if view == 'back':
        f = chars(FRONT)
        g = Grid(W, H)
        for y in range(H):
            for x in range(W):
                v = f.a[y][W - 1 - x]
                g.a[y][x] = RELIGHT.get(v, v) if v is not None else None
        for y, row in BACK_OVER.items():
            for x, c in enumerate(row):
                if c != '.':
                    g.a[y][x] = c
        return g
    raise ValueError(view)


def layer(g, cs, keep):
    out = Grid(g.w, g.h)
    for y in range(g.h):
        for x in range(g.w):
            v = g.a[y][x]
            if v is not None and ((v in cs) == keep):
                out.a[y][x] = v
    return out


def shift(g, dx=0, dy=0, y0=0, y1=None):
    """copy of g with rows y0..y1 moved by (dx, dy); the vacated rows clear"""
    y1 = g.h - 1 if y1 is None else y1
    out = copy(g)
    for y in range(y0, y1 + 1):
        out.a[y] = [None] * g.w
    for y in range(y0, y1 + 1):
        for x in range(g.w):
            v = g.a[y][x]
            X, Y = x + dx, y + dy
            if v is not None and 0 <= X < g.w and 0 <= Y < g.h:
                out.a[Y][X] = v
    return out


def to_slots(g):
    out = Grid(g.w, g.h)
    for y in range(g.h):
        for x in range(g.w):
            v = g.a[y][x]
            if v is not None:
                out.a[y][x] = KEY[v]
    return out


def compose(body, pole, lant):
    out = Grid(W, H)
    over(out, pole)
    over(out, body)
    over(out, lant)
    return out


def parts(view):
    g = base(view)
    return layer(g, POLE, True), layer(g, LANTERN, True), layer(g, POLE | LANTERN, False)


def idle(view):
    pole, lant, body = parts(view)
    sway = -1 if view == 'back' else 1
    f0 = compose(body, pole, lant)
    sunk = shift(body, 0, 1, 0, 13)                 # out-breath: hat, face, shoulders sink 1 px
    sunk.a[0] = [None] * W
    f1 = compose(sunk, pole, shift(lant, sway, 0))
    flick = {'Q': 'G', 'G': 'Q'}
    lant2 = Grid(W, H)
    for y in range(H):
        for x in range(W):
            v = lant.a[y][x]
            if v is not None:
                lant2.a[y][x] = flick.get(v, v)
    f2 = compose(sunk, pole, lant2)
    return [to_slots(f) for f in (f0, f1, f2)]


def walk(view):
    pole, lant, body = parts(view)
    frames = []
    for i in range(4):
        b = copy(body)
        if view == 'side':
            for j, row in enumerate(SIDE_LEGS[i]):
                b.a[20 + j] = [c if c != '.' else None for c in row]
        if i % 2 == 0:
            frames.append(compose(b, pole, lant))
            continue
        up = shift(b, 0, -1, 0, 19)                 # the body rises with the passing leg
        up.a[19] = b.a[20][:]
        if view != 'side':                          # front and back: the passing boot lifts
            xs = range(3, 8) if i == 1 else range(7, 12)
            for x in xs:
                up.a[20][x] = b.a[21][x]
                up.a[21][x] = b.a[22][x]
                up.a[22][x] = b.a[23][x]
                up.a[23][x] = None
            for x in range(3, 12):                  # keep the shared outline column whole
                if up.a[23][x] is None and b.a[23][x] is not None and x not in xs:
                    up.a[23][x] = b.a[23][x]
        lag = -1 if (view == 'side' or i == 1) else 0
        frames.append(compose(up, shift(pole, 0, -1), shift(lant, lag, -1)))
    return [to_slots(f) for f in frames]


def export():
    out = []
    for view in ('front', 'back', 'side'):
        out.append(('sprite', 'ferrier_idle_' + view, idle(view), AX, AY,
                    {'durations': [600, 420, 480], 'tags': {'idle': (0, 2)}}))
        out.append(('sprite', 'ferrier_walk_' + view, walk(view), AX, AY,
                    {'fps': 8, 'tags': {'walk': (0, 3)}}))
    return out
