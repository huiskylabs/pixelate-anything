# pixelate-anything

**Hand-crafted pixel art for AI agents.**

![Lantern Isle in winter: a cottage on a snowy island under the northern lights](docs/lantern-isle-winter.png)

*Lantern Isle in winter, one season of a seamless four-season loop with its own lofi soundtrack. Every pixel, the aurora, the snowfall and the lamplight on the water are drawn in code by the kit.*

It ships three ways:
- **An agent skill** (`SKILL.md`), which carries the craft.
- **A CLI** (`pixelate`), which does the work.
- **An MCP server**, so any MCP client can use the same tools, with previews returned as images the agent can look at.

**Rebuild, don't convert.** Give it a photo of a place, and the agent does what a pixel artist would:
- keeps the photo's composition and camera,
- reads the place's shape language,
- keeps the reference's perspective when it matters, or chooses a stylized projection,
- picks the palette,
- adds the life the photo doesn't have.

| San Francisco, in the photo's own 3/4 camera | the same blocks, isometric | Santorini, from a Pexels aerial |
|---|---|---|
| ![SF rebuild](docs/sf-rebuild.gif) | ![SF isometric](docs/iso-city.gif) | ![Santorini](docs/santorini.gif) |

**Classic genres, original games.** Console-era presets (8-bit NES-style, Game Boy-style, 16-bit) hold art to the hardware's limits and check it.

| Rooftop Run, an 8-bit platformer screen | Island Village, Game Boy-style | Pixel Harbor, a title screen from the iso city |
|---|---|---|
| ![Rooftop Run](docs/rooftop-run.gif) | ![Island Village](docs/island-village.gif) | ![Pixel Harbor](docs/title-screen.gif) |

![One scene in five orthographic projection presets](docs/projections.png)

**Scenes that loop forever.** Lantern Isle turns through four seasons with its own generative lofi soundtrack, as a seamless 1080p or 4K video.

![Lantern Isle through four seasons](docs/lantern-isle-seasons.png)

| mode | what you get |
|---|---|
| **Rebuild** | a photo of a place rebuilt with its camera or one of five orthographic presets (side, 3/4 top-down, 2:1 iso, oblique, military). Vanishing-point views are drawn on the native-pixel canvas; the orthographic renderer handles boxes and curved solids (rounded boxes, vaults, domes, arches, terrain), cast shadows, palette swaps from day to night, and palette-cycled water |
| **Eras** | original screens under real console limits: 8-bit NES-style (master palette, 4-colour blocks, 3-colour sprites), Game Boy-style 4 shades, 16-bit; a checker, retargeting, pixel fonts for HUDs and dialogue, including Chinese and Japanese |
| **Convert** | a quick mode for logos, screenshots and bold photos: palette fitting, majority sampling, despeckle, flattening, grading, cut-out sprites with outlines |
| **Palettes** | hue-shifted ramps from a few base colours, extraction from references, presets, and export to Aseprite/GIMP/hex/JSON/PNG |
| **Assets** | sprites, characters with animations, items, corner autotiles with variants, and tilemaps, exported as PNG strips with Aseprite-style JSON, an atlas, GIFs, contact sheets and silhouette checks |
| **Scenes and loops** | pixel scenes that move through moods (seasons, dusk and rain, ...), exported as a live HTML page, a seamless 1080p/4K MP4, a GIF or stills |
| **Music** | generative lofi, chiptune (NES-style pulse, triangle and noise) and ambient, which follows a scene or stands alone as seamless game loops (OGG/WAV) |


## Install

```sh
git clone https://github.com/huiskylabs/pixelate-anything
cd pixelate-anything
pip install -r requirements.txt     # pillow and numpy are required; mcp and playwright are optional
./pixelate doctor                   # shows what each mode needs (node for scenes, ffmpeg for video)
./pixelate setup                    # registers the MCP server and the skill with your agents (asks first)
```

`setup` covers:
- **Claude Code:** the MCP server, plus the skill in `~/.claude/skills`.
- **Cursor, Codex and Gemini CLI:** the MCP server.

It shows its plan, asks before changing anything, and backs up every file it edits. For any other MCP client, run the server with `python3 /path/to/pixelate-anything/pixelate mcp` (stdio).

Then ask your agent for anything pixel art:
- *"rebuild this aerial photo of my city as an isometric pixel-art scene, day to night"*
- *"make a 16x16 knight with idle and walk animations and a dungeon tileset"*
- *"a 4K pixel-art lofi loop of a lighthouse through a storm into dawn"*
- *"a chiptune overworld theme that loops for my game"*
- *"an 8-bit side-scrolling platformer screen of my city at sunset, NES limits"*

## CLI

