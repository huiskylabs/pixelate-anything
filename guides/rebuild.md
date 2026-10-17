# Rebuild: turn a photo or a place into real pixel art

This is the default for any photo of a place, a building or a scene. Converting a photo
(`guides/pixelate.md`) gives a filtered photo. Rebuilding gives what a pixel artist would make:
- the composition and camera of the reference,
- every shape redrawn on clean pixel lines,
- a palette chosen for the mood,
- and life added: light, weather, traffic, people, a day turning to night.

`examples/san-francisco` is the quality bar. An aerial photo of the Financial District is rebuilt:
- in its own camera (`art/rebuild.py`),
- and again as an isometric diorama (`art/city.py`).

## 1. Read the shape language first

Before placing anything, write down what the reference is made of. A wrong vocabulary can't be fixed later by detail.

- **Rectilinear or curved?**
  - SF's Financial District is boxes.
  - A Cycladic village is rounded cubes, vaults, domes, arches, and walls that flow into the hillside.
  - Old towns lean and taper.
  - Nature is blobs and layers.
- **The 5-8 signature forms.**
  - For Santorini: a rounded whitewashed cube; a flat-roof terrace with a rounded parapet; a white or blue barrel vault; a small dome; an arched door and window cut deep into the wall; a curving terrace wall of volcanic stone; a winding stair; a kidney pool.
- **Density and regularity.** A grid with gaps, or packed and irregular, stepping, merging and following the contours?
- **Accents.** The few colours and details that say *this place*: blue doors, bougainvillea, a beacon, a flag.

Then **build the kit**:
1. Make one function per signature form, with seeded variation.
2. Render the forms side by side on a plain ground.
3. Compare them with crops of the photo.

Only when the parts read right, compose. Use `tools/sdf.py` for anything curved:
- `RBox` with corner radii,
- `Cyl` (also lying down, for vaults), `Sphere` (domes), `Cone`,
- `Smooth` unions, for plaster flowing between houses,
- `Sub` with `Arch`, for openings cut in as real recesses,
- `Terrain`, for curved terraces and slopes.

Use `Iso.box` only where the place really is boxes. `examples/santorini/art/santorini.py` is the worked example.

## 2. Pick the camera

The five views below are useful presets, not limits. Choose one when it fits the reference or the art's use. `tools/iso.py` renders these orthographic views from one 3D description; see `examples/projections`. It does not render vanishing-point perspective.

| camera | lines | pick it for |
|---|---|---|
| `side` | horizontal and vertical | a street front or skyline seen level; platformer backgrounds |
| `topdown` (3/4) | horizontal and vertical | a high, front-on view; RPG and town maps |
| `iso` (2:1 dimetric) | 2-pixel steps | a view onto a corner of things; strategy games, dioramas, tiles |
| `oblique` | true front, 2:1 depth | building fronts that must read exactly, with some depth |
| `military` (45°) | 1:1 steps | a steep plan view, graphic maps |

For a reference rebuild, inspect the image yourself: `pixelate route` reads request words, not image geometry. Record the crop, horizon (including when it falls outside the frame), visible vanishing point(s), near/far scale and the landmark's position. If the reference uses one- or two-point perspective, or the request explicitly asks for it, keep that camera instead of substituting iso. A stylized projection is a choice to confirm, not an automatic correction.

Construct perspective in screen space on the native-pixel canvas. Mark the horizon and vanishing point(s), block in the nearest and farthest silhouettes, then place receding edges and repeated units along those guides. For one point, depth edges meet one point; for two points, each horizontal face direction meets its own point. Snap corners to integer pixels and hand-step long diagonals with consistent clusters. Check shrinking windows, paving and figures at 1x before detailing; limit far detail and use the palette's haze. This is authored pixel drawing, not a full 3D perspective renderer. Steep or distant converging edges may need selective simplification to avoid noisy stair-steps, but the camera and framing still need to read.

## 3. Trace the layout

Read the reference and list what makes it *that* place:
- the landmark and where it sits in the frame,
- the big masses in front and behind,
- the street pattern,
- the parks and water,
- the one or two signature details (a spire, a crown, a dome, a flag).

