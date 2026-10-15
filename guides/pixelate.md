# Image to pixel art

`pixelate image IMG -o out.png [options]` turns a photo, painting, logo, screenshot or
render into real pixel art. It is not a downscale: it fits a palette, picks each pixel
deliberately, and cleans up stray pixels. It writes `out.png` (1x, indexed) and
`out@Nx.png` (a nearest-neighbour preview to look at).

## Choose the settings

| question | option |
|---|---|
| How big? | `--width N` sets output pixels across. Use 32-64 for icons and avatars, 64-128 for portraits, 160-320 for scenes. Or use `--block 8` for one pixel per 8 source pixels. |
| Which colours? | `--colors N` finds N colours in the image (8-24 is typical). `--palette NAME` uses a preset (`pico-8`, `sweetie-16`, `gameboy`, your own `.hex`/`.gpl`/`.json`, or `"#a,#b,..."`). |
| What kind of source? | `--mode photo` (the default for jpg): smooths texture first, then takes each block's mean. `--mode art` (the default for png): takes the majority colour per block, which keeps hard edges and thin lines. |
| A monochrome palette? | `--match luma` maps by brightness. It is picked automatically when the palette has little hue variety, as with gameboy. |
| Gradients look banded? | `--dither ordered` dithers mixed blocks between their two nearest colours. Leave it off for clean flats. |
| A cut-out sprite? | `--outline` adds a 1 px outline in the darkest colour around opaque shapes, and transparency is kept. |
| A flat result? | Raise `--sat` (default 1.15) and `--contrast` (default 1.1), which are applied before fitting. |

## Workflow

1. Run with defaults at two or three widths (for example 64, 96 and 128), and look at the previews.
2. Pick the width where the subject reads with the fewest pixels. Smaller is more "pixel art".
3. Try `--colors` lower (8-12) for a stronger style, or a preset palette to match a game.
4. **Finish by hand.** Automated pixelation is a strong first pass, not the final art. Fix:
   - **Faces:** use 1-2 px eyes in the darkest colour, a clean mouth line, and remove stray pixels on the skin.
   - **Silhouettes:** close gaps in the outline and straighten jagged diagonals into clean 1:1, 1:2 or 2:1 steps.
   - **Noise:** merge leftover lone pixels into their neighbours unless they are deliberate highlights.

   To edit, load the PNG into a Grid (`artlib`) or rewrite rows as a `.px` sprite (see `guides/assets.md`), then export again.
5. For game assets, put the result in an asset pack and export it as sheets.

## Notes

- Portraits and photos come out recognisable but painterly. A pixel artist would still redraw the eyes and mouth; you should too.
- Art mode almost perfectly reconstructs art that was originally pixel art, such as a blurry upscaled screenshot. Set `--width` to its original pixel width.
- To pixelate in the style of an existing piece, extract its palette (`pixelate palette extract ref.png -n 16 -o pal`) and pass `--palette pal.hex`.