```
pixelate route --intake "make a pixel scene"          # JSON plan with optional questions for a generic scene
pixelate route "a rainy town" --brief -o brief.md    # pre-filled scene brief
pixelate route --lint brief.md                       # check the completed brief
pixelate image photo.jpg -o out.png --width 96 --palette sweetie-16
pixelate era screen.png --era gameboy               # does it obey the console's limits?
pixelate palette ramps sky=#3b5dc9 leaf=#5aa04a --steps 5 -o pal/mine
pixelate new assets my-pack && pixelate assets my-pack
pixelate new scene my-scene && pixelate shot my-scene 10 40 --grid && pixelate check my-scene --page
pixelate audio my-scene loop.wav && pixelate video my-scene out.mp4 --audio loop.wav
pixelate new music theme && pixelate audio theme theme.ogg
pixelate style --list && pixelate style lofi        # every style, then one style's card
pixelate tools rain && pixelate tools post.Post.lightmap   # the kit on demand: a topic, a signature
pixelate critique --brief brief.md                  # an independent art director grades the brief
pixelate critique still.png --brief brief.md        # ... and then the still
pixelate critique still.png --brief brief.md --role lighting  # optional observations, no grade
pixelate critique still.png --brief brief.md --consult lighting.md  # lead reconciles notes
pixelate critique-music track.wav --brief brief.md  # opt-in listening-agent prompt after music gate
```

Intake offers two optional questions for a generic scene request. A specific request goes straight to routing. The brief records camera choices; for a photo without a named view, inspect the reference before choosing one.

## MCP tools

The server's tools:
- **Guides and projects:** `guide`, `new_project`.
- **Intake and briefs:** `intake_request`, `route_request`, `write_brief`, `lint_brief`. The same routing and brief steps are available without a shell.
- **Styles and the kit on demand:** `style_card`, `kit_tools` (the same as `pixelate style NAME` and `pixelate tools [QUERY]`).
- **Files:** `write_file`, `read_file`, `list_files`. Writes stay inside the workspace.
- **Image, palette, assets:** `pixelate_image`, `palette`, `export_assets`, `generate_sprites`.
- **Gate and critique:** `check_frame`, `check_music`, `critique_prompt` (lead or scoped visual specialist, with optional lead consult notes), `music_critique_prompt` (opt-in prompt for a separate agent to listen after the music gate).
- **Scenes and output:** `preview_scene`, `check_scene`, `build_page`, `render_audio`, `render_video`, `render_gif`.

Tools that make pictures return them as images, so the agent can judge its own work. A second agent that did not draw it judges better: `critique_prompt` gives the lead the rubric, brief and images; optional specialists observe without grading. `music_critique_prompt` does not listen or invoke an agent. The workspace is the directory the agent starts the server in, or `$PIXELATE_WORKSPACE`.

## Layout

| path | what |
|---|---|
| `SKILL.md` | lean entry point: the ten steps, each naming one command and one file to read |
| `guides/` | one guide per mode: rebuild, eras, pixelate, palettes, assets, scenes, music |
| `references/` | `brief.md` (intent to approved brief), `drawing.md` (how to draw), `delivery.md` (gate, art director, still, animation plan), `art-director.md` (the critique rubric); the scene engine API |
| `pixelate`, `tools/` | the CLI, the MCP server, setup, and the tools behind them (`iso.py`: orthographic projections and boxes; `sdf.py`: curved solids) |
| `tools/route_regression_cases.py`, `tests/` | routing examples and intake tests |
| `engine/` | scene and loop engine: palette renderer, exact timeline, phase dissolves, soundtrack, page |
| `templates/` | `scene`, `music` and `assets` starting points |
| `examples/` | `san-francisco` and `santorini` (rebuilds), `projections`, `retro` (original 8-bit and Game Boy-style screens), `lantern-isle` (a 4-season loop video), `meadow-kit` (a game asset pack), `gallery` (what the demos make) |
| `demo/` | `cli_demo.sh` and `mcp_demo.py`: the gallery, made through each interface |
| `palettes/` | presets |
| `fonts/` | Ark Pixel 12px for Chinese and Japanese text |

## Why the loops are exact

- **Picture:** every frame is a pure function of its tick, and every animation period divides the loop.
- **Music:** random choices are seeded per cycle, and ambience beds and tape wobble turn a whole number of times per loop.
- **Checks:** the tools verify the seam. The audio after the loop matches its start (below −60 dB), and the last frame steps into the first like any other frame.

## License

MIT. Made by Huisky Labs.

The CJK pixel font in `fonts/` is [Ark Pixel Font](https://github.com/TakWolf/ark-pixel-font) by TakWolf, under the SIL Open Font License 1.1 (`fonts/OFL.txt`). Reference photos and their licenses are listed in `examples/gallery/SOURCES.md`.
