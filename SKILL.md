---
name: pixel-loop
description: Make hand-crafted pixel-art animated loops with a generative lofi soundtrack (seasons, day and night, weather or any set of moods) and export them as a live HTML page and crisp 1080p or 4K MP4 that loops seamlessly. Use for lofi video covers, ambient loops, pixel-art scenes, YouTube or social loops.
---

# pixel-loop

Build a scene that cycles through moods ("phases": seasons, times of day, weather),
with music whose chords, tempo and instruments change with each phase and blend
like a DJ set. The result loops exactly: picture and music repeat with no seam, so
one short file can be put on repeat for hours.

The engine does the hard, mechanical parts (exact looping, dithered phase
dissolves, palette rendering, the soundtrack, encoding). **You** do the art: the
palettes, the sprites, the composition and the small lived-in details. The quality
of the result is the quality of that art, so most of the work is there.

Reference: `examples/lantern-isle` is a finished scene (an island cottage through
four seasons). Read its files when you need to see how something is done well.

## Requirements

`node` (18+), `python3` with `pillow` and `numpy`, `ffmpeg` with libx264, and
Playwright's Chromium (`pip install playwright && playwright install chromium`;
needed for the soundtrack and the page check). Check with `node -v; ffmpeg -version | head -1`.

## Workflow

1. **Settle the brief** (ask only what you cannot infer):
   - subject and setting
   - phases: 2 to 6, each with a mood, a palette idea, signature elements and its music
   - canvas
   - output: page, MP4 or both

   Canvas sizes by aspect:
   - 16:9: `240x135` (8x = 1080p, 16x = 4K), `320x180` (6x / 12x) or `480x270` (4x / 8x). Smaller canvases mean bigger, chunkier pixels and less art to draw.
   - Square: `270x270` or `360x360`.
   - Vertical: `270x480`.

   Pick the canvas so the subject fills the frame.

2. **Start from the template.** `cp -r <skill>/templates/starter <workdir>/<scene>`.
   Read `references/scene-contract.md` once: files, `SCENE` fields, hooks, engine API.

3. **Palettes first** (`palettes.js`). Read `references/craft.md` before choosing colours.
   - One strict palette per phase, slots with fixed roles: the same slot means the same material in every phase, so a sprite drawn once reads correctly in all of them.
   - 3 to 5 tones per material, hue-shifted (shadows cooler and more saturated, lights warmer), never pure black or white.

4. **Draw the sprites** (`sprites.js`, `def(name, key, rows)`). Hand-place every pixel.
   - Outlines and lit edges come from one light direction.
   - Small signature details tell the story (a cat on a sill, a mug, footprints).
   - For organic or repeated shapes (terrain, canopies, snow overlays), write Python with `tools/artlib.py` in `<scene>/art/*.py` and run `python3 <skill>/tools/gen_sprites.py <scene>`.
   - Preview constantly.

5. **Compose and animate** (`scene.js` hooks). Follow the loop rules below.
   - Background: gradients with `bands()`.
   - Objects: `blit` into `OB`.
   - Light and reflection: `sceneAfterObjects`.
   - Flicker by swapping palette entries: `sceneDynamic`.
   - Weather: `sceneParticles`.

6. **Write the music** (`music.js`). Read `references/music.md`.
   - Give each phase its own key, chords, tempo, swing, lead instrument, drum feel and ambience.
   - Give each turnaround a ii-V into the next phase's first chord.

7. **Look and check, every iteration:**
   ```
   python3 <skill>/tools/shot.py <scene> 5 30 55 80 --grid --zoom 3    # then view the PNGs
   python3 <skill>/tools/check.py <scene> --page
   ```
   View every shot yourself, at zoom, in every phase and mid-transition. Fix what looks off before adding more. `check.py` must say ALL OK.

8. **Deliver:**
   ```
   python3 <skill>/tools/build.py <scene> --release                # one self-contained HTML page
   python3 <skill>/tools/render_audio.py <scene> <scene>/loop.wav  # one seamless loop of the music
   python3 <skill>/tools/render_video.py <scene> out-1080p.mp4 --audio <scene>/loop.wav
   python3 <skill>/tools/render_video.py <scene> out-4k.mp4 --scale 16 --audio <scene>/loop.wav  # 240x135 -> 4K
   ```
   The page plays live generative music after a tap on the play button and runs forever. The MP4 is one exact loop (`cycle x grand` seconds) to put on repeat. Use a scale that is a whole, even number so pixels stay square and colours stay exact.

   Costs on 2 cores:
   - **2 minute loop:** about 1 minute for the soundtrack and 2 minutes for the 1080p encode.
   - **6 minute loop:** about 8 minutes for the soundtrack, and around 20 minutes for the 4K encode.

## Loop rules (the engine relies on them)

- Everything on screen is a pure function of the tick `k` (30 per second): use `hash`/`hash2`/`hash3`, never `Math.random`, and no state carried between frames.
- The picture loop is `TICKS = cycle * grand * 30` ticks. **Every period must divide it**: blink cycles, sway tables, walk paths, cloud trips, particle periods (particle clocks run at 15 Hz, `k >> 1`, so their periods divide `TICKS / 2`). `check.py` catches a seam but not which period caused it, so pick periods from the divisors as you write them.
- Step the motion: compute slow clocks (`(k / 3) | 0` is 10 fps, `(k / 15) | 0` is 2 fps). Smooth 30 fps motion looks digital; 2 to 12 fps looks hand-animated.
- Things that drift (clouds, mist, swells) make whole trips per loop: position = `floor(k2 * span * trips / (TICKS / 2)) mod span`, with the span wider than the frame so a sprite is fully off screen when it wraps.
- `cycle` must match the phases' natural length (8 bars at each tempo plus one transition bar each). `check.py` prints the right number if it is off.

## What makes it look hand-made (summary of references/craft.md)

- **Limited palette, no blending.** No gradients except dithered bands, no blur, glow, anti-aliasing or alpha. Light is shown with palette swaps, dithered pools and rim pixels.
- **Everything placed by hand.** Positions are hand-picked; avoid even scatter and avoid symmetry. A few deliberate imperfections help: a patched roof tile, a crooked post, a worn path.
- **Clear silhouettes.** Give everything an outline and a lit side, with three-tone shading per form. Canopies are clumps with lit tops and dark undersides, not balls with noise.
- **Each phase has signature elements**, not just a recolour. Lantern Isle's are rain rings, fireflies, birds crossing the moon, and an aurora.
- **Weather and particles stay sparse and layered by depth.** Far ones are small and dim, near ones bigger and brighter.
- **Gradients need wide dithers.** Use 10 to 16 dithered rows between bands, or the sky reads as stripes.
- **Look at it.** The common failures are a canopy that reads as a ball, a roof that reads as a brick wall, smoke drawn as dotted squares, a striped sky, a busy sea, and a subject too small in the frame. Shots at zoom reveal all of them.

## Files

- `engine/`: core (timeline, palettes, sprites, blit), render (phases, dissolve, particle helpers), audio (soundtrack), main (page), shell.html. Do not edit for a scene.
- `tools/`: build, shot, check, gen_sprites + artlib, render_audio, render_video.
- `templates/starter/`: the smallest complete scene (2 phases, 240x135).
- `examples/lantern-isle/`: a full scene (4 seasons, 480x270, Python-authored art).
- `references/`: scene-contract.md (API), craft.md (art direction), music.md (soundtrack).
