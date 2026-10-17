#!/usr/bin/env python3
"""The kit on demand: topics, modules and functions, read from the source (ast, nothing heavy imported).

usage: pixelate tools                    every topic and module, one line each
       pixelate tools TOPIC [--style S]  the techniques for a subject (rain, 雨, fog, water, small lights),
                                         the same keywords routing uses; --style drops what S does not allow
       pixelate tools MODULE             the module's public functions and classes: signature, first doc line
       pixelate tools MODULE.func        the full signature and docstring (MODULE.Class.method works too)

A word that is both a topic and a module (water, sky) prints both. Modules in references/assets are
examples: read them to see how a finished thing was built, never call them.

    import kit
    print(kit.listing()); print(kit.topic('rain')); print(kit.module('post')); print(kit.member('post.Post.lightmap'))
"""
import ast, pathlib, sys

TOOLS = pathlib.Path(__file__).resolve().parent
KIT = TOOLS.parent
EXAMPLES_DIR = KIT / 'references' / 'assets'
sys.path.insert(0, str(TOOLS))
import route

SKIP = {'cli', 'mcp_server', 'setup_agents', 'kit'}          # the command line itself, not drawing code
CONDITIONS = {'lofi': 'lofi style only', 'iso': '2:1 iso projection', 'topdown': '3/4 top-down projection',
              'side': 'side projection', 'soft': 'styles with a light layer', 'strict': 'styles without a light layer',
              '!post:shaft': 'styles without the soft shaft (pastel-cell, the pixel-only styles)',
              '!iso': 'side and 3/4 top-down projections', 'nodither': 'styles without dither',
              'bayer': 'styles with Bayer dither'}

# composed generators (tools/recipes.py) offered for a topic before its primitives
RECIPES = {
    'rock': [('rock_face', 'strata ledges, lit lips, recesses, flakes and a frayed edge, never a masonry grid')],
    'water': [('pouring_fall', 'a waterfall that curls over its lip, widens raggedly and breaks into spray')],
    'sky': [('cloud_bank', 'three masses of very different width, flat undersides, lit top tier, no scallop row')],
    'buildings': [('Perspective', 'one- or two-point scaffold: receding edges, shrinking repeats, boxes')],
    'stairs and steps': [('Perspective', 'step edges and repeats that shrink toward the vanishing point')],
    'crowds': [('crowd_vignettes', 'people as groups (ring, line, cluster) with poses and open ground between')],
    'figures': [('crowd_vignettes', 'place several figures as small scenes, not confetti')],
    'procession': [('crowd_vignettes', "a 'line' group: a file of walkers facing one way, unevenly spaced")],
}

# ---------------------------------------------------------------- source
def _path(mod):
    for d in (TOOLS, EXAMPLES_DIR):
        p = d / (mod + '.py')
        if p.exists():
            return p
    return None

def _tree(mod):
    p = _path(mod)
    return ast.parse(p.read_text(encoding='utf-8')) if p else None

def _first(doc, n=200):
    d = ' '.join((doc or '').strip().split('\n\n')[0].split())
    return d if len(d) <= n else d[:n - 3].rsplit(' ', 1)[0] + '...'

def _args(fn, drop_self=False, short=False):
    if short:                                   # names only: the listing stays small, NAME gives defaults
        x = fn.args
        a = ', '.join([v.arg for v in x.posonlyargs + x.args] + (['*' + x.vararg.arg] if x.vararg else
                      (['*'] if x.kwonlyargs else [])) + [v.arg for v in x.kwonlyargs] +
                      (['**' + x.kwarg.arg] if x.kwarg else []))
    else:
        a = ast.unparse(fn.args)
    if drop_self:
        parts = [x.strip() for x in a.split(',')] if a else []
        if parts and parts[0] in ('self', 'cls'):
            a = a.split(',', 1)[1].strip() if ',' in a else ''
    return '(%s)' % a

def _public(tree):
    return [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and not n.name.startswith('_')]

def _methods(cls):
    return [n for n in cls.body if isinstance(n, ast.FunctionDef) and not n.name.startswith('_')]

def _sig(node, owner=None, short=False):
    if isinstance(node, ast.ClassDef):
        init = next((n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == '__init__'), None)
        return node.name + (_args(init, True, short) if init else '()')
    return node.name + _args(node, owner is not None, short)

def modules():
    """-> [(name, line, is_example)]: the catalogued modules with their summaries, the other tools/*.py
    by their docstrings, then the references/assets examples"""
    out, seen = [], set()
    for m, what in route.CATALOG:
        out.append((m, what, False)); seen.add(m)
    for p in sorted(TOOLS.glob('*.py')):
        m = p.stem
        if m in seen or m in SKIP:
            continue
        t = ast.parse(p.read_text(encoding='utf-8'))
        out.append((m, _first(ast.get_docstring(t), 110) or '-', False)); seen.add(m)
    for m, what in route.EXAMPLES:
        out.append((m, what, True))
    return out

