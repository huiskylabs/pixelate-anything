"""Chinese and Japanese text as pixels: dialogue lines, name plates, signs, titles.

The glyphs are Ark Pixel Font 12px by TakWolf (https://github.com/TakWolf/ark-pixel-font,
SIL OFL 1.1, see fonts/OFL.txt), subset to the 6,763 GB2312 hanzi, CJK punctuation, full-width
forms and kana: fonts/ark-pixel-12px.hex. Latin letters and digits fall back to the kit's 5x7 font
(tools/pixfont.py), set on the same baseline. Text goes into a PIL image (colours as RGB tuples)
or into anything with .set(x, y, v) (colours as palette slots).

    import cjkfont
    cjkfont.draw(img, '剑冢之下，埋着谁的名字？', 96, 24, (240, 228, 196), outline=(16, 12, 20))
    cjkfont.width('月下')                      # 24
    for i, line in enumerate(cjkfont.wrap(text, 200)):
        cjkfont.draw(img, line, x, y + i * cjkfont.LINE, colour)

The 90s RPG look: cream text with a dark 1 px outline straight over the picture, the speaker's
name in a cool accent colour above it, a blinking triangle when the line is done
(cjkfont.draw(img, '▼', ...)). Reveal a line a few characters per frame with draw(..., upto=n).
"""
import pathlib
import pixfont

KIT = pathlib.Path(__file__).resolve().parents[1]
FONT = KIT / 'fonts' / 'ark-pixel-12px.hex'
EM = 12          # glyph box
LINE = 16        # line height that leaves room for an outline
_G = None
NO_LINE_START = set('，。！？、；：）」』》〉…—～,.!?;:)')

def _load():
    global _G
    if _G is None:
        _G = {}
        for line in open(FONT, encoding='utf-8'):
            if line.startswith('#') or ':' not in line:
                continue
            cp, w, hx = line.strip().split(':')
            rows = [int(hx[i:i + 4], 16) for i in range(0, len(hx), 4)]
            if len(rows) > EM:                       # a few symbols come in a taller box: centre them
                k = (len(rows) - EM) // 2
                rows = rows[k:k + EM]
            _G[int(cp, 16)] = (int(w), rows)
    return _G

def glyph(ch):
    """(width, rows) with bit width-1 of each row the leftmost pixel; None if the font lacks it"""
    if ch == ' ':
        return (6, [0] * EM)
    if ord(ch) < 128:
        g = pixfont.GLYPHS.get(ch.upper() if ch.upper() in pixfont.GLYPHS else ch)
        if g is None:
            return None
        rows = [0, 0, 0]
        for r in g.split('|'):
            rows.append(sum(1 << (5 - i) for i, c in enumerate(r) if c == '#'))
        return (6, rows + [0] * (EM - len(rows)))
    return _load().get(ord(ch))

def advance(ch, spacing=0):
    g = glyph(ch)
    return (g[0] if g else EM) + spacing

def width(s, spacing=0):
    return max(0, sum(advance(c, spacing) for c in s) - spacing)

def wrap(s, max_w, spacing=0):
    """break a line to fit max_w pixels; CJK breaks anywhere, but a line never starts with closing
    punctuation (it stays on the line before)"""
    lines, cur = [], ''
    for ch in s:
        if ch == '\n':
            lines.append(cur); cur = ''; continue
        if cur and width(cur + ch, spacing) > max_w and ch not in NO_LINE_START:
            lines.append(cur); cur = ''
        cur += ch
    if cur:
        lines.append(cur)
    return lines

class _PilTarget:
    def __init__(self, img):
        self.px = img.load(); self.W, self.H = img.size
    def set(self, x, y, v):
        if 0 <= x < self.W and 0 <= y < self.H:
            self.px[x, y] = v

def draw(target, s, x, y, colour, shadow=None, outline=None, spacing=0, upto=None):
    """draw s with its top-left at (x, y). outline: a 1 px ring round every stroke (8 neighbours);
    shadow: a 1 px drop shadow down and right; upto: only the first n characters (typing effect).
    Returns the x after the last character."""
    tgt = target if hasattr(target, 'set') else _PilTarget(target)
    s = s if upto is None else s[:max(0, int(upto))]
    pts, cx = [], x
    for ch in s:
        g = glyph(ch) or glyph('？')
        w, rows = g
        for j, r in enumerate(rows):
            for i in range(w):
                if r >> (w - 1 - i) & 1:
                    pts.append((cx + i, y + j))
        cx += w + spacing
    if outline is not None:
        on = set(pts)
        for px, py in pts:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if (px + dx, py + dy) not in on:
                        tgt.set(px + dx, py + dy, outline)
    if shadow is not None:
        for px, py in pts:
            tgt.set(px + 1, py + 1, shadow)
    for px, py in pts:
        tgt.set(px, py, colour)
    return cx
