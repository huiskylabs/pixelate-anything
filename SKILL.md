---
name: pixelate-anything
description: Hand-crafted pixel art of any kind. Use it to rebuild a photo or a place as real pixel art (side view, 3/4 top-down or isometric), convert images, build palettes, draw sprites, characters, items and tilesets with sheets and GIFs, make pixel scenes and seamless animated loops with a generative soundtrack (lofi, chiptune, ambient) as a live page, MP4 or GIF, or make loopable game music.
---

# pixelate-anything

Pixel art that looks hand-made, not generated. One kit, several modes, shared tools.

**Rebuild, don't convert.** Given a photo of a place or a thing, the default is to rebuild it: keep the reference's composition and camera, redraw every shape on clean pixel lines in a projection pixel art uses, choose the palette, and add life. Conversion (`pixelate image`) is a quick first pass, a reference underlay, or the right call only for paintings and simple bold subjects.

## How every job runs

1. **Read the intent.** Write one line on what the user most likely wants but didn't say: the feeling, the use, the era it recalls, what would disappoint them.
2. **Route as a hint.** `python3 tools/route.py "the request"` ranks styles and names the mode. It matches keywords, so it informs the choice; you make it.
3. **Expand into a brief.** `route.py "the request" --brief`, fill every TODO with concrete choices, `--lint` it. A full job gets the 11 sections plus section 0, the choices to confirm. A small ask (a palette, one sprite, an icon set, a pixelated photo) gets a short brief. See "From one line to a brief" in `references/craft.md`.
4. **The user confirms the brief.** Build only from an approved brief.
5. **Draw everything from scratch in code.** The tools in `tools/` are drawing primitives with no look of their own (canvas and slot grid, palettes and ramps, outlines, dither, shapes and masks, material textures, light layers, projections, animation timing) plus the checks; `guides/toolkit.md` lists them. Finished objects in `references/assets/` (boats, cats, props, runes, particle sprites) are examples to read, never call (`references/assets/README.md`). Anything missing is a slot map you write.
6. **Pass the gate.** `pixelate check FRAME.png --style S --scale N` (and `pixelate check SCENE` for engine scenes). Redraw until every line passes. Taste beyond the numbers is the next step.
7. **Show one still for go/no-go.** The user accepts it or asks for changes.
8. **Only then animate,** after the user confirms the animation plan: loop length, what moves, and the rates.

The tools handle the mechanical parts (colour maths, exact loops, exports). The quality comes from the art decisions and from looking at every preview at zoom.

## Pick the mode, then read its guide

| the person wants | mode | read |
|---|---|---|
| a photo of a place, building or scene as pixel art (the default for photos) | rebuild | `guides/rebuild.md` |
| an isometric or top-down city, diorama, map or tileset | rebuild / assets | `guides/rebuild.md` + `guides/assets.md` |
| a screen in a classic console style (8-bit, Game Boy, 16-bit), a title screen, a retro look | eras | `guides/eras.md` (+ `guides/assets.md`) |
| a quick conversion: a painting, logo, screenshot, or a photo as a reference underlay | image | `guides/pixelate.md` |
| a palette (from a mood, a reference image, or for a game) | palette | `guides/palettes.md` |
| sprites, a character with animations, items, icons, a tileset, a sprite sheet | assets | `guides/assets.md` |
| a pixel illustration, wallpaper or thumbnail (still) | scene | `guides/scenes.md` |
| an animated loop or lofi video cover, as a live page, MP4 or GIF | scene | `guides/scenes.md` + `guides/music.md` |
| music: a lofi, chiptune or ambient loop, game music, a soundtrack | music | `guides/music.md` |

Read `references/craft.md`: it holds the rules that separate hand-made pixel art from generic output, and the brief every job starts from. For a look learned from a game style (pastel platformer, contre-jour, neon noir, arcade, tactics iso and others), read `guides/styles.md`.

## Run things

Use the single command `pixelate` (`<skill>/pixelate`, a Python 3 script):

```
pixelate doctor                         what is installed, what each mode needs
pixelate new scene|music|assets DIR     start from a template
pixelate image IMG -o out.png ...       image -> pixel art
pixelate palette ramps|extract|show|list ...
pixelate assets PACK                    export sprites, sheets, GIFs, atlas, tilemaps, whole animated scenes
pixelate era IMG --era nes|gameboy|snes|genesis|gba|pico-8 [-o OUT]   check or force console-era limits
pixelate shot SCENE 5 30 --grid         preview frames (then LOOK at them)
pixelate check FRAME.png --style S --scale N   the gate, one frame
pixelate check SCENE --page             the gate, an engine scene
pixelate build SCENE --release          live HTML page
pixelate audio SCENE loop.wav|ogg       seamless music loop
pixelate check TRACK.wav --style S --use loop|showcase|song   the music gate (any code made it)
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
- **Draw it yourself, in code.** Never paste or trace an image, and never call a finished object from `references/assets/`; read it, then draw your own at the scene's size and style.
- **Hand-place and keep it asymmetric.** Pick positions yourself; uniform scatter and symmetry read as generated.
- **Outlines and one light direction.** Every form has a dark outline from its own ramp, a lit side and a shadow side.
- **Look at every preview at zoom.** The usual failures are mush, noise, stripes, a subject too small, and a recolour sold as a variation. Fix them before adding more.
- **Nothing is shown or delivered before the gate passes.** The frame gate checks budget, square pixels, palette (`--pal`, `--pre`), readability (`--actor`), allowed post ops (`--used`) and pixel craft (`--intent` marks deliberate flecks). The music gate does the same for sound: write the music yourself in any code, render it, `pixelate check TRACK.wav` until it passes (`guides/music.md`).
- **Export at whole-number scales** with nearest neighbour, so pixels stay square. For video, use even scales, which keep colours exact.

## Layout

- `pixelate`: the command; `tools/`: everything it runs (also `tools/mcp_server.py`)
- `guides/`: one guide per mode; `references/`: craft rules and the scene engine API
- `engine/`: the scene and loop engine (picture, timeline, soundtrack, page)
- `templates/`: starting points for `scene`, `music` and `assets` (used by `pixelate new`)
- `examples/`:
  - `san-francisco`: an aerial photo rebuilt in its own 3/4 camera and as an isometric diorama, day to night. The quality bar for rebuilds.
  - `projections`: one scene in the five projections (side, 3/4 top-down, 2:1 iso, oblique, military).
  - `retro`: original classic-genre screens under console-era limits (8-bit platformer, Game Boy-style RPG, title screen).
  - `lantern-isle`: a 4-season loop, the quality bar for scenes.
  - `meadow-kit`: a hero, items, an autotile set and a map.
  - `gallery`: what the `demo/` scripts make through the CLI and the MCP server.
- `palettes/`: presets (`pixelate palette list`)
