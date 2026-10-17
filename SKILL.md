---
name: pixelate-anything
description: Hand-crafted pixel art of any kind. Use it to rebuild a photo or a place as real pixel art (side view, 3/4 top-down or isometric), convert images, build palettes, draw sprites, characters, items and tilesets with sheets and GIFs, make pixel scenes and seamless animated loops with a generative soundtrack (lofi, chiptune, ambient) as a live page, MP4 or GIF, or make loopable game music.
---

# pixelate-anything

Pixel art that looks hand-made, drawn from scratch in code. Run `pixelate` (`<skill>/pixelate`); `pixelate --help` lists every command, `pixelate doctor` what is installed. With no shell, the MCP server has the same tools.

## Steps

Copy these 10 steps into your todo list first; a skipped step stays as `skip: <reason>`. Read only what each step names.

1. **Check intake, then read the intent.** Run `pixelate route --intake "REQUEST"` (or MCP `intake_request`). Only when disposition is `offer`, optionally ask its two questions. Accept answers in the user's own words, proceed if they skip, and combine explicit answers with the original request before the brief. For `direct`, proceed without intake questions. Read `references/brief.md#read-the-intent`.
2. **Route as a hint, in the same call as the brief.** Run `pixelate route "CLARIFIED REQUEST" --brief [STYLE] -o brief.md` (`--full` forces all 11 sections). Section 0 shows the style, runners-up and defaults; if your intent read disagrees, rerun with that STYLE. Skip plain `pixelate route` and `pixelate style --list` unless no runner-up fits.
3. **Expand into a brief.** Fill every TODO, then `pixelate route --lint brief.md`. Read `references/brief.md`, `examples/lantern-isle/BRIEF.md` (the bar) and, in era mode, `guides/eras.md` (the limits); each TODO names the `references/drawing.md` section and command it needs.
4. **Block-in, then art director on the brief.** Draw the brief's boxes as a greyscale block-in; pass `pixelate check BLOCKIN.png --blockin --brief brief.md`. Give a separate agent the prompt from `pixelate critique --brief brief.md --block BLOCKIN.png`, apply its changes and lint until it grades A (not for a short brief).
5. **The user confirms the brief.** Read `references/brief.md#confirm`.
6. **Draw everything from scratch in code.** Read the mode's guide (below), run `pixelate tools TOPIC` or `MODULE`, and read the `references/drawing.md` section for what you draw.
7. **Pass the gate.** Run `pixelate check FRAME.png --style S --scale N`; redraw until every line passes: that means legal, not good. Read `references/delivery.md#gate`.
8. **Art director on the still.** As in step 4, with `pixelate critique FRAME.png --brief brief.md --prev LAST.md`, gating again after each fix.
9. **One still to the user** for go/no-go. Read `references/delivery.md#still`.
10. **Confirm the animation plan, then animate.** Read `references/delivery.md#animation-plan`.

## Modes

| mode | the person wants | not this when | guide |
|---|---|---|---|
| scene | a still or an animated loop, a lofi cover, a place with no photo | a photo or a real place to rebuild | `guides/scenes.md` (+ `guides/music.md`) |
| rebuild | a photo or a real place as pixel art, an iso city | it's an invented place (scene) | `guides/rebuild.md` |
| era | a screen that obeys a console's limits (8-bit, Game Boy, 16-bit) | the era is only a look (scene with a style) | `guides/eras.md` |
| assets | sprites, a character, items, icons, tiles to reuse | the figure is part of one scene (scene) | `guides/assets.md` |
| music | a lofi, chiptune or ambient loop alone | it scores a scene (scene + `guides/music.md`) | `guides/music.md` |

A quick image conversion: `guides/pixelate.md`. A palette: `guides/palettes.md`.

## Hard rules

- Draw everything yourself in code. `references/assets/` holds read-only examples: read them, never call them.
- Pixel-art projections only: side, 3/4 top-down, 2:1 iso, oblique, military.
- Originals only: no existing characters, places, logos or UI.
- Rebuild, don't convert: `pixelate image` is a first pass at most.
- Every effect is done in code: light, particles, weather, never painted or filtered.
