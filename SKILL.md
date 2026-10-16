---
name: pixelate-anything
description: Hand-crafted pixel art of any kind. Use it to rebuild a photo or a place as real pixel art (side view, 3/4 top-down or isometric), convert images, build palettes, draw sprites, characters, items and tilesets with sheets and GIFs, make pixel scenes and seamless animated loops with a generative soundtrack (lofi, chiptune, ambient) as a live page, MP4 or GIF, or make loopable game music.
---

# pixelate-anything

Pixel art that looks hand-made, drawn from scratch in code. Run `pixelate` (`<skill>/pixelate`); `pixelate --help` lists every command, `pixelate doctor` what is installed. With no shell, the MCP server has the same tools.

## Steps

Read only what each step names.

1. **Read the intent.** One line on what the user wants but didn't say. Read `references/brief.md#read-the-intent`.
2. **Route as a hint.** Run `pixelate route "REQUEST"`. The mode's guide (table below) is for step 5; the brief doesn't need it.
3. **Expand into a brief** (a short brief for a small ask; `--full` forces all 11 sections). Run `pixelate route "REQUEST" --brief -o brief.md`, fill every TODO, then `pixelate route --lint brief.md`. Read `references/brief.md`; each TODO names its section and command. The brief already lists techniques for its subjects; run `pixelate tools TOPIC` only for a subject it lacks.
4. **The user confirms the brief.** Read `references/brief.md#confirm`.
5. **Draw everything from scratch in code.** Run `pixelate tools TOPIC` or `pixelate tools MODULE`. Read the `references/drawing.md` section for what you draw.
6. **Pass the gate.** Run `pixelate check FRAME.png --style S --scale N`; redraw until every line passes. Read `references/delivery.md#gate`.
7. **One still to the user** for go/no-go. Read `references/delivery.md#still`.
8. **Confirm the animation plan, then animate.** Read `references/delivery.md#animation-plan`.

`pixelate style S` prints one style's rules, light, budgets and craft limits; `pixelate style --list` lists them.

## Modes

| mode | the person wants | guide |
|---|---|---|
| scene | a still or an animated loop, a lofi cover | `guides/scenes.md` (+ `guides/music.md`) |
| rebuild | a photo or place as pixel art, an iso city | `guides/rebuild.md` |
| era | an 8-bit, Game Boy or 16-bit screen | `guides/eras.md` |
| assets | sprites, a character, items, icons, tiles | `guides/assets.md` |
| music | a lofi, chiptune or ambient loop | `guides/music.md` |

A quick image conversion: `guides/pixelate.md`. A palette: `guides/palettes.md`.

## Hard rules

- Draw everything yourself in code. `references/assets/` holds read-only examples: read them, never call them.
- Pixel-art projections only: side, 3/4 top-down, 2:1 iso, oblique, military.
- Originals only: no existing characters, places, logos or UI.
- Rebuild, don't convert: redraw a photo, `pixelate image` is a first pass at most.
- Every effect is done in code: light, particles, weather, never painted or filtered.
