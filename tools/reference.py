#!/usr/bin/env python3
"""Inspect a rebuild reference without pretending to infer its camera or subject.

pixelate reference PHOTO -o reference.json [--marks reference.json]

The JSON is a correctable observation record; re-run with --marks after adding a horizon,
vanishing points or landmark boxes. Values and edge directions are measurements, not an art
score. The overlay shows sampled edges and any manual marks against the original photo.
"""
import argparse
import hashlib
import json
import math
import pathlib

import numpy as np
from PIL import Image, ImageDraw, ImageOps


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    return float(value)


def annotations(path, source_hash, size):
    camera = {'projection': 'unknown', 'horizon_y': None, 'vanishing_points': [], 'notes': ''}
    if not path:
        return camera, []
    data = json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError('marks must be a JSON object')
    if data.get('source_sha256') and data['source_sha256'] != source_hash:
        raise ValueError('marks belong to another photo (source_sha256 differs)')
    raw = data.get('camera', {})
    if not isinstance(raw, dict) or raw.get('projection', 'unknown') not in (
            'unknown', 'orthographic', 'one-point', 'two-point', 'other'):
        raise ValueError('camera.projection must name a supported projection')
    camera['projection'] = raw.get('projection', 'unknown')
    if raw.get('horizon_y') is not None:
        camera['horizon_y'] = number(raw['horizon_y'], 'camera.horizon_y')
    points = raw.get('vanishing_points', [])
    if not isinstance(points, list) or len(points) > 2:
        raise ValueError('camera.vanishing_points must be a list of up to two points')
    for point in points:
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError('each vanishing point must be [x, y] in photo pixels')
        camera['vanishing_points'].append([number(point[0], 'vanishing x'), number(point[1], 'vanishing y')])
    if not isinstance(raw.get('notes', ''), str):
        raise ValueError('camera.notes must be text')
    camera['notes'] = raw.get('notes', '')
    landmarks = data.get('landmarks', [])
    if not isinstance(landmarks, list) or len(landmarks) > 32:
        raise ValueError('landmarks must be a list of at most 32 boxes')
    normalized = []
    for entry in landmarks:
        if not isinstance(entry, dict) or not isinstance(entry.get('name'), str) or not entry['name'].strip():
            raise ValueError('each landmark needs a nonempty name')
        box = entry.get('box')
        if not isinstance(box, list) or len(box) != 4:
            raise ValueError('landmark.box must be [x0, y0, x1, y1]')
        x0, y0, x1, y1 = [number(v, 'landmark coordinate') for v in box]
        if not (0 <= x0 < x1 <= size[0] and 0 <= y0 < y1 <= size[1]):
            raise ValueError('landmark box must be inside the photo')
        normalized.append({'name': entry['name'].strip()[:80], 'box': [x0, y0, x1, y1]})
    return camera, normalized


def observe(photo, marks=None):
    photo = pathlib.Path(photo).resolve()
    source_hash = digest(photo)
    with Image.open(photo) as opened:
        image = ImageOps.exif_transpose(opened).convert('RGB')
    sample = image.copy()
    sample.thumbnail((512, 512), Image.Resampling.BOX)
    values = np.asarray(sample.convert('L'), dtype=np.float32)
    bands = [int((values < 85).sum()), int(((values >= 85) & (values < 170)).sum()),
             int((values >= 170).sum())]
    fractions = [round(count / values.size, 4) for count in bands]
    value_map = np.asarray(sample.convert('L').resize((12, 12), Image.Resampling.BOX), dtype=np.uint8).tolist()

    if min(values.shape) < 2:
        gy = np.zeros_like(values)
        gx = np.zeros_like(values)
    else:
        gy = np.gradient(values, axis=0)
        gx = np.gradient(values, axis=1)
    strength = np.hypot(gx, gy)
    threshold = max(20.0, float(np.quantile(strength, 0.9)))
    edges = strength > threshold
    angles = []
    if int(edges.sum()) >= 30:
        directions = (np.degrees(np.arctan2(gy[edges], gx[edges])) + 90) % 180
        weights, _ = np.histogram(directions, bins=np.arange(0, 181, 15), weights=strength[edges])
        for index in np.argsort(weights)[-2:][::-1]:
            if weights[index] > 0:
                angles.append({'direction_deg': int(index * 15 + 7.5),
                               'edge_weight_share': round(float(weights[index] / weights.sum()), 3)})
    camera, landmarks = annotations(marks, source_hash, image.size)
    record = {'schema': 1, 'source': str(photo), 'source_sha256': source_hash,
              'size': list(image.size), 'sample_size': list(sample.size),
              'value_evidence': {'bands': ['dark', 'middle', 'light'], 'fractions': fractions,
                                 'luma_grid_12x12': value_map,
                                 'method': 'Pillow L on a <=512px thumbnail; fixed 0..84, 85..169, 170..255 bins'},
              'edge_evidence': {'sampled_edge_pixels': int(edges.sum()), 'directions': angles,
                                'method': 'local gradient directions in 15-degree bins; not vanishing points'},
              'camera': camera, 'landmarks': landmarks,
              'unknowns': ['camera and horizon are not inferred', 'silhouettes and focal point are not inferred',
                           'value and edge measurements are not an aesthetic or fidelity score']}
    return record, image, edges


def overlay(image, edges, record, output):
    mask = Image.fromarray(edges.astype(np.uint8) * 90).resize(image.size, Image.Resampling.NEAREST)
    tint = Image.new('RGBA', image.size, (255, 0, 200, 0))
    tint.putalpha(mask)
    result = Image.alpha_composite(image.convert('RGBA'), tint).convert('RGB')
    draw = ImageDraw.Draw(result)
    w, h = image.size
    horizon = record['camera']['horizon_y']
    if horizon is not None and 0 <= horizon < h:
        draw.line((0, horizon, w - 1, horizon), fill=(0, 255, 255), width=max(1, w // 500))
    for x, y in record['camera']['vanishing_points']:
        if 0 <= x < w and 0 <= y < h:
            r = max(3, w // 200)
            draw.ellipse((x - r, y - r, x + r, y + r), outline=(0, 255, 255), width=2)
    for entry in record['landmarks']:
        box = entry['box']
        draw.rectangle(box, outline=(255, 220, 0), width=max(1, w // 500))
        draw.text((box[0] + 2, max(0, box[1] - 12)), entry['name'], fill=(255, 220, 0))
    result.save(output)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='pixelate reference', description=__doc__)
    parser.add_argument('photo', help='source photo, not the pixel-art render')
    parser.add_argument('-o', '--out', required=True, help='editable JSON observation record')
    parser.add_argument('--marks', help='JSON with camera and landmark marks; may be the previous --out')
    args = parser.parse_args(argv)
    out = pathlib.Path(args.out).resolve()
    if out.suffix.lower() != '.json':
        parser.error('--out must be a .json file')
    try:
        record, image, edges = observe(args.photo, args.marks)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    out.parent.mkdir(parents=True, exist_ok=True)
    picture = out.with_suffix('.overlay.png')
    overlay(image, edges, record, picture)
    record['overlay'] = str(picture)
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"{out}: {record['size'][0]}x{record['size'][1]}, photo SHA-256 {record['source_sha256'][:12]}")
    print(f"value bands dark/middle/light: {record['value_evidence']['fractions']}; "
          f"edge directions: {record['edge_evidence']['directions']}")
    print(f"camera: {record['camera']['projection']} (manual marks); overlay: {picture}")


if __name__ == '__main__':
    main()
