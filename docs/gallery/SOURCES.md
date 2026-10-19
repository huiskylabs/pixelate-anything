# Gallery sources and licenses

The generated images, palettes and music are in this folder: `mcp/`, `palettes/` and `music/` (moved with `git mv` from `examples/gallery` in phase 1 of `docs/PLAN-library.md`). They are notes on what the demos make, not a library piece. They are regenerated, from the repository root, by:
- `demo/cli_demo.sh`: a palette (`palettes/winter-night`, not committed), a `library/retro-screens` export and era checks through the CLI.
- `demo/mcp_demo.py`: the `library/projections`, `library/san-francisco`, `library/santorini` and `library/retro-screens` exports, the `palettes/santorini` palette and `music/pixel-radio.ogg` from `library/starter-music`, made through the MCP server, which saves the returned images and copies each pack's `@2x`/`@3x` frames into `mcp/` (GIFs and MP4s there are not committed).

The pack exports land in each piece's `out/`; for these four packs git ignores everything there but `out/golden/`. The committed files predate the move: they were made from `examples/` and `templates/music`, so a regeneration can differ where a piece changed since (`music/pixel-radio.ogg` is the old "Pixel Radio" template; `library/starter-music` is now a subject-neutral scaffold, so a rerun writes a different loop). Regenerating rewrites these files; preserve the San Francisco reference provenance below.

## References that are not redistributed here

These are rebuilt rather than converted. The photos themselves are not in the repository.

| rebuild | reference | where |
|---|---|---|
| `library/san-francisco` (and the Pixel Harbor city in `library/retro-screens`, a copy of it) | aerial photo of the Financial District and the Transamerica Pyramid | The user confirmed this reference came from [Pexels](https://www.pexels.com/legal-pages/license/), which permits use and modification. The exact photo URL was not retained. The reference photo is **not** included or relicensed under the repository's MIT license; the first-party drawing code and resulting pixel art are. |
| `library/santorini` | "Houses on Hill" by Vasilis Karkalas | https://www.pexels.com/photo/houses-on-hill-11222833/ (Pexels license) |

## Fonts

| file | what | license |
|---|---|---|
| `fonts/ark-pixel-12px.hex` | Ark Pixel Font 12px by TakWolf (GB2312 hanzi, CJK punctuation, full-width forms, kana), from https://github.com/TakWolf/ark-pixel-font at commit 98b31730f7752e003baccf68e9c3ad507a6ddc91 | SIL OFL 1.1, see `fonts/OFL.txt` |

## Research for the projections

- https://en.wikipedia.org/wiki/Isometric_video_game_graphics
- https://slynyrd.com/blog/2018/4/12/pixelblog-4-graphical-projection-part-2
- https://compuphase.com/axometr.htm

## Original work

`library/retro-screens` (Rooftop Run, Island Village, Pixel Harbor) and `library/lantern-isle` are
original in their characters, places, titles and text, except that the Pixel Harbor city behind the title
screen is the `library/san-francisco` rebuild, with the Pexels reference provenance above. Console names in the era presets describe
hardware limits only.