Then place them:
- **Front-on orthographic views:** place the photo's large forms on screen. `bld(x0, x1, roof_top, roof_front, height)` in `examples/san-francisco/art/rebuild.py` turns "the roof sits here on screen and the front is this tall" into a 3D box. Work landmark first, then the foreground, then fill the rest.
- **Perspective views:** use the brief's horizon, vanishing points and native-pixel boxes to draw the landmark and the main receding planes first. Place near and far repeats by hand along the guides; do not feed them to `Iso.box`.
- **Isometric:** lay out a street grid in world units. 16 units is one 32x16 tile.
- **Fill:** use procedural blocks (row houses, trees) for the rest, seeded by `hash2` so they stay put, and keep them clear of the landmarks (`RESERVED`).
- **Organic places:** follow the contours instead of a grid. Vary widths and depths, leave gaps for stairs and alleys, and let neighbours merge (`Smooth`). Let houses sink into the terrace above, so a roof becomes the next terrace.
- **Fill the frame.** Show a crop of a world that continues past every edge, not a block floating in the sky. A full-bleed square reads as a place, a floating slab as a model. Generate past the frame and let the canvas cut it.

## 4. Shapes (tools/iso.py, tools/sdf.py)

For the five orthographic cameras, use the shapes recipe below. For one- or two-point perspective, draw converging edges on the native-pixel canvas as in section 2. `Iso` does not render vanishing points.

```python
from iso import Iso, frustum, windows, clone
s = Iso(W, H, origin=(ox, oy), camera='topdown', depth=0.62, slots=palette.keys())
s.box(x, y, z, w, d, h, 'cream', top='roof3', left=windows('cream', 'glass', lit='litA'))
s.gable(x, y, z, w, d, h, 'brick')         # pitched roof
s.pyramid(...); frustum(s, ...)              # stepped or smoothly tapering towers
s.cylinder(cx, cy, z, r, h, 'glassy')        # round towers
s.sprite(tree_grid, x, y, z)                 # hand-drawn sprites stand in the scene
s.solid(Sub(Smooth(0.7, RBox(x, y, z, x + 10, y + 8, z + 9, r=1.4), vault),
           Arch(x + 2, y + 7.2, z, 2, 2, 5, mat='door')))   # curved solids, any camera
s.cast_shadows(sun=(-0.7, 0.4, 0.6), step=-2) # one or two ramp steps darker where blocked
grid = s.render()                            # outline, selective outline, lit rims
```

How faces are coloured:
- **Function faces:** a face can be a function `f(u, v, t)` of its own coordinates. Use one for windows, ribbon glazing, mullions, tiles, water and anything animated.
- **Ramps:** materials are ramp names (`cream0..cream4`). Faces take their lit or shaded step automatically.
- **Finishing passes:** the finishing passes in `render()` are what make it read as drawn.

## 5. Palette: add what the photo lacks

Photos are often grey, flat and hazy, and a rebuild should not copy that:
- **Ramps:** give every material a hue-shifted ramp (`pixelate palette ramps`).
- **Colour:** add colour the photo only hints at, such as pastel houses, green trees, red brick, and glass that reflects the sky.
- **Haze:** fade the far distance into haze, one dithered step lighter.
- **Light sources:** keep them as slots: window groups (`litA..litD`), lamps, headlights, a beacon. By day they match the wall or glass. At night they glow.
- **More moods:** derive dusk and night by relighting the day palette in OKLab (`examples/san-francisco/art/palettes.py`). Then set the light sources by hand. One render, three palettes.

## 6. Bring it to life

Draw the static world once, then per frame:
1. `clone` it,
2. add the moving things (cars, boats, people, birds),
3. render,
4. swap palettes along a timeline, dissolving with a Bayer dither.

Rules for the motion:
- **Exact loops:** keep every motion a whole number of trips per loop, so it loops exactly.
- **Speed:** move things 1-2 px per frame at 12 fps.
- **Night lights:** flicker by toggling a light group's colour per frame, never by redrawing.

Export with an art module that returns `{'kind': 'scene', 'images': frames}`. Then `pixelate assets PACK` writes:
- the first frame as a PNG,
- a GIF,
- an MP4.

## 7. Look and compare

Put the render next to the reference at the same size and check:
- Are the forms the reference's forms (curved where it is curved, boxy where it is boxy)?
- Is the density the same, and is the regularity the same?
- Is the landmark instantly recognisable, at the same place in the frame?
- Do the big masses sit where they sit in the photo? Do the horizon, convergence, near/far scale and crop still match its camera?
- Does the eye go to the landmark first? If not, quiet the surroundings: lower contrast, fewer windows, more haze.
- Are there any noisy areas? Fix them with fewer, bigger shapes, placed texture and flat roofs.
