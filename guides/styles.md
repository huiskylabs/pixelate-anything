# Styles

A style is a set of decisions: where the light lives, how ramps bend, which dither is allowed,
how outlines work, what the numbers of a finished frame look like. Each preset in
`tools/styles.py` writes down one look measured from a reference game, so a scene can pick a
style instead of re-deciding all of it. The presets describe techniques and numbers only. The
art you make with them is your own.

```
python3 tools/styles.py                      list the presets
python3 tools/styles.py neon-noir            one preset in full
python3 tools/styles.py neon-noir out@5x.png --scale 5     check a delivered frame
python3 tools/stats.py frame.png --style neon-noir         the numbers behind the check
python3 tools/palette.py styles -o ramps     every ramp style as a swatch sheet
```

## The two-layer rule

**The pixel layer is always strict.** Every pixel is a palette slot on the integer grid, with no
anti-aliasing and only nearest-neighbour integer scaling. All ten references keep to this. Metal
Slug's blur and Katana ZERO's 4.5x grid are capture artefacts, not part of the style.

**The light layer is optional. When a style has one, code generates it** from the scene's own
masks, positions and depth planes (`tools/post.py`). It must declare two things:

- **res**:
  - `none`: no light layer. Light is a palette step (`tools/light.py`), or don't light at all.
  - `native`: the light is computed once per art pixel and scaled up last, so every cell stays one flat colour.
  - `screen`: the light is smooth inside each art pixel.
- **blend**: `screen`, `add`, `multiply` or `lerp`.

Each style uses exactly one regime. Mixing regimes in one frame makes it read as a filter.
Nothing is hand-painted in an editor and nothing is AI-generated. Every light, particle and UI
piece is a pure function of (inputs, t, T, seed), so it can be recomputed when the palette, the
light position or the loop length changes.

Vignette, grain, scanlines and chromatic aberration are off unless a preset lists them. None of
the ten references uses grain, scanlines or aberration. Darkness is drawn into the scene (voids,
doorways, a drawn frame), not filtered onto it.

## Picking a style

1. **Where does the softness come from?**
   - Nowhere (flat, graphic, retro): `arcade`, `tactics`, `sticker-iso`, `illustrated`, `lofi`.
   - Soft, but on the pixel grid: `pastel-cell`, `native-glow`, `hd-overworld`, `neon-noir`.
   - Soft at screen resolution (cinematic, cosy): `contre-jour`, `cosy-lightmap`.
2. **What is the key?**
   - High-key: `pastel-cell` (median L .78).
   - Mid: `illustrated` (environment L .30-.78).
   - Low: `hd-overworld`, `native-glow`.
   - Mostly dark: `contre-jour` (65% below L .25), `tactics` (84% below .30), `neon-noir` (26% exact black), `cosy-lightmap` (52% below L .1).
3. **Where is the colour?**
   - One hue window: `pastel-cell`.
   - Rationed to 1-2% of the pixels: `tactics`, `neon-noir`, `contre-jour`.
   - Warm actors on a cold world: `arcade`.
   - Gamut-edge paint: `sticker-iso`.
4. **How big is a character?**
   - Tiny in a big set (8-16% of the frame height): `contre-jour`, `native-glow`, `neon-noir`, `cosy-lightmap`.
   - The scene is a dense crowd: `sticker-iso`.
   - A monument fills the frame: `illustrated`.

## The presets

Columns:
- **res**: where the light lives (see the two-layer rule).
- **ramp**: the `palette.ramp(style=...)` to build materials with.
- **outline**: the outline mode (modes are listed after the table).

| preset | reference | res, blend | ramp | dither | outline | scale, size |
|---|---|---|---|---|---|---|
| `contre-jour` | 01 Sword & Sworcery | screen, screen between depth planes | `ramp_between` (navy to rose through grey), `haze_levels` | none | none, 1 px rims | 3x 640x360 |
| `pastel-cell` | 02 Celeste | native, screen (bloom from cloud masks only) | `window` + `grade(hue_window, floor_L)` | none | actors only, dark violet | 6x 320x180 |
| `native-glow` | 03 Hyper Light Drifter | native, add | `families` + `drift` | none | none | 4x 480x270 |
| `hd-overworld` | 04 Sea of Stars | native, lerp (clouds at an altitude) | `rise` | checker inside clouds only | per class, tinted near-blacks | 3x 640x360 |
| `arcade` | 05 Metal Slug 3 | none (palette steps) | `arcade` for actors, flat cold `lofi` for the world | checker on HUD gauges only | own darkest step | 4x 304x224 |
| `tactics` | 06 Into the Breach | none | `arch` + `neutral_ramp` | none | black, white spec strokes | 2x 640x360 |
| `sticker-iso` | 07 Freitas iso | none, no shadows | `flat` + neutral ladder | none | full black silhouette | 4x 600x600 |
| `illustrated` | 08 Owlboy | none (water is a palette glaze) | `living` + `haze` | checker wear on stone | selective | 2x 640x360 |
| `neon-noir` | 09 Katana ZERO | native, multiply wall wash + add outer glow | `lit` | checker inside paintings only | none, warm lamp rim | 5x 384x216 |
| `cosy-lightmap` | 10 Stardew mine | screen, multiply lamp map | `plum` + `toy` | checker on wall crowns | per part, shared plum | 4x 480x270 |
| `lofi` | this repo's lantern-isle | none | `lofi` (the default `ramp`) | bayer4 gradients | own | 6x 320x180 |

Outline modes:
- `none`: no outline.
- `own`: the material's darkest step.
- `part`: each part outlined in its own dark.
- `selective`: the material's darkest step on the lit side, near-black on the shadow side.
- `black`: a full `#000` silhouette.
- `actors`: only actors and interactive objects are outlined.

