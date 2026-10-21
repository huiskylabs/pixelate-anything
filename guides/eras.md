# Console eras: classic looks from real limits

The classics look the way they do because of their hardware: few colours, small screens, sprites
of three colours, tiles that share palettes. `tools/era.py` holds these limits as presets and checks
any image against them (`pixelate era IMG --era nes`; MCP `era`).

**Make original work.** Use an era's limits and its genre conventions: side scrolling, a status
bar, a dialogue box, a title screen with a blinking prompt. Never use an existing game's
characters, worlds, names, logos or signature objects, and don't make "a version of" a known
game. Invent the hero, the place and the title. `library/retro-screens` shows the genre conventions:
- **Rooftop Run:** an 8-bit platformer over San Francisco rooftops.
- **Island Village:** a Game Boy-style RPG screen of the Santorini village.
- **Pixel Harbor:** a title screen.

`retro-screens` is a `study`, unreviewed, and not a legal base: its migration notes (`library/retro-screens/history/migration.md`) record the two NES screens above exceeding the 256-tile limit, while the Game Boy screen passes its era gate.

**Starter and worked examples.** A new era screen takes the style loop in `SKILL.md`, like any scene; the author path in `references/authoring.md` is for a new library piece. `starter-era-nes` is a neutral NES starter built the way the hardware builds a screen (an 8x8 tile nametable, 16x16 attribute blocks, a sprite list, 2C02 colours): `pixelate remix starter-era-nes work/NAME --request "..."`. It passes the NES gate empty and is unreviewed; it is no template for the other consoles. For another console, remix `starter-scene-still` and give its `piece.json` the console's screen: `canvas` and the output's `size` at the screen size, the delivered `scale`, and the output's `era` so the gate runs `--era` (`references/piece.md`); then replace its placeholders. `four-machines` draws one moment under four console limits and `quarry-wakes` is a Neo Geo-tagged scene; both are `study` status references to read.

## The presets

| era | screen | colour | the rules that shape the look |
|---|---|---|---|
| `nes` | 256x224 | the 2C02 master palette (`palettes/nes.hex`, 54 colours), 25 on screen | background: each 16x16 block uses one 3-colour sub-palette plus a shared backdrop (4 colours); sprites: 3 colours + transparent, layered for more |
| `gameboy` | 160x144 | 4 shades of one ramp (`palettes/gameboy.hex`, or any one-hue ramp) | everything in 4 shades; contrast does all the work |
| `snes` | 256x224 | 15-bit colour, 256 on screen | 16 colours per 8x8 tile |
| `genesis` | 320x224 | 9-bit colour, 61 on screen | 16 colours per 8x8 tile |
| `gba` | 240x160 | 15-bit colour, 256 on screen | 16 colours per 8x8 tile |
| `pico-8` | 128x128 | its 16 colours | |
| `cga` | 320x200 | black, cyan, magenta, white (`palettes/cga-mode4.hex`) | four fixed colours for everything; shown at 4:3, so a pixel is taller than wide (4x by 5x on its own); mixed tones only as hand-placed checker or 25% patterns |

## Designing inside the limits

**8-bit (NES-style)**
- **Plan sub-palettes:** a sky, a brick, a skyline, the lights. Keep each 16x16 area to about three colours plus the backdrop.
- **Skies:** bands with 2-row checker dithers between them.
- **Characters:** 3 colours (outline, main, skin), and a second overlapping sprite for accents (a scarf, a bag).
- **Depth:**
  - Use parallax layers: a far skyline fixed or barely moving, a mid skyline at half speed, the playfield at full speed.
  - Give each layer a period that divides the loop, so the screen loops exactly.

**Game Boy-style**
- **Shades:** four shades of one ramp. `palettes/gameboy.hex` is the DMG's green; the era check takes
  any one-hue ramp of four (the Pocket's greys, a green-grey), so use the request's.
- **Build the background from tiles.** Unique 8x8 tiles are the budget (256 on the hardware, often
  fewer in a request), and one stray pixel makes a tile unique:
  1. Draw a small tile set first, by role: sky (flat, the dither band, cloud edges), ground and rock
     (2-3 fills plus edges and corners), the building (wall, roof course, window, door, trim), water
     (2-3 wave tiles), and a few one-off tiles for the story spots.
  2. Lay the screen as a 20x18 map of those tiles; props that move and the actors are sprites on top.
  3. Count after every pass: `pixelate era BG.png --era gameboy --tiles --limit N` on the background
     alone prints the count. Reuse before adding: flat areas cost one tile, shift a pattern by whole
     tiles, and gather detail into a few spots. The DMG map cannot flip tiles, so a mirror costs one more.
- **Sprites:** 3 shades plus transparent, 10 per scanline and 40 on screen; the gate counts 8x8 cells
  from the brief's `- Sprites:` line, an upper bound (the 8x16 mode halves the total).
- **The 3/4 RPG view** (`guides/rebuild.md`, the `topdown` camera):
  - flat roofs from above, in the lightest shade;
  - fronts facing you, a shade down;
  - outlines in the darkest shade.
- **Dark elements** need a light ground to read against (a dome against a whitewashed terrace), and light ones need a dark ground (sails over the sea).
- **The dialogue box:** 2 px border, text in the darkest shade, a blinking arrow. `tools/pixfont.py` is a 5x7 font for HUDs and dialogue; `tools/cjkfont.py` draws Chinese and Japanese text (Ark Pixel 12px: `draw(img, text, x, y, colour, outline=)`, `width()`, `wrap()` with line-break rules).

**Retargeting a scene to an era.** Any scene can be pushed into an era: `era.enforce` snaps it to the palette and cuts colours. Night scenes need more than snapping, because nearest colours turn dark greys brown or teal. Map everything that is not a light onto an era-appropriate ramp by lightness (an NES night is black, deep blue, indigo, periwinkle), and snap only the lights. `library/retro-screens/art/title_screen.py` does this.

**Check it.** Run `pixelate era OUT.png --era nes`. For background-only layers, add `--layer bg` to apply the per-block rule, and `--tiles` (with `--limit N` for a request's own budget) to count the unique tiles.
