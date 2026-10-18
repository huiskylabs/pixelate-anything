#!/usr/bin/env python3
"""Build static library gallery cards from the index, only for human-cleared entries.

A rights ledger is a publication allowlist, not a machine verification of permission. A maintainer
must inspect source rights before adding an entry. No piece commands or image decoders run here.
"""
import argparse
import html
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path

import library

KIT = Path(__file__).resolve().parent.parent
START = '<!-- library gallery: generated start -->'
END = '<!-- library gallery: generated end -->'
MAX_MEDIA = 2 * 1024 * 1024
EXTENSIONS = {'.png': b'\x89PNG\r\n\x1a\n', '.gif': b'GIF8', '.webp': b'RIFF'}


class GalleryError(ValueError):
    pass


def regular(path, limit=None):
    """Read a regular file without following a link; refuse oversize before allocating."""
    if path.is_symlink():
        raise GalleryError(f'{path}: link not allowed')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as file:
        info = os.fstat(file.fileno())
        if not stat.S_ISREG(info.st_mode) or (limit is not None and info.st_size > limit):
            raise GalleryError(f'{path}: not a regular file within {limit} bytes')
        data = file.read((limit + 1) if limit is not None else -1)
    if limit is not None and len(data) > limit:
        raise GalleryError(f'{path}: larger than {limit} bytes')
    return data


def permissions(path):
    try:
        ledger = json.loads(regular(path, 128 * 1024), object_pairs_hook=library.unique_pairs)
    except (OSError, UnicodeError, ValueError) as exc:
        raise GalleryError(f'{path}: invalid permissions ledger ({exc})') from None
    if not isinstance(ledger, dict) or set(ledger) != {'schema', 'pieces'} or ledger['schema'] != 1 or not isinstance(ledger['pieces'], dict):
        raise GalleryError('permissions ledger needs schema 1 and a pieces object')
    for piece_id, record in ledger['pieces'].items():
        library.slug(piece_id, 'gallery piece id')
        if not isinstance(record, dict) or set(record) != {'evidence'}:
            raise GalleryError(f'{piece_id}: expected an evidence path')
        library.relative(record['evidence'], f'{piece_id}.evidence')
    return ledger['pieces']


def cards(catalog, ledger):
    """(cards, media bytes) from a fresh deterministic index and explicit permission entries."""
    catalog = Path(catalog).absolute()
    if catalog.is_symlink():
        raise GalleryError('library root is a link')
    index = json.loads(regular(catalog / 'index.json', 2 * 1024 * 1024))
    if regular(catalog / 'index.json', 2 * 1024 * 1024) != library.index(catalog):
        raise GalleryError('index is stale: run pixelate library index on trusted code first')
    known = {entry['id']: entry for entry in index['pieces']}
    manifests = library.scan(catalog)
    if set(ledger) - set(known):
        raise GalleryError('permissions name unknown pieces: ' + ', '.join(sorted(set(ledger) - set(known))))
    entries, media = [], {}
    for piece_id in sorted(ledger):
        entry = known[piece_id]
        piece = catalog / piece_id
        evidence = piece / ledger[piece_id]['evidence']
        try:
            if not regular(evidence, 128 * 1024).strip():
                raise GalleryError(f'{evidence}: empty rights evidence')
        except OSError as exc:
            raise GalleryError(f'{evidence}: missing or unsafe rights evidence ({exc})') from None
        path = entry['media'].get('thumb')
        if path is None:
            raise GalleryError(f'{piece_id}: no declared thumbnail; keep it off the published gallery')
        path = path.removeprefix(piece_id + '/')
        ext = Path(path).suffix.lower()
        if ext not in EXTENSIONS:
            raise GalleryError(f'{piece_id}: thumbnail must be PNG, GIF or WebP')
        data = regular(piece / path, MAX_MEDIA)
        if not data.startswith(EXTENSIONS[ext]) or (ext == '.webp' and data[8:12] != b'WEBP'):
            raise GalleryError(f'{piece_id}: thumbnail magic does not match {ext}')
        name = f'{piece_id}{ext}'
        media[name] = data
        entries.append(dict(id=piece_id, title=entry['title'], summary=entry['summary'],
                            status=entry['status'], request=manifests[piece_id]['request'],
                            image=name, evidence=ledger[piece_id]['evidence']))
    return entries, media


def markdown(entries, prefix):
    def safe(value):
        value = ' '.join(str(value).split())
        return re.sub(r'([\\`*_{}\[\]()!|#<>])', r'\\\1', value)

    if not entries:
        return 'No library cards are published yet: source redistribution permissions still need human review.\n'
    lines = []
    for item in entries:
        title, piece_id = safe(item['title']), item['id']
        lines += [f'### {title} (`{piece_id}`)', '',
                  f"![{title}]({prefix}media/{item['image']})", '',
                  f"{safe(item['summary'])} **Declared status:** `{item['status']}` (not an art or rights certificate).", '',
                  f"**Request:** {safe(item['request'])}", '',
                  f'`pixelate remix {piece_id} work/YOUR-NAME --request "YOUR REQUEST"`', '',
                  'A rights-evidence path was recorded for this card; the ledger is not proof of permission.', '']
    return '\n'.join(lines).rstrip() + '\n'


