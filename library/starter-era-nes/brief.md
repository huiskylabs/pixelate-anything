# Starter: Era NES

A neutral scaffold for one NES-style screen that keeps the console's limits. It draws no subject
of its own: replace every placeholder tile and sprite with the screen the request asks for, then
rewrite this brief for it. Make original work: no cast, world, name, logo or signature object
from an existing game (guides/eras.md).

## Intent

- What it is now: a side-view screen with a status bar (three pips and an empty gauge), a plain
  sky with a checker-dithered lower band, a flat far strip, flat ground, a foreground strip, one
  floating placeholder platform and one 16x16 placeholder marker sprite standing on the ground.
- What to make of it: a title, a level, a menu or any other screen held to NES limits.

## Composition

- Status bar in tile rows 0-3; sky to row 13; dithered band and far strip in rows 14-17; ground
  from row 18; foreground strip from row 24.
- The marker sprite stands on the ground at x 56; the platform floats at tile column 20, row 10.
- No hero is declared: a neutral placeholder is not meant to hold the frame's focus. Once a
  subject exists, add its Hero line (box, peak value) so the gate's focus checks run.

## Palette

- `art/nespal.py`: one shared backdrop, four background sub-palettes of three colours (sky band
  and far strip, ground, platform, status bar) and one sprite palette of three colours, all from
  the 2C02 master palette (`palettes/nes.hex`); 13 colours on screen of the 25 allowed.

## Technical

- Screen: the kit's `nes` preset, 256x224 at 1x (the 224 lines an NTSC set shows of the
  256x240 picture the console draws), delivered at 3x (768x672) as `out/screen.png`.
- Background: a 32x28 nametable of 8x8 tiles; every 16x16 attribute block uses one sub-palette
  plus the backdrop; at most 256 unique tiles.
- Sprites: 8x8 hardware sprites of 3 colours plus transparent, at most 8 per scanline and 64 in
  all; the marker is 4 of them.
- Gate: `pixelate check out/screen.png --era nes --style lofi --scale 3 --pal out/palette.json
  --brief brief.md`. The era replaces the value budget; `lofi` supplies only the craft and
  composition limits.
- Background alone: `pixelate era out/bg.png --era nes --layer bg --tiles` (the per-block rule).
- Gate override: none