Most scenery in most styles is not outlined: rims and seams separate the forms.

Every preset also lists:
- `allowed_post` and `banned_post`: the `post.Post` ops the style may and may not use.
- `motion`: `stepped` (hold tables, 2-12 fps) for every style except `cosy-lightmap`, whose actors move in screen pixels.
- `fps`, a rough authored colour count, figure sizes.
- `budgets`: the numbers a frame must hit.

`styles.allows('neon-noir', 'vignette')` answers whether an op is allowed. `styles.ramps(name, {'rock': '#hex'})` builds slots with the style's ramp.

## Ramps

`palette.ramp(base, steps, shift)` with no style is the toolkit's original ramp (`lofi`):
- darks go blue-violet, lights go warm and paler;
- about 0.125 L per step.

Older scenes depend on it, so it never changes. The references bend their ramps in many different ways:

| style | what it does | measured on |
|---|---|---|
| `rise` | 0.054 L a step; chroma grows toward the light; plum or teal darks | 04 rock and foliage |
| `arch` | chroma peaks mid-ramp; the lights go cool and white | 06 sky |
| `flat` | faces at L -0.12 -0.05 0 +0.04 +0.07, fixed hue, chroma at the gamut edge | 07 paint |
| `living` | chroma added at both ends: a grey with mauve darks and cream lights | 08 stone |
| `lit` | 9 close steps, red-brown darks, gold lights, one hot top step | 09 wood and stone |
| `plum` | step 0 is the shared plum dark of every brown; gold lights | 10 rock and timber |
| `window` | hues held inside 245-350; L floor 0.37 | 02 rock |
| `toy` | constant hue; long darks, short lights; plus a near-white glint | 10 creatures |
| `arcade` | the lofi turn, +40 degrees dark to light; the body lights keep their chroma and stop at L .82; the top step is the specular | 05 chitin |

These knobs work with any style:
- `dL`
- `L_range`
- `dark_hue` and `light_hue`
- `chroma_ends`
- `l_max`
- `anchor_dark`
- `base_index`
- `window`
- `hot_jump`

More tools:
- `ramp_path(stops)` splines any (L, C, h) path.
- `ramp_between(dark, light)` crosses two temperatures through grey, never through green or violet.
- `neutral_ramp(Ls)` gives near-greys with a faint cast.
- `grade(pal, stops, mode='lch', keep=..., hue_window=..., floor_L=...)` puts a whole palette into one mood. Hue moves the short way round, so complements never go grey. Keep the actor's backdrop out of the grade.
- `flash(pal)` is the 1-2 frame lightning or hit palette.
- `haze(pal, fog, amount, contrast)` gives `far_` slots for depth layers. Depth comes from the palette, never from blur.
- `drift(a, b, n)` with `drift_index` makes a frame family whose hue moves across the screen.
- `families()` writes a whole role palette.

## Budgets

The references keep their numbers tight, and the numbers are easy to break. `stats.budget(frame_1x, style)` returns the rules a frame breaks:

| style | rules (fractions of the frame) |
|---|---|
| `contre-jour` | at least 55% of pixels below L .25; at most 2% above L .6 and 0.3% above L .75; at most 2% above C .08 |
| `pastel-cell` | at least 97% of coloured pixels in hue 240-360; nothing below L .35; median L at least .6 |
| `native-glow` | at least half the pixels in L .2-.4; at most 5% at L .7 or above; black only in the void |
| `hd-overworld` | median C .025-.06; at most 10% above L .8 |
| `arcade` | at least 45% below L .25; at most 7% above L .75. With masks: the actor's median C at least .06, the world's at most .03, actor detail at least 1.8x the world's |
| `tactics` | at most 2.5% above C .08; at least 70% below L .3 |
| `sticker-iso` | 8-30% exact black; at least 15% above L .7 |
| `illustrated` | at most 1% below L .25 and 1.5% above L .85. With masks: the environment stays in L .30-.78 |
| `neon-noir` | at most 1.5% above C .10; at least 15% exact black |
| `cosy-lightmap` | 35-65% below L .1; at most 0.6% above L .8 |

Each reference passes its own budget when measured on its native frame.

Masks are 1x bool arrays or slot names (`'hero'` is the ramp hero0..heroN, `'far_'` every slot with that prefix). With masks, `stats.py` can check more:
- per-role rules: `env:L[0.3,0.78]`
- ratios between masks: `actor/world:detail`
- gaps between layers: `gap:far,near`
- readability: `stats.readability(img, actor_mask)`

`stats.frame_stats` reports everything at once.

## Checks before delivery

1. **The pixel layer.** Render the frame before any light. `stats.palette_subset(img, PAL)` must report no off-palette pixels.
2. **Native styles** (`none` and `native`). `stats.native_cells(delivered, scale)` must be 0.
3. **Screen styles.** The light must come only from the `post.py` calls the scene lists.
4. **Budget.** `styles.check(frame_1x, style, big=delivered)` runs steps 1-2 and the budget together.

## Export

Frames from a screen-resolution light layer (`Post.image()`) are already at delivery size. Pass `'prescaled': True` (and `'scale'`) in the scene dict, or `assets.export_scene(..., prescaled=True)`. Then:
- nothing is resized again;
- the MP4 keeps a 3x frame at 3x;
- an APNG is written, because a 255-colour GIF bands soft light.

Pixel-only and native styles export as before.

## Eras

`tools/era.py` holds console limits. `neogeo` checks one layer at a time:
- `--layer sprite`: every 16x16 tile uses at most 15 colours plus transparent.
- `--layer fix` (the HUD): 8x8 tiles.

Use it with `arcade`: render the actor and FX layers separately and check each one.
