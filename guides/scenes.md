# Scenes and animated loops

A scene cycles through moods ("phases": seasons, times of day, weather) with music whose
chords, tempo and instruments change with each phase and blend between them like a DJ set.
Picture and music loop exactly, so one short file can play for hours.

Outputs:
- a **live HTML page**, which plays live generative music after a tap and runs forever
- a **seamless MP4** (1080p or 4K)
- a **GIF**
- **still PNGs** (wallpapers, thumbnails)

`library/lantern-isle` is the quality bar: an island cottage through four seasons. Read its files when you need to see how something is done well.

**Starters and worked examples.** Making a new scene takes the style loop in `SKILL.md`; the author path in `references/authoring.md` is for a new library piece, and the workflow below is its long form. Begin from a neutral starter, then replace its placeholders: `starter-scene-still` for a still (`pixelate remix starter-scene-still work/NAME --request "..."`) or `starter-scene-loop` for a loop with music (`pixelate new scene NAME`, below). Starters pass the technical gate empty and are unreviewed. The other pieces are `study` status, unreviewed references; `pixelate library test ID --quick` reports each one's gate result. To read, by what you need:
- a looping engine scene with music: `lantern-isle`, `starter-scene-loop`;
- stills under another style budget: `quarry-wakes` (arcade, with a sting), `tide-procession` (contre-jour silhouette, music), `tidewater-signal` (lofi, music);
- stills scored with music: `endless-ascent`, `canyon-cycle`.

## Workflow

1. **Settle the brief.** On the style loop, the brief from `pixelate route --brief` with a clean lint is enough, and review waits for the still. On the author path, read the intent, route as a hint, then write the full brief (the eleven sections in `references/brief.md`, at the density of `library/lantern-isle/brief.md`), block it in and seek an A within the review budget (`pixelate critique --brief brief.md`, `references/delivery.md#art-director`), and show the full brief for approval only at A. Build only once the user confirms it. Pick a style from `guides/styles.md`. A single still gets a short brief, which skips brief-stage review.
   - **The subject.**
   - **Phases:** 1 to 6, each with a mood, a palette idea, signature elements and its music.
   - **The canvas:**
     - 16:9: `240x135` (8x = 1080p, 16x = 4K), `320x180` (6x/12x) or `480x270` (4x/8x)
     - square: `270x270`, `360x360`
     - vertical: `270x480`
     - Smaller canvases mean chunkier pixels and less to draw.
   - **The outputs.**

2. **Start:** `pixelate new scene my-scene` gives a 2-phase, 240x135 starter that passes every check (for a still, begin from `starter-scene-still` instead). Read `references/scene-contract.md` once: files, `SCENE` fields, hooks, engine API.

3. **Palettes** (`palettes.js`): one per phase, with the same slot names. See `guides/palettes.md` and `references/drawing.md#palette`.

4. **Sprites** (`sprites.js`, `def(name, key, rows)`): draw every object from scratch and hand-place every pixel.
   - For organic or repeated shapes (terrain, canopies, snow overlays), write Python in `my-scene/art/*.py` with the primitives in `tools/` (`pixelate tools TOPIC`, `pixelate tools MODULE`) and run `pixelate sprites my-scene`.
   - Finished objects in `references/assets/` (boats, cats, props, particle sprites) are examples to read, never call. Anything the kit lacks is a slot map you write.

5. **Compose one still** (`scene.js` hooks), with nothing moving yet:
   - **Background:** `bands()` gradients.
   - **Objects:** `blit` into `OB`.
   - **Reflections and light on water:** `sceneAfterObjects`.

6. **Gate it, then show it.**
   ```
   pixelate video my-scene --png 0 still.png --scale 4
   pixelate check still.png --style lofi --scale 4 [--pal P] [--actor MASK]
   pixelate check my-scene
   ```
   Redraw until every line passes, then get the still's critique (`pixelate critique still.png --brief brief.md`, `references/delivery.md#art-director`) and show the user that one still for go/no-go. On the style loop that is one round: apply its fixes once and show the still with its grade. On the author path, seek an A within the review budget; if review stops below A, report the grade and unresolved ranked fixes and ask whether to continue or change the brief; do not deliver that still as finished. For a still-only job, the A still is the delivery.

