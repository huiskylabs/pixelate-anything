# Starter: Era NES: notes (phase 2)

New on 2026-10-18 as one of the three starters planned in docs/PLAN-library.md section 6.2. These are build facts, not a review: nobody has reviewed or approved this piece, and a passing check is not approval.

## What it draws

A status bar (three pips, an empty gauge), a plain sky in the backdrop colour with a checker-dithered lower band, a flat far strip in two heights, flat ground, a foreground strip, one floating placeholder platform and one 16x16 placeholder marker sprite. No authored subject and nothing taken from an existing game.

## How it keeps the limits

- Screen: the kit's `nes` preset, 256x224 (the NTSC-visible 224 lines of the 256x240 picture the console draws). The kit's era check fails any other size, so the starter uses it rather than 256x240.
- The renderer builds the picture as the hardware does: each 8x8 cell of a 32x28 nametable takes a tile from the pattern table, and its colours come from the sub-palette the attribute table gives its 16x16 block, plus the shared backdrop. A legal tile set and palette therefore give a legal background by construction.
- Sprites: four 8x8 hardware sprites (one 16x16 marker), each 3 colours plus transparent from one sprite palette, drawn after the background. `out/oam.json` lists their boxes.
- Colours: 13 on screen of 25, all from `palettes/nes.hex`; `art/nespal.py` stops the render if a colour is not in the kit's 2C02 palette.

## Checked (kit 1.0.0, Python 3.12.3, Pillow 12.3.0, numpy 2.5.4, SciPy 1.17.1, Linux x86_64)

- `python3 art/screen.py` in a lone clean copy writes `out/screen.png` (768x672, scale 3), `out/palette.json`, `out/bg.png` and `out/oam.json`; two runs give identical bytes. The golden `out/golden/screen.png` is the NEAREST 1x downsample (256x224) and reproduces the frame exactly.
- `pixelate check out/screen.png --era nes --scale 3`: ALL PASS (era nes: 13 colours, size, palette; 26 unique tiles of 256).
- The declared gate, `pixelate check out/screen.png --era nes --style lofi --scale 3 --pal out/palette.json --brief brief.md`: ALL PASS. `lofi` adds only its craft and composition limits (bottom third 77.8% empty of 88%); the era replaces the value budget.
- Background alone: `pixelate era out/bg.png --era nes --layer bg --tiles`: legal (every 16x16 block within 4 colours). Sprites: `era.check_sprites` on `out/oam.json`: no issue, 4 hardware sprites, at most 2 on a scanline.
- `pixelate library test starter-era-nes --quick`: ok, gate_ok, golden 0 px different. Its auxiliary `era` report runs `pixelate era` on the 3x frame without a scale, so it prints the 768x672 size; that is how `tools/render.py` calls it for every era piece, and era legality is decided by the gate's own `--era` lines, which pass.

Not checked: `pixelate judge`, `pixelate critique`, any human or art-director review, and sprite flicker or palette changes over time (it is one still).

## Licensing and provenance

No references or borrowed assets. First-party code under the repository MIT license. Media (`media/thumb.png`, `media/contact.png`) are made from the golden.
