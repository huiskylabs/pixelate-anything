---
name: pixelate-anything
description: Hand-crafted pixel art of any kind, drawn new in code from a written style card, with a library of runnable pixel-art programs to learn from and remix. Use it to rebuild a photo or a place as real pixel art while preserving its camera, convert images, build palettes, draw sprites, characters, items and tilesets with sheets and GIFs, make pixel scenes and seamless animated loops with a generative soundtrack (lofi, chiptune, ambient) as a live page, MP4 or GIF, or make loopable game music.
metadata:
  version: "1.0.0"
---

# pixelate-anything

Every piece here is a program, drawn in code from a written style card. The default for every model is the style loop: pick a style, read its card, write a short brief, draw it new from a starter, render and check it, deliver it. `library/` holds runnable pieces; read them for technique after the brief, never as the starting picture, because starting from a finished piece makes every result look like it. Remix a piece directly only when the person asks for a variant of that piece. Authoring a library piece is the rigorous path. Run `pixelate` (`<skill>/pixelate`); `pixelate --help` lists every command, `pixelate doctor` what is installed. Without a shell, the MCP server (`pixelate mcp`) offers `find_pieces`, `remix_piece`, `render_piece`, `deliver_piece` and opt-in `add_piece` plus the author-path tools. MCP execution still runs trusted piece code on the server without a sandbox.

## The style loop

Copy these steps into your todo list; a skipped step stays as `skip: <reason>`.

