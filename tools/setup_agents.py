#!/usr/bin/env python3
"""pixelate setup: register the MCP server (and the skill) with your coding agents.

usage: pixelate setup [--yes] [--only claude,cursor,codex,gemini] [--dry-run]

  claude   `claude mcp add --scope user` + the skill linked into ~/.claude/skills/pixelate-anything
  cursor   ~/.cursor/mcp.json             mcpServers.pixelate-anything
  codex    ~/.codex/config.toml           [mcp_servers.pixelate-anything]
  gemini   ~/.gemini/settings.json        mcpServers.pixelate-anything
Shows the plan first and asks before changing anything; every edited file is backed up
next to itself (.bak-YYYYmmdd-HHMMSS). Restart the agent afterwards.
The server runs in the directory the agent starts it in (your project): outputs land there.
"""
import json, os, pathlib, shutil, subprocess, sys, time

KIT = pathlib.Path(__file__).resolve().parent.parent
NAME = 'pixelate-anything'
HOME = pathlib.Path.home()
CMD = [sys.executable, str(KIT / 'pixelate'), 'mcp']

def backup(p):
    if p.exists():
        b = p.with_name(p.name + '.bak-' + time.strftime('%Y%m%d-%H%M%S'))
        shutil.copy2(p, b)
        return b

def plan_claude():
    steps = []
    if shutil.which('claude'):
        steps.append(('run', ['claude', 'mcp', 'add', '--scope', 'user', NAME, '--'] + CMD))
    else:
        steps.append(('note', 'claude CLI not found: add the MCP server by hand: ' + ' '.join(CMD)))
    skills = HOME / '.claude' / 'skills' / NAME
    if not skills.exists():
        steps.append(('link', skills))
    return steps

def plan_json(path):
    return [('json', path)]

def plan_codex():
    return [('toml', HOME / '.codex' / 'config.toml')]

TARGETS = {
    'claude': (lambda: (HOME / '.claude').exists() or shutil.which('claude'), plan_claude),
    'cursor': (lambda: (HOME / '.cursor').exists(), lambda: plan_json(HOME / '.cursor' / 'mcp.json')),
    'codex': (lambda: (HOME / '.codex').exists() or shutil.which('codex'), plan_codex),
    'gemini': (lambda: (HOME / '.gemini').exists() or shutil.which('gemini'), lambda: plan_json(HOME / '.gemini' / 'settings.json')),
}

def describe(step):
    k, v = step
    return {'run': lambda: 'run: ' + ' '.join(map(str, v)), 'link': lambda: 'link skill: %s -> %s' % (v, KIT),
            'json': lambda: 'add mcpServers.%s to %s' % (NAME, v), 'toml': lambda: 'add [mcp_servers.%s] to %s' % (NAME, v),
            'note': lambda: v}[k]()

def apply(step):
    k, v = step
    if k == 'run':
        r = subprocess.run(v, capture_output=True, text=True)
        print('  ', (r.stdout + r.stderr).strip()[:300] or 'ok')
    elif k == 'link':
        v.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(KIT, v)
    elif k == 'json':
        v.parent.mkdir(parents=True, exist_ok=True)
        data = json.loads(v.read_text()) if v.exists() and v.read_text().strip() else {}
        b = backup(v)
        data.setdefault('mcpServers', {})[NAME] = {'command': CMD[0], 'args': CMD[1:]}
        v.write_text(json.dumps(data, indent=2) + '\n')
        if b: print('   backup:', b)
    elif k == 'toml':
        v.parent.mkdir(parents=True, exist_ok=True)
        text = v.read_text() if v.exists() else ''
        if '[mcp_servers.%s]' % NAME in text:
            print('   already present'); return
        b = backup(v)
        text += '\n[mcp_servers.%s]\ncommand = %s\nargs = %s\n' % (NAME, json.dumps(CMD[0]), json.dumps(CMD[1:]))
        v.write_text(text)
        if b: print('   backup:', b)
    elif k == 'note':
        pass

def main(a):
    if '-h' in a or '--help' in a:
        print(__doc__); return
    only = None
    if '--only' in a:
        only = a[a.index('--only') + 1].split(',')
    chosen = [t for t in TARGETS if (only is None and TARGETS[t][0]()) or (only and t in only)]
    if not chosen:
        print('no supported agents found (claude, cursor, codex, gemini). Register by hand:\n  ' + ' '.join(CMD)); return
    plan = [(t, s) for t in chosen for s in TARGETS[t][1]()]
    print('pixelate-anything setup will:')
    for t, s in plan:
        print('  [%s] %s' % (t, describe(s)))
    if '--dry-run' in a:
        return
    if '--yes' not in a:
        if input('proceed? [y/N] ').strip().lower() not in ('y', 'yes'):
            print('nothing changed'); return
    for t, s in plan:
        print('[%s] %s' % (t, describe(s)))
        apply(s)
    print('done. Restart your agents; then ask for pixel art (try: "pixelate this photo", "make a sprite pack", "make a lofi loop video").')

if __name__ == '__main__':
    main(sys.argv[1:])