# ---------------------------------------------------------------- views
def listing():
    L = ['Topics (`pixelate tools TOPIC`; any keyword routing uses works, English or Chinese):']
    for words, label, items in route.TOPIC_TOOLS:
        L.append('  %-16s %s' % (label, ', '.join(words[:8]) + (', ...' if len(words) > 8 else '')))
    L += ['', 'Modules (`pixelate tools MODULE`, then `pixelate tools MODULE.func`):']
    ex = False
    for m, what, is_ex in modules():
        if is_ex and not ex:
            L += ['', 'Examples in references/assets (read them, never call them):']
            ex = True
        L.append('  %-12s %s' % (m, what))
    L += ['', 'Always: ' + route.ALWAYS_TOOLS + '.']
    return '\n'.join(L) + '\n'

def find_topics(q):
    t = ' ' + q.lower() + ' '
    ql = q.lower().strip()
    return [x for x in route.TOPIC_TOOLS if ql == x[1] or ql in x[1].split(' and ') or route._hits(t, x[0])]

def topic(q, style=None):
    """the techniques for every topic the query names, filtered to what `style` allows"""
    hits = find_topics(q)
    if not hits:
        return None
    L = []
    for words, label, items in hits:
        L.append('# %s  (keywords: %s)%s' % (label, ', '.join(words), ('  [style %s]' % style) if style else ''))
        for it in items:
            if isinstance(it, tuple):
                text, cond = it
                if style:
                    st = route.styles.get(style)['name']
                    if not route._fits(cond, st, route.ROUTE[st]['projection']):
                        continue
                    L.append('- ' + text)
                else:
                    why = CONDITIONS.get(cond) or ('styles that allow the %s light op' % cond[5:]
                                                   if cond.startswith('post:') else '%s style only' % cond[6:]
                                                   if cond.startswith('style:') else cond)
                    L.append('- %s  [%s]' % (text, why))
            else:
                L.append('- ' + it)
        for name, line in RECIPES.get(label, ()):
            L.append('- recipe `recipes.%s`: %s' % (name, line))
        L.append('')
    L.append('Signatures: `pixelate tools MODULE.func` (recipes: `pixelate tools recipes`). Check the result with '
             '`pixelate judge FRAME.png`. Rules for drawing it: references/drawing.md. '
             'Always: ' + route.ALWAYS_TOOLS + '.')
    return '\n'.join(L) + '\n'

def module(mod):
    tree = _tree(mod)
    if tree is None:
        return None
    is_ex = _path(mod).parent == EXAMPLES_DIR
    head = _first(ast.get_docstring(tree), 400)
    L = ['# %s  (%s)' % (mod, _path(mod).relative_to(KIT)), '']
    if is_ex:
        L += ['An example in references/assets: read it to see how a finished thing was built, never call it.', '']
    if head:
        L += [head, '']
    for n in _public(tree):
        d = _first(ast.get_docstring(n), 110)
        L.append('- %s%s' % (_sig(n, short=True), (': ' + d) if d else ''))
        if isinstance(n, ast.ClassDef):
            for f in _methods(n):
                fd = _first(ast.get_docstring(f), 90)
                L.append('  - .%s%s' % (_sig(f, n, short=True), (': ' + fd) if fd else ''))
    L += ['', 'Defaults and the full docstring: `pixelate tools %s.NAME`.' % mod]
    return '\n'.join(L) + '\n'

def member(ref):
    mod, *path = ref.split('.')
    tree = _tree(mod)
    if tree is None or not path:
        return None
    node, owner = tree, None
    for k in path:
        body = node.body
        nxt = next((n for n in body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == k), None)
        if nxt is None:
            return None
        owner = node if isinstance(node, ast.ClassDef) else None
        node = nxt
    L = ['%s.%s%s' % (mod, '.'.join(path[:-1]) + '.' if path[:-1] else '', _sig(node, owner)), '']
    L.append(ast.get_docstring(node) or '(no docstring)')
    if isinstance(node, ast.ClassDef):
        L += ['', 'methods:']
        for f in _methods(node):
            L.append('  .%s%s' % (_sig(f, node), (': ' + _first(ast.get_docstring(f), 160)) if ast.get_docstring(f) else ''))
    L.append('')
    L.append('source: %s line %d' % (_path(mod).relative_to(KIT), node.lineno))
    return '\n'.join(L) + '\n'

def query(q='', style=None):
    """the CLI and MCP entry point: '' lists, a topic word, a module, or module.name"""
    q = (q or '').strip()
    if not q:
        return listing()
    if '.' in q and _path(q.split('.')[0]):
        return member(q) or ('no %s: try `pixelate tools %s`\n' % (q, q.split('.')[0]))
    t = topic(q, style)
    parts = [x for x in (t, module(q) if _path(q) and not (t and style) else None) if x]   # with --style, a topic wins
    if parts:
        return '\n'.join(parts)
    return 'no topic or module for %r; topics: %s. `pixelate tools` lists the modules too.\n' % (
        q, ', '.join(label for _, label, _ in route.TOPIC_TOOLS))

def main(a):
    if a and a[0] in ('-h', '--help'):
        print(__doc__); return 0
    style = None
    if '--style' in a:
        i = a.index('--style'); style = a[i + 1]; del a[i:i + 2]
    out = query(' '.join(a), style)
    print(out, end='')
    return 1 if out.startswith('no topic or module for') else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
