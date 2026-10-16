---
name: pixelate-anything
description: Hand-crafted pixel art of any kind. Use it to rebuild a photo or a place as real pixel art (side view, 3/4 top-down or isometric), convert images, build palettes, draw sprites, characters, items and tilesets with sheets and GIFs, make pixel scenes and seamless animated loops with a generative soundtrack (lofi, chiptune, ambient) as a live page, MP4 or GIF, or make loopable game music.
---

# pixelate-anything

Pixel art that looks hand-made, drawn from scratch in code. Run `pixelate` (`<skill>/pixelate`); `pixelate --help` lists every command, `pixelate doctor` what is installed. With no shell, the MCP server has the same tools.

## Steps

Copy these 8 steps into your todo list first. A step you skip stays there as `skip: <reason>`. Read only what each step names.

1. **Read the intent.** One line on what the user wants but didn't say. Read `references/brief.md#read-the-intent`.
2. **Route as a hint, in the same call as the brief.** Run `pixelate route "REQUEST" --brief [STYLE] -o brief.md` (a short brief for a small ask; `--full` forces all 11 sections). Section 0 shows the picked style, the runners-up and the defaults; if your intent read disagrees, rerun with that STYLE. Plain `pixelate route "REQUEST"` only when you want to compare styles first.
3. **Expand into a brief.** Fill every TODO, then `pixelate route --lint brief.md`. Read `references/brief.md` and `examples/lantern-isle/BRIEF.md` (the bar); each TODO names the `references/drawing.md` section and command it needs, read just those. The brief lists techniques for the subjects the request names; run `pixelate tools TOPIC` only for a subject it lacks.
4. **The user confirms the brief.** Read `references/brief.md#confirm`.
5. **Draw everything from scratch in code.** Read the mode's guide (table below), run `pixelate tools TOPIC` or `pixelate tools MODULE`, and read the `references/drawing.md` section for what you draw.
6. **Pass the gate.** Run `pixelate check FRAME.png --style S --scale N`; redraw until every line passes. Read `references/delivery.md#gate`.
7. **One still to the user** for go/no-go. Read `references/delivery.md#still`.
8. **Confirm the animation plan, then animate.** Read `references/delivery.md#animation-plan`.

`pixelate style S` prints one style's rules, light, budgets and craft limits; `pixelate style --list` lists them.

## Modes

| mode | the person wants | not this when | guide |
|---|---|---|---|
| scene | a still or an animated loop, a lofi cover, a place with no photo | they give a photo or name a real place to rebuild | `guides/scenes.md` (+ `guides/music.md`) |
| rebuild | a photo or a real place as pixel art, an iso city | it's an invented place (scene) | `guides/rebuild.md` |
| era | a screen that obeys a console's limits (8-bit, Game Boy, 16-bit) | the era is only a look, no hard limits (scene with a style) | `guides/eras.md` |
| assets | sprites, a character, items, icons, tiles to reuse | the figure is part of one scene (scene) | `guides/assets.md` |
| music | a lofi, chiptune or ambient loop alone | it scores a scene (scene + `guides/music.md`) | `guides/music.md` |

A quick image conversion: `guides/pixelate.md`. A palette: `guides/palettes.md`.

## Hard rules

- Draw everything yourself in code. `references/assets/` holds read-only examples: read them, never call them.
- Pixel-art projections only: side, 3/4 top-down, 2:1 iso, oblique, military.
- Originals only: no existing characters, places, logos or UI.
- Rebuild, don't convert: redraw a photo, `pixelate image` is a first pass at most.
- Every effect is done in code: light, particles, weather, never painted or filtered.