7. **Confirm the animation plan.** Show the loop length (`cycle`, `grand`, ticks), what moves, and each rate and frame count, every period dividing the loop (the brief's motion table, updated). Animate only after the user says OK.

8. **Animate**, following the loop rules below:
   - **Flicker:** `sceneDynamic`.
   - **Weather:** `sceneParticles`.
   - **Moving objects:** frames picked with slow clocks in `sceneObjects`.

9. **Music** (`music.js`): see `guides/music.md`. Leave out `music.js` for a silent loop.

10. **Look and check, every iteration:**
    ```
    pixelate shot my-scene 5 30 55 80 --grid --zoom 3     # then view the PNGs
    pixelate check my-scene --page
    ```
    - View every phase and a frame mid-transition, at zoom.
    - Fix what looks off before adding more.
    - `check` must say ALL OK, and frames from each phase pass the frame gate like the still did.

11. **Deliver:**
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

## Summary of the craft (details in references/drawing.md)

- **Strict palettes, no blending.** Light is palette swaps, dithered pools and rim pixels.
- **Hand-placed and asymmetric**, with deliberate imperfections such as a patched tile or a crooked post.
- **Outline and lit side** on every form. Canopies are clumps, not balls.
- **Signature elements for each phase**, not just a recolour.
- **Sparse, layered weather.** Wide dithers (10-16 rows) in gradients.
- **The subject fills about half the frame width.** Calm areas let the eye rest.

## Using the Python kit in a lofi scene

The lofi style plays in the JS engine, but every drawing tool in the kit is Python. The bridge
is the scene's art modules (`my-scene/art/*.py`): `pixelate sprites my-scene` runs each
module's `export()` and writes `sprites.js`. Two rules:

- **Kit drawings become engine sprites.** Kit tools draw into a `canvas.Canvas` (its slot array
  is `c.g`, `None` = transparent) or a plain slot grid. Copy it into an `artlib.Grid` with
  `sprite.paste(grid, c.g, x0, y0)` and return `('sprite', name, [Grid, ...], ax, ay)`; the
  generator writes it with `artlib.to_js`. Use the scene's slot names (the ones in
  `palettes.js`): a tool that writes its own ramps (`fx.PALETTE`, such as `fire0..fire6`) needs
  those slots added to every phase palette or renamed through its slot arguments, or
  `pixelate check` reports unknown keys. Lofi allows no post ops, so nothing from `post.Post`
  or alpha glazes crosses over.
- **Python motion does not run in the page; bake it.** `anim.*`, `fx.*` with `t`, `sprite.chain`,
  `canvas.drift` and the rest are pure functions of `t`, so call them once per drawing and ship
  the drawings as frames (pick one in `scene.js` with a slow clock: `((k / 6) | 0) % n`), or ship
  positions as a table through `('const', NAME, 'js literal')`. Every baked period must divide
  `TICKS` (frames x hold), or `TICKS / 2` on the 15 Hz particle clock; `anim.check_periods`
  says which do not.

`references/assets/particles.py` shows how lofi weather is baked this way (read it, never call it):
a Field holds hand-keyed drawings and per-particle tables whose periods divide `TICKS / 2`, so the
particles loop exactly; `export(NAME)` returns the drawings, the table and the engine helper
`drawBaked`, and `grid(k2, W, H)` previews a step in Python. Write your own field for the scene's
weather, at its size and in its palette.

```python
# my-scene/art/art_kit.py
import anim, canvas, sprite
from art_weather import drizzle                     # your own Field, written like references/assets/particles.py
from artlib import Grid

TICKS = 96 * 2 * 30                                  # cycle * grand * 30, as in config.js

def buoy(t):
    """one drawing of a bell buoy, bobbing 1 px"""
    c = canvas.Canvas(9, 14)
    dy = anim.stepped_sin(t, 8, amp=1, hold=1)
    c.rect(2, 6 + dy, 6, 12 + dy, 'R2')
    c.vline(4, 1 + dy, 5 + dy, 'K1')
    c.outline(c.mask_of('R'), 'K0')
    return c

def to_grid(c):
    g = Grid(c.W, c.H)
    sprite.paste(g, c.g, 0, 0)                       # Canvas slots -> artlib.Grid
    return g

def export():
    frames = [to_grid(buoy(t)) for t in range(8)]    # the bob, baked into 8 drawings
    anim.check_periods(TICKS, {'buoy': 8 * 6})       # 8 drawings held 6 ticks each
    rain = particles.drizzle(320, 180, T2=TICKS // 2)
    return [('sprite', 'buoy', frames, 4, 13)] + rain.export('DRIZZLE')
```

```js
// scene.js / fx.js
blit(OB, SPR.buoy, 210, 150, ((k / 6) | 0) % 8);                 // in sceneObjects
function sceneParticles(si, k, dens, out, D) {
  if (si === DAWN) drawBaked(DRIZZLE, k >> 1, dens, out, D);     // fades with dens in a dissolve
}
```