def page(entries):
    blocks = []
    for item in entries:
        e = lambda value: html.escape(str(value), quote=True)
        blocks.append(f'<article><h2>{e(item["title"])}</h2><img src="media/{e(item["image"])}" '
                      f'alt="{e(item["title"])}"><p>{e(item["summary"])}</p>'
                      f'<p>Declared status: {e(item["status"])}; not an art or rights certificate.</p>'
                      f'<p>Request: {e(item["request"])}</p>'
                      f'<code>pixelate remix {e(item["id"])} work/YOUR-NAME --request "YOUR REQUEST"</code></article>')
    body = '\n'.join(blocks) if blocks else '<p>No cards published: redistribution permissions await human review.</p>'
    return ('<!doctype html>\n<html lang="en"><meta charset="utf-8"><title>pixelate-anything library</title>'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<style>body{font:1rem system-ui;max-width:64rem;margin:auto;padding:2rem;background:#141824;color:#eee}'
            'article{border:1px solid #667;padding:1rem;margin:1rem 0}img{max-width:100%;image-rendering:pixelated}'
            'code{display:block;overflow:auto;white-space:pre-wrap}</style><h1>Runnable pixel-art library</h1>'
            '<p>Each card links to its source program; no gate pass implies art quality, approval or rights.</p>'
            + body + '</html>\n')


def replace_generated(path, data):
    """Replace a generated file, never write through a hard link or a planted symlink."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise GalleryError(f'{path}: unsafe generated path')
    fd, temporary = tempfile.mkstemp(prefix='.gallery-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as file:
            file.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def build(catalog=KIT / 'library', ledger_path=KIT / 'docs/gallery/permissions.json', root=KIT, check=False):
    root = Path(root).absolute()
    if root.is_symlink() or any((root / name).is_symlink() for name in ('docs', 'docs/gallery', 'docs/gallery/media')):
        raise GalleryError('gallery root or parent is a link')
    ledger = permissions(Path(ledger_path))
    entries, media = cards(catalog, ledger)
    readme = root / 'README.md'
    text = regular(readme, 512 * 1024).decode('utf-8')
    if text.count(START) != 1 or text.count(END) != 1 or text.index(START) > text.index(END):
        raise GalleryError('README needs one ordered pair of gallery markers')
    body = markdown(entries, 'docs/gallery/')
    updated = text[:text.index(START)] + START + '\n## Library gallery\n\n' + body + END + text[text.index(END) + len(END):]
    desired = {readme: updated.encode('utf-8'), root / 'docs/gallery/library.md':
               ('# Runnable library gallery\n\n' + markdown(entries, '')).encode('utf-8'),
               root / 'docs/gallery/index.html': page(entries).encode('utf-8')}
    folder = root / 'docs/gallery/media'
    if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
        raise GalleryError(f'{folder}: unsafe media folder')
    existing = list(folder.iterdir()) if folder.exists() else []
    if any(p.is_symlink() or not p.is_file() or not re.fullmatch(r'[a-z0-9-]+\.(png|gif|webp)', p.name) for p in existing):
        raise GalleryError(f'{folder}: unexpected or unsafe file; do not overwrite it')
    desired.update({folder / name: data for name, data in media.items()})
    stale = set(existing) - {folder / name for name in media}
    if check:
        mismatches = [str(path) for path, data in desired.items() if not path.is_file() or regular(path) != data]
        mismatches.extend(str(path) for path in sorted(stale))
        if mismatches:
            raise GalleryError('gallery not generated: ' + ', '.join(mismatches))
    else:
        folder.mkdir(parents=True, exist_ok=True)
        for path in stale:
            path.unlink()
        for path, data in desired.items():
            replace_generated(path, data)
    return {'cards': len(entries), 'ids': [entry['id'] for entry in entries], 'withheld': len(json.loads(regular(Path(catalog) / 'index.json'))['pieces']) - len(entries)}


def main(argv=None):
    parser = argparse.ArgumentParser(prog='pixelate gallery', description=__doc__)
    parser.add_argument('--check', action='store_true', help='compare generated files; write nothing, run no piece code')
    args = parser.parse_args(argv)
    try:
        print(json.dumps(build(check=args.check), sort_keys=True))
    except (GalleryError, library.LibraryError, OSError, UnicodeError) as exc:
        parser.exit(1, f'gallery: {exc}\n')


if __name__ == '__main__':
    main()
