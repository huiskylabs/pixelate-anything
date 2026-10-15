# Assets: sprites, characters, items, tilesets

An asset pack is a folder you export with `pixelate assets PACK`. Start one with
`pixelate new assets PACK`; `examples/meadow-kit` is a complete pack: a hero with idle and
walk, items, props, a grass/dirt autotile set with variants, animated water, and a map.

```
PACK/
  pack.json      {"name": ..., "palette": "palette.json", "scale": 6, "preview_bg": "#2a2836", "maps": [...]}
  palette.json   {slot: "#hex"}   ->  pixelate palette ramps ... -o PACK/palette, then add "ol" (outline) and "wh"
  sprites/*.px   hand-drawn sprites
  art/*.py       sprites built in code (variations, procedural tiles), via tools/artlib.py
  maps/*.txt     tilemap previews
```

`pixelate assets PACK` writes `PACK/out/`:
- **Per sprite:** `name.png` (1x strip of frames), `name.json` (frame rects, durations, tags, pivot, in the Aseprite array layout that Phaser, Godot and Unity importers read), `name@Nx.png`, and `name.gif` (animations only).
- **Whole pack:** `atlas.png` and `atlas.json` hold every frame. `contact.png` and `silhouettes.png` are the two to look at. Each map is written as `<map>.png`.

It also prints a report: unknown keys, ragged frames, colours per sprite, and lone pixels.

## The .px format

```
sprite: potion
anchor: 5 10                 # pivot: where the sprite stands (feet, base)
fps: 8                       # or: durations: 600 450   (ms per frame)
tags: idle 0-1               # animation ranges, as many as you like
key: o=ol c=boot2 g=glass2 G=glass3 w=wh R=red2 r=red1 d=red0
frame
...oooo...
...ocCo...
```

- `.` is transparent.
- Key values are palette slots (or `#rrggbb`).
- Rows must have equal length. Count them: the report flags ragged rows.
- `pixelate topx IMG PALETTE` turns any PNG (for example a `pixelate image` result) into a `.px` you can edit by hand.

## Sizes and readability

- **Grid:** pick it first. 16x16 is the classic tile and character size, 8x8 suits items and icons, and 24-32 px characters leave room for faces.
- **Draw at 1x, judge at 1x and at 6x.** A sprite that doesn't read at 1x won't be saved by detail.
- **Silhouette test:** `silhouettes.png` must show what each thing is from its shape alone.
- **Outlines:**
  - Use the darkest tone of the palette (`ol`) and give each sprite one light direction (upper left).
  - Selective outlining, where the outline is lighter where light hits, is a polish step for 24 px and up.
- **Shading:** three tones per material is plenty at 16 px. Put the highlight on the lit edge, not in the centre ("pillow shading" reads as amateur).
- **Clean lines:**
  - Diagonals step evenly (1:1, 2:1, 1:2).
  - Avoid "jaggies", irregular steps like 1-2-1-3.
  - Avoid doubled 2 px lines where 1 px works.
- **Lone pixels** are fine as eyes, sparkles and highlights. Many of them on a surface read as noise.

## Characters and animation

- **Proportions at 16 px:** the head takes 6-7 rows, the body 4-5 and the legs 3. Eyes are single dark pixels two apart with a skin pixel between.
- **Derive frames from one drawing.** Draw the base pose once, then build frames by moving parts in code. `examples/meadow-kit/art/hero.py` makes idle by sinking the head and arms 1 px and walk by lifting each foot and raising the body. This keeps every frame consistent, and fixing the base fixes them all.
- **Frame counts:**
  - idle: 2-4 frames, 400-700 ms each
  - walk: 4 frames at 8 fps (contact, passing, contact, passing)
  - run: 6
  - attack: 3-5, holding the anticipation and impact frames longer
- **Directions:** front (down), back (up) and one side, mirrored for the other side. Keep the pivot at the feet, the same in every frame.
- **Motion is a few pixels, not a few frames.** Moving 1 px between frames is clearest; smear and squash only on fast actions.

## Items, icons and props

- Read first, detail second: a coin is a circle with a highlight, a potion a bottle with liquid and a glint.
- **Spin animations:** full face, then three-quarter, then edge, then a mirrored three-quarter (see the coin in `sprites/items.px`).
- Props stand on their base. Set the anchor at the base, so maps can place them by their ground point.

## Tilesets

- **Corner autotiles (16 tiles):** two terrains meet; tile index = NW*8 + NE*4 + SW*2 + SE, where 1 means the second terrain.
  - `examples/meadow-kit/art/terrain.py` generates the set: the shape blends the corner values, and a little noise fades to zero at the edges so neighbours always meet.
  - The edges get pixel-art treatment: a light lip where grass overhangs dirt, a dark rim elsewhere, and a shadow under the lip.
- **Seamless tiles:** keep texture away from tile edges, or wrap it. Test with a map.
- **Variants:** add 2-4 alternates of plain tiles (sprite meta `variants: {0: [0, 16, 17, 18]}`) or large areas show a 16 px repeat.
- **Texture is placed, not sprinkled:** a few tufts and pebbles per tile, on a mostly flat base. Per-pixel speckle reads as noise.
- **Animated tiles** (water, lava) shift a pattern that wraps exactly over the frame count, for example 4 px per frame over 4 frames on a 16 px tile.
- **Map preview** (`maps/*.txt`):

  ```
  tileset: grass_dirt
  tile: 16
  corners:          # one char per tile corner: '.' first terrain, '#' second
  ......
  ..##..
  props:            # name x y [frame], placed by anchor
  bush 20 30
  ```

## Workflow

1. Write the palette with `pixelate palette ramps` into `palette.json`, then add `ol` and `wh`.
2. Block the most important sprite first (the hero), at 1x. Export and look at the contact sheet, the silhouette and the GIF.
3. Fix readability, then build the remaining sprites around its style: same outline, light and shading.
4. Tiles next, then a map that puts everything together. The map is the real test: scale, contrast and repetition all show there.
5. Deliver `out/`: the strips and JSON for engines, the GIFs and contact sheet for people.
