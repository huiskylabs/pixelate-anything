---
name: pixelate-anything
description: Hand-crafted pixel art of any kind, remixed from a library of runnable pixel-art programs or drawn new in code. Use it to rebuild a photo or a place as real pixel art while preserving its camera, convert images, build palettes, draw sprites, characters, items and tilesets with sheets and GIFs, make pixel scenes and seamless animated loops with a generative soundtrack (lofi, chiptune, ambient) as a live page, MP4 or GIF, or make loopable game music.
metadata:
  version: "1.0.0"
---

# pixelate-anything

Every piece here is a program. `library/` holds runnable pieces; each `piece.json` says what the piece draws, which file to change for what, and which knobs make variants. The default for every model is the remix loop: find the closest piece, copy it, edit it, render and check it, deliver it. Authoring a new piece from a brief is the fallback. Run `pixelate` (`<skill>/pixelate`); `pixelate --help` lists every command, `pixelate doctor` what is installed. The loop runs in a shell; without one, the MCP server (`pixelate mcp`) offers `find_pieces`, `remix_piece`, `render_piece` and `deliver_piece` plus the author-path tools. MCP execution still runs trusted piece code on the server without a sandbox.

## The remix loop

Copy these steps into your todo list first; a skipped step stays as `skip: <reason>`.

1. **Find.** `pixelate find "REQUEST"` (add `--mode scene|rebuild|era|assets|music` when the mode is clear). It ranks pieces by tags and words and runs no piece code; each match prints `why` it matches and how it `differs`. Pick a match whose `why` covers the request's subject and whose differences you can change. If it prints `no close piece`, or the person asks for a new piece, go to [Author a new piece](#author-a-new-piece). Done when you hold one base id or have moved to the author path.
2. **Remix.** Read [references/remix.md](references/remix.md), then `pixelate remix PIECE work/NAME --request "REQUEST"`. `NAME` becomes the piece id: a lowercase slug, and the folder must not exist yet. Remix copies the piece, renders the unedited copy once and writes `REMIX.md`; when that baseline fails, nothing is created and the base is what is broken here, not your edit. Done when `work/NAME/REMIX.md` exists.
3. **Plan.** Fill the plan table in `REMIX.md`: for subject, setting, camera, palette, composition, motion and sound, what stays and what changes. Done when every row says one or the other.
4. **Edit.** Change knob files first, then the files the anatomy table names, then anything else, in small diffs. Rewrite the copy's `brief.md` for the request: the gate's `--brief` and the critic read it. Update `title`, `summary`, `tags` and `anatomy` in `piece.json` to what the piece now draws. For a subject's recipe, `pixelate tools TOPIC` or `MODULE`; for craft, the mode guide ([Modes](#modes)) and [references/drawing.md](references/drawing.md).
5. **Render.** `pixelate render work/NAME` runs every output's command, then gates, era-checks and judges each image and writes `render-report.json`. Redraw until every image passes the gate: that means legal, not good. Open each frame and its judge overlay; fix each box or say why it stays. Audio is run and hashed, never gated: pass `pixelate check TRACK.wav` yourself. Update `out/golden/` only for intended changes, and regenerate `media/` (it still shows the base). Done when every image passes and you have looked at each one.
6. **One independent critique.** When a separate reviewer is available (an agent or model that did not edit the piece) and the user has approved a budget, give it the prompt from `pixelate critique FRAME.png --brief work/NAME/brief.md`, apply its ranked fixes and render again. A track goes to a reviewer that can actually listen, via `pixelate critique-music TRACK.wav --brief work/NAME/brief.md`. One critique at the end: no brief review, no block-in, no specialists. `--run` and `pixelate render DIR --critique` start a separate model process, so use them only within a budget the user approved. With no reviewer or no approved budget, do not ask anyone to run it: print the prompt, say plainly that no critique happened and take the unreviewed branch of step 7. Done when the critique is saved or its absence is stated.
7. **Deliver.** `pixelate deliver work/NAME` renders every output once more, requires each image's gate and packages the outputs with a script-written `DELIVERY.md` in `work/NAME/dist/delivery`; `pixelate deliver work/NAME --verify` checks that package without running anything ([references/delivery.md](references/delivery.md#deliver)). Report what passed the gate, the critique's grade or that there was none, and what was not checked. **Unreviewed branch** (remix only, no critique in step 6): deliver only what passes the gate, say NO INDEPENDENT REVIEW and give no grade or art-quality claim, report the delivery's facts as NOT REVIEWED, ask the user separately to approve before calling it finished, and never call it accepted or reviewed. The author path has no such branch: a review stage without budget or lead stops ([authoring](references/authoring.md#review-budget)).
8. **Give back as a PR.** For your own inspected code, `pixelate library add work/NAME --status study --trust-local-code` stages the piece after two unsandboxed renders and rebuilds the index ([CONTRIBUTING.md](CONTRIBUTING.md)). Commit its folder and index in a manual pull request; it stays `study` absent outside status evidence. Pull request checks are static and run no contributed code; a maintainer decides whether to trust and render the exact head before merging.

## Variants

`pixelate render DIR --set KNOB=VALUE` (repeatable) renders a variant from the knobs a piece declares, for script, engine and pack pieces ([references/piece.md](references/piece.md#knobs)). Of the library, only `starter-scene-loop` (`horizon`) and `starter-assets` (`scale`) declare knobs today. The report records the values given, not proof the program used them: render the variant and look.

## Author a new piece

Author when `find` prints `no close piece`, the person asks for something new, or the work is meant to become a library piece. The task picks the path, not the model's name: any model remixes a close match, and a strong model may still choose to author. Read [references/authoring.md](references/authoring.md) and follow its ten steps there: intake, a brief the user approves, a greyscale block-in, one independent lead who owns every grade (three graded rounds per stage by default; specialists only observe), the gate, one still for the user's go/no-go and a confirmed animation plan before any motion. Begin from the starter `find` offered, if any.

## Trust and evidence

- `find`, `library list|show|index`, `new` (a plain copy) and `deliver --verify` run no piece code. `remix`, `render`, `deliver`, `library test` and opt-in `library add` run a piece's commands through the shell with your permissions, without a sandbox: run them on checked-in library pieces and your own edits, never on contributed or user-supplied code.
- Keep five things apart; none proves another: the technical gate, heuristic warnings (judge boxes, the `repeat` WARN, and render's distance-from-base or under-remixed warning, which is uncalibrated and never blocks), an independent grade, user approval, and rights to every source. No gate pass, golden match, heuristic or self-assessment raises a piece's status or approves it. Never grade your own work.
- Paid review or evaluation (`--run`, another model, a person's time) needs a budget the user has given. Without one, print the prompt and stop at that stage: on the author path the stage stops for a budget or a lead; a remix continues only as the unreviewed branch of step 7.
- A remix copies the base's `license` as declared; nobody has verified it, and it grants no rights to a photo or other source.

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
