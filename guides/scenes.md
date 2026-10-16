# Scenes and animated loops

A scene cycles through moods ("phases": seasons, times of day, weather) with music whose
chords, tempo and instruments change with each phase and blend between them like a DJ set.
Picture and music loop exactly, so one short file can play for hours.

Outputs:
- a **live HTML page**, which plays live generative music after a tap and runs forever
- a **seamless MP4** (1080p or 4K)
- a **GIF**
- **still PNGs** (wallpapers, thumbnails)

`examples/lantern-isle` is the quality bar: an island cottage through four seasons. Read its files when you need to see how something is done well.

## Workflow

1. **Settle the brief.** Ask only what you can't infer, then write the full brief (the eleven sections in `references/craft.md`, at the density of `examples/lantern-isle/BRIEF.md`) and show it before building. Pick a style from `guides/styles.md`.
   - **The subject.**
   - **Phases:** 1 to 6, each with a mood, a palette idea, signature elements and its music.
   - **The canvas:**
     - 16:9: `240x135` (8x = 1080p, 16x = 4K), `320x180` (6x/12x) or `480x270` (4x/8x)
     - square: `270x270`, `360x360`
     - vertical: `270x480`
     - Smaller canvases mean chunkier pixels and less to draw.
   - **The outputs.**

   For a still image, use a single phase and export a PNG with `pixelate video SCENE --png 0 out.png --scale 4`.

2. **Start:** `pixelate new scene my-scene` gives a 2-phase, 240x135 starter that passes every check. Read `references/scene-contract.md` once: files, `SCENE` fields, hooks, engine API.

3. **Palettes** (`palettes.js`): one per phase, with the same slot names. See `guides/palettes.md` and `references/craft.md`.

4. **Sprites** (`sprites.js`, `def(name, key, rows)`): hand-place every pixel.
   - For organic or repeated shapes (terrain, canopies, snow overlays), write Python in `my-scene/art/*.py` with `tools/artlib.py` and run `pixelate sprites my-scene`.

5. **Compose and animate** (`scene.js` hooks), following the loop rules below:
   - **Background:** `bands()` gradients.
   - **Objects:** `blit` into `OB`.
   - **Reflections and light on water:** `sceneAfterObjects`.
   - **Flicker:** `sceneDynamic`.
   - **Weather:** `sceneParticles`.

6. **Music** (`music.js`): see `guides/music.md`. Leave out `music.js` for a silent loop.

7. **Look and check, every iteration:**
   ```
   pixelate shot my-scene 5 30 55 80 --grid --zoom 3     # then view the PNGs
   pixelate check my-scene --page
   ```
   - View every phase and a frame mid-transition, at zoom.
   - Fix what looks off before adding more.
   - `check` must say ALL OK.

8. **Deliver:**
   ```
   pixelate build my-scene --release                       # my-scene/dist/<title>.html
   pixelate audio my-scene my-scene/loop.wav               # one seamless loop of the music
   pixelate video my-scene out-1080p.mp4 --audio my-scene/loop.wav
   pixelate video my-scene out-4k.mp4 --scale 16 --audio my-scene/loop.wav   # 240x135 -> 3840x2160
   pixelate gif my-scene out.gif --scale 3                 # short loops; slice with --frames K0:K1
   ```
   Use whole, even scales: pixels stay square and colours exact. The MP4 is one exact loop (`cycle x grand` seconds).

   Costs on 2 cores:
   - **2 minute loop:** about 1 minute of audio and 2 minutes of 1080p encoding.
   - **6 minute loop:** about 8 minutes of audio and about 20 minutes of 4K encoding.

## Loop rules (the engine relies on them)

- **Everything is a pure function of the tick `k`** (30 per second). Use `hash`/`hash2`/`hash3`, never `Math.random`, and carry no state between frames.
- **The picture loop is `TICKS = cycle * grand * 30` ticks, and every period must divide it.** That covers blink cycles, sway tables, walk paths, cloud trips and particle periods. Particle clocks run at 15 Hz (`k >> 1`), so their periods must divide `TICKS / 2`.
- **Step the motion.**
  - Use slow clocks: `(k / 3) | 0` is 10 fps and `(k / 15) | 0` is 2 fps.
  - 2-12 fps looks hand-animated; smooth 30 fps looks digital.
- **Drifting things make whole trips per loop.** Clouds, mist and swells move by `floor(k2 * span * trips / (TICKS / 2)) mod span`, with the span wider than the frame.
- **`cycle` must match the phases' natural length** (bars at each tempo plus one transition bar each). `check` prints the right number.

## Summary of the craft (details in references/craft.md)

- **Strict palettes, no blending.** Light is palette swaps, dithered pools and rim pixels.
- **Hand-placed and asymmetric**, with deliberate imperfections such as a patched tile or a crooked post.
- **Outline and lit side** on every form. Canopies are clumps, not balls.
- **Signature elements for each phase**, not just a recolour.
- **Sparse, layered weather.** Wide dithers (10-16 rows) in gradients.
- **The subject fills about half the frame width.** Calm areas let the eye rest.
