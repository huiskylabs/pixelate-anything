# pixelate-anything

**Hand-crafted pixel art for AI agents.** It ships three ways:
- **An agent skill** (`SKILL.md`), which carries the craft.
- **A CLI** (`pixelate`), which does the work.
- **An MCP server**, so any MCP client can use the same tools, with previews returned as images the agent can look at.

![Lantern Isle through four seasons](docs/lantern-isle-seasons.png)

| mode | what you get |
|---|---|
| **Image to pixel art** | photos, paintings, logos and screenshots turned into clean pixel art (palette fitting, majority sampling, despeckle, outlines), not a blurry downscale |
| **Palettes** | hue-shifted ramps from a few base colours, extraction from references, presets, and export to Aseprite/GIMP/hex/JSON/PNG |
| **Assets** | sprites, characters with animations, items, corner autotiles with variants, and tilemaps, exported as PNG strips with Aseprite-style JSON, an atlas, GIFs, contact sheets and silhouette checks |
| **Scenes and loops** | pixel scenes that move through moods (seasons, dusk and rain, ...), exported as a live HTML page, a seamless 1080p/4K MP4, a GIF or stills |
| **Music** | generative lofi, chiptune (NES-style pulse, triangle and noise) and ambient, which follows a scene or stands alone as seamless game loops (OGG/WAV) |

![Photo to pixel art](docs/pixelate-photo.png)
![Meadow Kit: a hero, items and a generated autotile set, laid out as a map](docs/meadow-map.png)

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
- *"pixelate this photo of my dog in the Game Boy palette"*
- *"make a 16x16 knight with idle and walk animations and a dungeon tileset"*
- *"a 4K pixel-art lofi loop of a lighthouse through a storm into dawn"*
- *"a chiptune overworld theme that loops for my game"*

## CLI

```
pixelate image photo.jpg -o out.png --width 96 --palette sweetie-16
pixelate palette ramps sky=#3b5dc9 leaf=#5aa04a --steps 5 -o pal/mine
pixelate new assets my-pack && pixelate assets my-pack
pixelate new scene my-scene && pixelate shot my-scene 10 40 --grid && pixelate check my-scene --page
pixelate audio my-scene loop.wav && pixelate video my-scene out.mp4 --audio loop.wav
pixelate new music theme && pixelate audio theme theme.ogg
```

## MCP tools

The server's tools:
- **Guides and projects:** `guide`, `new_project`.
- **Files:** `write_file`, `read_file`, `list_files`. Writes stay inside the workspace.
- **Image, palette, assets:** `pixelate_image`, `palette`, `export_assets`, `generate_sprites`.
- **Scenes and output:** `preview_scene`, `check_scene`, `build_page`, `render_audio`, `render_video`, `render_gif`.

Tools that make pictures return them as images, so the agent can judge its own work. That is the single biggest quality lever. The workspace is the directory the agent starts the server in, or `$PIXELATE_WORKSPACE`.

## Layout

| path | what |
|---|---|
| `SKILL.md` | entry point: picks the mode, points to its guide |
| `guides/` | one guide per mode: pixelate, palettes, assets, scenes, music |
| `references/` | craft rules for a hand-made look; the scene engine API |
| `pixelate`, `tools/` | the CLI, the MCP server, setup, and the tools behind them |
| `engine/` | scene and loop engine: palette renderer, exact timeline, phase dissolves, soundtrack, page |
| `templates/` | `scene`, `music` and `assets` starting points |
| `examples/` | `lantern-isle` (a 4-season loop video) and `meadow-kit` (a game asset pack) |
| `palettes/` | presets |

## Why the loops are exact

- **Picture:** every frame is a pure function of its tick, and every animation period divides the loop.
- **Music:** random choices are seeded per cycle, and ambience beds and tape wobble turn a whole number of times per loop.
- **Checks:** the tools verify the seam. The audio after the loop matches its start (below −60 dB), and the last frame steps into the first like any other frame.

## License

MIT. Made by Huisky Labs.
