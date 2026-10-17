# Ten moments

Ten showcase requests for pixelate-anything, ranked by expected impact. Each one is rendered at its two best moments, with a five-second sound sample. Everything is drawn from scratch in code with the kit, and every still passes `pixelate check` for its style. Each folder holds:

- `brief.md`: the short brief (hero, planes, value plan, palette roles, sound plan, any gate override with its reason).
- `art/`: the drawing code.
- `out/`: the two stills (`NN-a.png`, `NN-b.png`) at a whole-number scale, plus their 1x versions and palettes.
- `sound/`: the 5 s sample (`NN-sample.mp3`) and the synth or engine project that renders it.

| # | moment | what you see | style, canvas | sound |
|---|---|---|---|---|
| 01 | [Monsoon Street, After Hours](01-monsoon-street) | A: the tram crosses the vanishing point in a downpour. B: at 2 a.m. the puddle mirrors the street. | rebuild of a Pexels photo in its own one-point camera; `cosy-lightmap` exterior, 480x270 at 4x | felt piano and brushes in B minor, rain bed, tram bell |
| 02 | [The Endless Ascent](02-endless-ascent) | A: the gondola passes the clock of a town carved into a giant trunk. B: it rises out of a cloud sea under the aurora. | `lofi`, 270x480 at 4x | guitar and Rhodes at 76 bpm, clock bell |
| 03 | [The Canyon That Moves Without Moving](03-canyon-cycle) | A: a rose sunset with lightning on the mesa. B: indigo night. Both decode from one index array. | `lofi`, 320x180 at 6x, palette cycling | ambient: thunder, wind and fire bed, music box |
| 04 | [The Tide Road Procession](04-tide-procession) | A: nine lanterns cross the causeway. B: the monastery door opens and spills light down the steps. | `contre-jour` beam, 640x360 at 3x | D Dorian drone, waves, bronze bell |
| 05 | [One Morning, Four Machines](05-four-machines) | A: one moment under four console limits (poster). B: the 16-bit panel at 4x. | Game Boy-, NES-, SNES- and GBA-style; each passes `pixelate era` | 16-bit arrangement: strings, FM bass, echo |
| 06 | [The Quarry Wakes](06-quarry-wakes) | A: a dredging machine breaks out of a flooded quarry. B: its leg slams the rim. | `arcade`, 304x224 at 4x, layers checked against `neogeo` | FM boss sting in E minor at 168 bpm |
| 07 | [Turntable Shipyard](07-turntable-shipyard) | A: dawn, bare ribs on the keel. B: night, the finished ship a quarter-turn later. | `tactics`, one 3D description in `iso`/`sdf`, 640x360 at 3x | 6/8 work song: concertina, mallets, saw |
| 08 | [Market Day, From the Bell Tower](08-market-day) | A: Strasbourg's street and squares at noon, full of market stories. B: the wedding on the hall steps at 8x. | rebuild of a Pexels aerial; `sticker-iso`, 600x600 at 4x | oom-pah march in B♭ over a crowd murmur |
| 09 | [Lanternmoss Mire](09-lanternmoss-mire) | A: the asset pack's map by day. B: the same tiles at night, glowing. | asset pack: 16x16 tiles, 16x24 hero, map 320x192 at 4x | chip SFX reel and item-get jingle |
| 10 | [Signal from Tidewater](10-tidewater-signal) | A: a keeper's radio on the sill in a storm (cassette cover). B: the lightning frame. | `lofi`, 270x480 at 4x | the overworld cue: pulse leitmotif at 132 bpm |

## Rebuild

Each script writes into its own folder's `out/` or `sound/`. Run them from that folder unless noted.

| # | stills | sound |
|---|---|---|
| 01 | `python3 art/render.py both` | `../../../pixelate audio music sound/full.wav`, then `python3 sound/make_sample.py` |
| 02 | `python3 art/scene_a.py` and `python3 art/scene_b.py` | `../../../pixelate audio music sound/full.wav`, then `python3 sound/make_sample.py` |
| 03 | `python3 art/render.py` | `../../../pixelate audio music sound/full.wav`, then `python3 sound/make_sample.py` |
| 04 | `python3 art/scene.py a b` | `../../../pixelate audio music sound/full.wav`, then `python3 sound/make_sample.py` |
| 05 | `python3 art/panel_gb.py`, `panel_nes.py`, `panel_snes.py`, `panel_gba.py`, then `python3 art/poster.py` | `python3 sound/theme.py` |
| 06 | `python3 art/scene.py A B` | `python3 sound/sting.py` |
| 07 | `python3 art/yard.py a` and `python3 art/yard.py b` | `python3 sound/shanty.py` |
| 08 | `python3 art/scene.py final out 130 162` | `python3 sound/march.py` |
| 09 | from the repo root: `./pixelate assets examples/moments/09-lanternmoss-mire`, then `python3 examples/moments/09-lanternmoss-mire/maps/render_map.py --gif` | `python3 sound/sfx_reel.py` |
| 10 | `python3 art/cover.py ab` | `../../../pixelate audio music sound/full.wav`, then `python3 art/sound.py` |

The engine-based samples (01-04 and 10) cut five seconds from a full render of the folder's `music/` project. The other samples are standalone numpy synths. Full-length renders and `.wav` files are not committed.

## Reference photos

01 and 08 rebuild photos from Pexels (Pexels license). They are rebuilt rather than converted, and the photos themselves are not in the repository.

- 01: [Night City Street after Rain Illuminated by Colorful Neon Signs Reflecting on a Wet Road](https://www.pexels.com/photo/night-city-street-after-rain-illuminated-by-colorful-neon-signs-reflecting-on-a-wet-road-18867525/) by Johannes Plenio
- 08: [Aerial View of Medieval Buildings on an Old Town](https://www.pexels.com/photo/aerial-view-of-medieval-buildings-on-an-old-town-14037897/) by Nick Verlice

All characters, places (other than the two rebuilt references), titles, glyphs and tunes are original.
