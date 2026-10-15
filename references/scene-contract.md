# Scene contract and engine API

A scene is a folder. The build concatenates, in order:

```
config.js  ->  engine/core.js  ->  engine/render.js  ->  files in scene.json  ->  music.js  ->  engine/audio.js  ->  engine/main.js
```

Everything is plain global scope in one strict-mode script, so later files can use
anything defined earlier. Node runs the same code without audio and main to export
frames, so drawing code must not touch `window` or `document`.

## scene.json

```json
{ "title": "Hilltop Cabin",
  "description": "one sentence for the page's meta description",
  "alt": "what the canvas shows, for screen readers",
  "files": ["palettes.js", "sprites.js", "scene.js"],
  "art": ["art_terrain", "art_house"] }
```

`files` lists the drawing files in load order. `art` (optional) lists the Python modules
`pixelate sprites <scene>` turns into `sprites.js`.

## config.js

```js
const SCENE = {
  name: 'Hilltop Cabin',
  width: 240, height: 135,        // native canvas
  phases: [{ name: 'dusk', bpm: 76 }, { name: 'rain', bpm: 68 }],   // 1..8 phases
  bars: 8,                        // bars per phase (melody phrases are 2 bars)
  cycle: 60,                      // seconds for one pass through all phases (whole seconds)
  grand: 2,                       // picture loop = cycle * grand seconds
  paletteFallback: 'dusk',        // optional: palette that fills slots another one leaves out
  slots: ['S0', 'S1', ...],       // every slot name used anywhere (max 255)
  dynamicSlots: ['WL0', ...]      // slots coloured per frame in sceneDynamic (no palette entry)
};
```

A phase may set `palette: 'key'` when its palette is named differently from the phase.

### Timing

- **One cycle:** each phase lasts `bars * 240 / bpm` seconds, plus a one-bar transition into the next phase at the mean tempo. Tempos are scaled by one common factor so the total is exactly `cycle` seconds. Keep that factor near 1: `pixelate check` prints the right `cycle` (or tempos) if it isn't.
- **Picture loop:** `TICKS = cycle * grand * 30` frames. Slow drifts (clouds, swells) may use the full picture loop.
- **Soundtrack:** the phases' music repeats every `cycle`. Its random choices are seeded by `cycle index mod grand`, so the audio also repeats exactly every picture loop.

## Hooks (global functions you define)

| hook | when | draws into |
|---|---|---|
| `sceneInit()` | once, after palettes are built | precompute shapes, tables |
| `sceneBack(si, k)` **required** | every frame, per phase | `BG` |
| `sceneObjects(si, k)` | after back | `OB` (0 = empty; covers BG) |
| `sceneAfterObjects(si, k)` | after objects | reads `OB`, writes `BG` (reflections, light on water) |
| `sceneFront(si, k)` | after compositing `IX = OB \|\| BG` | `IX` (low mist, foreground) |
| `sceneDynamic(si, k, D, P)` | after drawing | `D` live palette (Uint32 per slot), `P` base palette: `D[SL.X] = P[SL.Y]` |
| `sceneParticles(si, k, dens, out, D)` | after the phase dissolve | `out` (final RGBA Uint32), use `put`/`putSpr`; `dens` 1 → 0 across a transition |

`si` is the phase index and `k` the tick (0 to TICKS - 1). During a transition the
engine renders both phases fully and dissolves between them through an ordered dither
with a diagonal lean. Particles of both phases are drawn, weighted by `dens`.

## Engine API

**Constants**
- Canvas and loop: `W`, `H`, `NPX`, `HZ` (30), `TICKS`, `CYCLE`, `GRAND`.
- Phases: `NPH` (phase count) and `TIMELINE` (`{ bpm[], seg[] }`; each segment has `kind`, `s`, `start`, `dur`).

**Slots and sprites**
- `SL.NAME` is the index of a palette slot; `SLOT_LIST` lists them all.
- `SPR.name` is a sprite: `{ w, h, f: [frames], ax, ay }`.

**Drawing into an index buffer (`BG`, `OB`, `IX`)**
- `blit(buf, SPR.x, x, y, frame, flip, alpha, remap)`: `alpha < 1` dissolves the sprite through the 8x8 Bayer matrix; `remap` is a slot → slot table.
- `px(buf, x, y, slot)` sets one pixel.
- `hline(buf, x0, x1, y, slot)` draws a horizontal run.
- `bands(buf, stops, yEnd)` draws dithered gradient bands. Stops are `[[y, 'SLOT', transitionRows], ...]`, and each transition sits just above its stop.
- `setOrigin(x, y)` offsets every draw call. Use it when the art is authored in its own space; the engine resets it to 0,0 between hooks.

**Drawing particles into the final frame**
- `put(out, D, x, y, slot)` and `putSpr(out, D, SPR.x, x, y, frame, flip)`.

**Clocks and randomness**
- `pclock(k2, j, period, seed)` returns `[age, generation]`: a looping particle clock where `k2 = k >> 1` and the period divides `TICKS / 2`. Use `generation` to pick a new random position each time a particle restarts.
- `hash(n)`, `hash2(a, b)`, `hash3(a, b, c)` return a deterministic value in [0, 1). `mod(a, n)` is a modulo that is never negative.
- `flick(f10, seed, hold, pDim, pDeep)` returns 0, 1 or 2 (full, dim, deep) and holds it for `hold` steps. Use it for fire, candle and window flicker through `sceneDynamic`.
- `BAYER4` (4x4, values 0-15) and `BAYER8` (8x8, values 0-63) are ordered-dither thresholds.

**Phase timing**
- `seasonAt(k)` returns `{ si, f, nx }`: the current phase, the blend fraction toward the next phase, and the next phase.
- `seasonClock(k, s)` returns `{ t, dur }`: seconds since phase `s` began. Use it for timed events, such as birds crossing the moon at a set moment.

## Sprites

```js
def('cabin', { k: 'K0', R: 'R2', r: 'R1', y: 'WL2' }, `
..k..
.kRk.
kRrrk
`, { ax: 2, ay: 2 });            // anchor: blit(x, y) puts this pixel at x, y
```

- `.` or a space is transparent.
- Separate animation frames with a line of `---`; every frame shares the same size.
- Unknown keys are reported by `pixelate check`.
- Python art modules return `('sprite', name, [Grid, ...], ax, ay)`; see `tools/artlib.py` and `examples/lantern-isle/art/`.

## Debug page

`pixelate build <scene>` writes `dist/dev.html`:
- `?t=SECONDS&freeze=1` shows a fixed moment.
- `window.__dbg.set(t)` draws the frame at time `t`.
- `window.__dbg.grab()` returns a PNG data URL of the canvas.
- `window.LOFI.renderOffline(V0, seconds, 48000, solo, loop)` renders audio offline. `solo` is a list of stems, for example `['kick']`, `['keys', 'lead']` or `['amb']`.

`--release` strips all of these.
