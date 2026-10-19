# Styles

A style is a set of decisions: where the light lives, how ramps bend, which dither is allowed,
how outlines work, what the numbers of a finished frame look like. Each preset in
`tools/styles.py` writes down one look measured from a reference game, so a scene can pick a
style instead of re-deciding all of it. The presets describe techniques and numbers only. The
art you make with them is your own.

This guide holds the concepts and how to choose. Each style's own detail (its rules, light regime,
ramps, outline, value budget, craft limits, techniques, figure sizes and gate command) is printed
by one command:

```
pixelate style --list                        every preset, one line each
pixelate style neon-noir                     one preset's card
python3 tools/styles.py describe neon-noir   the raw preset data
pixelate check out@5x.png --style neon-noir --scale 5      the gate on a delivered frame
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

## Routing a request

`tools/route.py` turns a plain request into a style. It scores every preset on five kinds of
signal (subject, mood and key, time and weather, what it is for, a named reference game or repo
example), adjusts for dark or bright words and a stated projection, and returns the top three
with reasons. It also names the mode, so a photo goes to the rebuild guide and "NES" to the era
guide first. With `--brief` it writes the pre-filled brief; with `--lint` it critiques a finished
one. The full loop is in [references/brief.md](../references/brief.md).

| Request sounds like | Style | Light | Projection | Closest example |
|---|---|---|---|---|
| a calm diorama, island, cottage, seasons, lofi stream | `lofi` | none | side | `library/lantern-isle` |
| a bright pastel platformer, wind, a climber, a summit | `pastel-cell` | native | side | `library/rose-squall/art/rose_squall.py` |
| ruins, a lone wanderer, glowing sigils, a dusky world | `native-glow` | native | 3/4 | |
| a JRPG overworld, a town, sunlit water, rich HD-2D-like | `hd-overworld` | native | 3/4 | |
| an arcade shooter, soldiers, tanks, explosions, chunky action | `arcade` | none | side | |
| a tactics board, mechs, a grid, a battle map | `tactics` | none | 2:1 iso | `library/projections` |
| a city block, a busy street, a cross-section, many tiny people | `sticker-iso` | none | 2:1 iso | `library/san-francisco` |
| a big monument, a painted vista, an airship, clouds | `illustrated` | none | side | |
| a neon city at night, rain, a samurai, noir, a club | `neon-noir` | native | side | |
| a farm, a cosy village, lamps at night, a warm interior | `cosy-lightmap` | screen | 3/4 | |
| a backlit forest, a mountain at night, fog, a pillar of light, cinematic | `contre-jour` | screen | side | |
| a photo or an aerial | mode rebuild, then a style for the finish | | keep the photo's camera | |
| NES, Game Boy, 8-bit, SNES | mode era, then a style | | | |
| a sprite sheet, a tileset, icons | mode assets | | | |

When nothing scores, the router picks `lofi`, the toolkit's own look. The router matches
keywords, so treat it as a proposal: weigh it against what the user most likely means, answer
the questions below, and say which style you chose and why. For the tools a subject needs, run
`pixelate tools TOPIC --style S` ([toolkit.md](toolkit.md) says how to query the kit).

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

There are eleven: `contre-jour`, `pastel-cell`, `native-glow`, `hd-overworld`, `arcade`, `tactics`,
`sticker-iso`, `illustrated`, `neon-noir`, `cosy-lightmap` and `lofi`. `pixelate style NAME` prints
one preset's card: reference, res and blend, ramps, dither, outline, scale and size, budget and
craft limits.

Outline modes:
- `none`: no outline.
- `own`: the material's darkest step.
- `part`: each part outlined in its own dark.
- `selective`: the material's darkest step on the lit side, near-black on the shadow side.
- `black`: a full `#000` silhouette.
- `actors`: only actors and interactive objects are outlined.

Most scenery in most styles is not outlined: rims and seams separate the forms.

Every preset also lists (all on its card):
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

The references keep their numbers tight, and the numbers are easy to break. `stats.budget(frame_1x, style)` returns the rules a frame breaks. Each style's rules, in numbers and in words, are on its card (`pixelate style NAME`, "Value budget"), next to its craft limits (`craftcheck.CRAFT`).

Each reference passes its own budget when measured on its native frame.

Masks are 1x bool arrays or slot names (`'hero'` is the ramp hero0..heroN, `'far_'` every slot with that prefix). With masks, `stats.py` can check more:
- per-role rules: `env:L[0.3,0.78]`
- ratios between masks: `actor/world:detail`
- gaps between layers: `gap:far,near`
- readability: `stats.readability(img, actor_mask)`

`stats.frame_stats` reports everything at once.

## Checks before delivery

The gate runs all of these in one command, on the delivered frame:

```
pixelate check FRAME.png --style S --scale N [--pal palette.json] [--pre prelight.png]
               [--actor actor_mask.png] [--used op,op] [--intent mask.png]
```

1. **Budget.** Every rule of the style's numeric budget (on its card).
2. **Native cells** (`none` and `native` styles). Every N x N cell is flat (`stats.native_cells`).
3. **Post ops.** Each op in `--used` is one the style allows. Screen styles take their light only from the `post.py` calls the scene lists.
4. **The pixel layer.** `--pre` is the frame before any light (the frame itself for pixel-only styles); with `--pal` it must have no off-palette pixels (`stats.palette_subset`).
5. **Readability.** The actor (`--actor`) stands apart from the 8 px ring around it (`stats.readability`).
6. **Craft.** Orphans, jaggies, stripes, doubled outlines, pillow shading and clusters stay inside the style's `craftcheck.CRAFT` limits; `--intent` marks sparkles and flecks placed on purpose.

Every line prints PASS, FAIL or SKIP with the value and the limit. Redraw until every line passes, then show one still for go/no-go. Engine scenes also run `pixelate check SCENE`. `styles.check(frame_1x, style, big=delivered)` is the same budget check from Python.

## Export

Frames from a screen-resolution light layer (`Post.image()`) are already at delivery size. Pass `'prescaled': True` (and `'scale'`) in the scene dict, or `assets.export_scene(..., prescaled=True)`. Then:
- nothing is resized again;
- the MP4 keeps a 3x frame at 3x;
- an APNG is written, because a 255-colour GIF bands soft light.

Pixel-only and native styles export as before.

## Eras

`tools/era.py` holds console limits (`guides/eras.md`). `arcade` pairs with the `neogeo` era, checked
one layer at a time; its card has the details.