1. **Style.** `pixelate route "REQUEST"` proposes a style; weigh it against what the person means. `pixelate style NAME` prints the card: essence, what it is not, pitfalls, variation space, then the numbers. The request beats the card's defaults. Done when you have picked a style and read its card.
2. **Brief.** `pixelate route "REQUEST" --brief STYLE -o brief.md`, fill every TODO with choices from the card's variation space, then `pixelate route --lint brief.md` until clean ([references/brief.md](references/brief.md)). Done when the lint is clean.
3. **Find, for technique.** Only now `pixelate find "REQUEST"` (add `--mode scene|rebuild|era|assets|music`). Read the closest pieces' code for how things are drawn. A brief that names a piece it studied needs a `Differs from ID:` line naming four of subject, composition, camera, palette, light and motion ([not the reference](references/brief.md#not-the-reference)); the lint checks it. If the person asks for a variant of one piece, or `find` prints a piece whose `why` is the request itself, read [references/remix.md](references/remix.md) and remix that piece instead; if the person asks for a new library piece, go to [Author a new piece](#author-a-new-piece). Done when the lint is still clean.
4. **Start.** `pixelate remix STARTER work/NAME --request "REQUEST"` with the mode's starter ([Modes](#modes)), or `pixelate remix PIECE ...` on the remix branch. `NAME` becomes the piece id: a lowercase slug, and the folder must not exist yet. Remix renders the unedited copy once and writes `REMIX.md`; a failing baseline creates nothing. Done when `work/NAME/REMIX.md` exists.
5. **Draw.** Put your brief in the copy as `brief.md` (the gate's `--brief` and the critic read it), then draw it in the copy's own code, replacing the starter's placeholders. Update `title`, `summary`, `tags` and `anatomy` in `piece.json`. For a subject's recipe, `pixelate tools TOPIC` or `MODULE`; for craft, the mode guide and [references/drawing.md](references/drawing.md).
6. **Render.** `pixelate render work/NAME` runs every output's command, then gates, era-checks and judges each image and writes `render-report.json`. Redraw until every image passes the gate: that means legal, not good. Open each frame and its judge overlay; fix each box or say why it stays. Audio is run and hashed, never gated: pass `pixelate check TRACK.wav` yourself. Done when every image passes and you have looked at each one.
7. **One independent critique.** When a separate reviewer is available (an agent or model that did not edit the piece) and the user has approved a budget, give it the prompt from `pixelate critique FRAME.png --brief work/NAME/brief.md`, apply its ranked fixes and render again. A track goes to a reviewer that can listen, via `pixelate critique-music TRACK.wav --brief work/NAME/brief.md`. One critique at the end: no brief review, no block-in, no specialists. `--run` and `pixelate render DIR --critique` start a separate model process, so use them only within an approved budget. With no reviewer or no approved budget, do not ask anyone to run it: print the prompt, say plainly that no critique happened and take the unreviewed branch of step 8. Done when the critique is saved or its absence is stated.
8. **Deliver.** `pixelate deliver work/NAME` renders every output once more, requires each image's gate and packages the outputs with a script-written `DELIVERY.md`; `pixelate deliver work/NAME --verify` checks that package without running anything ([references/delivery.md](references/delivery.md#deliver)). Report what passed the gate, the critique's grade or that there was none, and what was not checked. **Unreviewed branch** (style loop only, no critique in step 7): deliver only what passes the gate, say NO INDEPENDENT REVIEW and give no grade or art-quality claim, report the delivery's facts as NOT REVIEWED, ask the user separately to approve before calling it finished, and never call it accepted or reviewed. The author path has no such branch: a review stage without budget or lead stops ([authoring](references/authoring.md#review-budget)).
9. **Give back as a PR.** For your own inspected code, `pixelate library add work/NAME --status study --trust-local-code` (or MCP `add_piece` with `trust_local_code=true`) stages the piece after two unsandboxed renders and rebuilds the index ([CONTRIBUTING.md](CONTRIBUTING.md)). Commit its folder and index in a manual pull request; it stays `study`. Pull request checks are static and run no contributed code; a maintainer decides whether to trust and render the exact head before merging.

## Variants

`pixelate render DIR --set KNOB=VALUE` (repeatable) renders a variant from the knobs a piece declares, for script, engine and pack pieces ([references/piece.md](references/piece.md#knobs)). Of the library, only `starter-scene-loop` (`horizon`) and `starter-assets` (`scale`) declare knobs today. The report records values, not proof the program used them: look.

## Author a new piece

Author only when the person asks for something new to keep as a library piece; anything else takes the style loop. The task picks the path, not the model's name. Read [references/authoring.md](references/authoring.md) and follow its ten steps there: intake, a brief the user approves, a greyscale block-in, one independent lead who owns every grade (one graded round per stage by default; specialists only observe), the gate, one still for the user's go/no-go and a confirmed animation plan before any motion. Begin from the starter `find` offered, if any.

## Trust and evidence

- `find`, `library list|show|index`, `new` (a plain copy) and `deliver --verify` run no piece code. `remix`, `render`, `deliver`, `library test` and opt-in `library add` run a piece's commands through the shell with your permissions, without a sandbox: run them on checked-in library pieces and your own edits, never on contributed or user-supplied code.
- Keep five things apart; none proves another: the technical gate, heuristic warnings (judge boxes, the `repeat` WARN, and render's distance-from-base or under-remixed warning, which is uncalibrated and never blocks), an independent grade, user approval, and rights to every source. No gate pass, golden match, heuristic or self-assessment raises a piece's status or approves it. Never grade your own work.
- Paid review or evaluation (`--run`, another model, a person's time) needs a budget the user has given. Without one, print the prompt and stop at that stage: on the author path the stage stops for a budget or a lead; the style loop continues only as the unreviewed branch of step 8.
- A copy keeps the base's `license` as declared; nobody has verified it, and it grants no rights to a photo or other source.

## Hard rules

- Original subjects only: no borrowed characters, logos, UI, worlds or names. A rebuild may depict the supplied place and camera.
- Draw everything yourself in code. `references/assets/` holds read-only examples: read them, never call them.
- Every effect is done in code: light, particles, weather, never painted or filtered.
- Keep the camera of the reference or the request. The five views (side, 3/4 top-down, 2:1 iso, oblique, military) are orthographic presets, not limits; build a one- or two-point perspective as a real projection on the native-pixel grid instead of swapping in iso ([guides/rebuild.md](guides/rebuild.md#2-pick-the-camera)).
- Rebuild, don't convert: `pixelate image` is a first pass at most.

## Modes

Each starter is a neutral placeholder to replace, never a finished or reviewed piece.

- **Scene still** (a still, a cover, a place with no photo): `starter-scene-still`, [guides/scenes.md](guides/scenes.md).
- **Scene loop** (an animated loop with sound, as a page, MP4 or GIF): `starter-scene-loop`, [guides/scenes.md](guides/scenes.md) and [guides/music.md](guides/music.md).
- **Era** (a screen that obeys a console's limits): `starter-era-nes` (NES only), [guides/eras.md](guides/eras.md).
- **Rebuild** (a photo or real place in its own camera): `starter-rebuild-perspective`, a true two-point pinhole camera, not an isometric preset, [guides/rebuild.md](guides/rebuild.md).
- **Assets** (sprites, a character, items, icons, tiles, sheets): `starter-assets`, [guides/assets.md](guides/assets.md).
- **Music** (a lofi, chiptune or ambient loop alone): `starter-music`, [guides/music.md](guides/music.md).
- **Quick image conversion**: [guides/pixelate.md](guides/pixelate.md). **A palette**: [guides/palettes.md](guides/palettes.md).
