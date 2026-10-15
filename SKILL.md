---
name: pixelate-anything
description: Hand-crafted pixel art of any kind. Use it to turn images into clean pixel art, build palettes, draw sprites, characters, items and tilesets with sheets and GIFs, make pixel scenes and seamless animated loops with a generative soundtrack (lofi, chiptune, ambient) as a live page, MP4 or GIF, or make loopable game music.
---

# pixelate-anything

Pixel art that looks hand-made, not generated. One kit, six modes, shared tools.

Every mode follows the same loop:
1. Plan the palette.
2. Place the pixels deliberately.
3. Render a preview.
4. **Look at it.**
5. Fix it.

The tools handle the mechanical parts (colour maths, exact loops, exports). The quality comes from the art decisions and from looking at every preview.

## Pick the mode, then read its guide

| the person wants | mode | read |
|---|---|---|
| a photo, drawing or logo turned into pixel art | image | `guides/pixelate.md` |
| a palette (from a mood, a reference image, or for a game) | palette | `guides/palettes.md` |
| sprites, a character with animations, items, icons, a tileset, a sprite sheet | assets | `guides/assets.md` |
| a pixel illustration, wallpaper or thumbnail (still) | scene | `guides/scenes.md` |
| an animated loop or lofi video cover, as a live page, MP4 or GIF | scene | `guides/scenes.md` + `guides/music.md` |
| music: a lofi, chiptune or ambient loop, game music, a soundtrack | music | `guides/music.md` |

Before drawing anything in any mode, read `references/craft.md`: it holds the rules that separate hand-made pixel art from generic output.

## Run things

Use the single command `pixelate` (`<skill>/pixelate`, a Python 3 script):

```
pixelate doctor                         what is installed, what each mode needs
pixelate new scene|music|assets DIR     start from a template
pixelate image IMG -o out.png ...       image -> pixel art
pixelate palette ramps|extract|show|list ...
pixelate assets PACK                    export sprites, sheets, GIFs, atlas, tilemaps
pixelate shot SCENE 5 30 --grid         preview frames (then LOOK at them)
pixelate check SCENE --page             automated checks
pixelate build SCENE --release          live HTML page
pixelate audio SCENE loop.wav|ogg       seamless music loop
pixelate video SCENE out.mp4 --audio loop.wav [--scale S]
pixelate gif SCENE out.gif
```

What each mode needs:
- **Image, palette and assets modes:** Python with pillow and numpy only.
- **Scenes:** add node.
- **Video and GIF:** add ffmpeg.
- **Music and the page check:** add Playwright Chromium.

If the agent has no shell but has the MCP server, the same tools exist as MCP tools: `pixelate_image`, `palette`, `export_assets`, `preview_scene`, `render_video`, and the rest.

## Rules for every mode

- **Palette first, and keep it strict.**
  - Each material gets 3 to 5 hue-shifted tones: shadows cooler, lights warmer.
  - The same slot names keep the same meaning everywhere.
  - Use no colour outside the palette, and no blur, anti-aliasing or alpha blending.
- **Hand-place and keep it asymmetric.** Pick positions yourself; uniform scatter and symmetry read as generated.
- **Outlines and one light direction.** Every form has a dark outline from its own ramp, a lit side and a shadow side.
- **Look at every preview at zoom.** The usual failures are mush, noise, stripes, a subject too small, and a recolour sold as a variation. Fix them before adding more.
- **Export at whole-number scales** with nearest neighbour, so pixels stay square. For video, use even scales, which keep colours exact.

## Layout

- `pixelate`: the command; `tools/`: everything it runs (also `tools/mcp_server.py`)
- `guides/`: one guide per mode; `references/`: craft rules and the scene engine API
- `engine/`: the scene and loop engine (picture, timeline, soundtrack, page)
- `templates/`: starting points for `scene`, `music` and `assets` (used by `pixelate new`)
- `examples/`:
  - `lantern-isle`: a 4-season loop, the quality bar for scenes.
  - `meadow-kit`: a hero, items, an autotile set and a map.
- `palettes/`: presets (`pixelate palette list`)
