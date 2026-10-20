# Authoring: the rigorous path for a new piece

This is the **author path**: the full process for making new work from a brief. It is not the default style loop in `SKILL.md` (style card, short brief, draw from a starter, one critique at the end, with no block-in and no specialist reviewers). Use it when the user asks for a full brief, or the work is meant to become a reusable library piece. The rigor pays off because others copy what comes out.

`SKILL.md` sends authoring here; the ten steps, their commands and stop rules live only in this file. It points to [brief.md](brief.md), [drawing.md](drawing.md), [delivery.md](delivery.md) and [art-director.md](art-director.md) for depth and uses only commands that exist today.

## Hard rules

- **Intake and brief approval come first.** The greyscale block-in (step 4) is the only drawing allowed before the user OKs the brief; nothing else is drawn until then. A full brief needs a bound independent A before the user confirms it, then drawing. A short brief has no brief-stage lead: after its block-in passes the block-in gate, the user confirms it as written, then drawing.
- **Block-in first.** A greyscale block-in passes `pixelate check BLOCKIN.png --blockin --brief brief.md`. A full brief's block-in goes to the lead with the brief; a short brief's does not.
- **One independent lead owns every grade.** It is a separate agent that did not write the brief or draw the work. You never grade your own work, and your report of a fix is not evidence. At most **three graded lead rounds per stage** (brief, still), counting round 1. Only the user can extend that.
- **Specialists observe and never grade.** After the first lead round, at most two scoped notes per artifact (`composition`, `lighting`, `set`, `character`), passed to the lead with `--consult`. `--prev` is only the previous *lead* critique.
- **The gate is not art quality.** A pass means the numbers are legal, not that the work is good. Keep four things apart; none proves another: the technical gate and heuristic warnings (`judge`, the `repeat` WARN), an independent lead grade, user approval, and licensing.
- **Paid or outside review needs a budget.** `pixelate critique ... --run`, another model or a person's time costs something. Without a budget the user has given, print the prompt (`pixelate critique ...` without `--run`), say the review has **not** happened, and stop at that stage, even if a reviewer is available: do not ask them to run it. Only the style loop, which has no review stage, may go on, and only as the unreviewed branch of [`SKILL.md`](../SKILL.md) step 8. Never run paid image or agent benchmarks on your own.
- **Original work only.** No borrowed characters, logos, UI layouts, worlds or names. A rebuild may depict the supplied place and camera. Draw everything in code; `references/assets/` and library pieces are read-only examples, never called.
- **Keep the camera the reference or the user asked for.** Orthographic presets (side, 3/4 top-down, 2:1 iso, oblique, military) are not perspective. For a one- or two-point view, build the projection on the native-pixel grid; do not swap in iso.
- **The user decides.** They confirm the brief, give go/no-go on one A still, and confirm the animation plan before any motion.
- **Every mode keeps working.** Still, scene loop, assets, era and music jobs all follow this path; they differ only in guide and starter.

## Starters and worked examples

A starter is a neutral placeholder piece, a place to begin. Copy one and replace its placeholders with the brief's subject; it is not a finished base, and none has been reviewed or graded. Passing the gate empty shows it renders and meets the technical limits, nothing more. Everything else in `library/` (except the starters) has status `study`: unreviewed, a reference for technique. `pixelate library test ID --quick` prints a study's `gate_ok`, and several studies currently fail the technical gate, so read them for technique, never as proof of a legal or approved result.

| the job | guide | starter | how to copy it |
|---|---|---|---|
| a still scene | [scenes.md](../guides/scenes.md) | `starter-scene-still` | `pixelate remix starter-scene-still work/NAME --request "..."` |
| a looping scene with sound | [scenes.md](../guides/scenes.md) | `starter-scene-loop` | `pixelate new scene work/NAME` |
| a console-era screen | [eras.md](../guides/eras.md) | `starter-era-nes` (NES limits only) | `pixelate remix starter-era-nes work/NAME --request "..."` |
| a photo or place, one- or two-point perspective | [rebuild.md](../guides/rebuild.md) | `starter-rebuild-perspective` (two-point) | `pixelate remix starter-rebuild-perspective work/NAME --request "..."` |
| sprites, items, tiles | [assets.md](../guides/assets.md) | `starter-assets` | `pixelate new assets work/NAME` |
| music alone | [music.md](../guides/music.md) | `starter-music` | `pixelate new music work/NAME` |

`NAME` becomes the new piece id, so it is a lowercase slug and the folder must not exist yet. `new` only copies; `remix` runs the starter's own checked-in commands without a sandbox, as `pixelate render` does on either copy. Copy only checked-in starters, and never run contributed or user-supplied drawing code this way. `remix` also renders the unedited copy once and writes `REMIX.md` ([remix.md](remix.md)); on this path read it for the anatomy table (which file draws what) and ignore its remix-only plan. Each guide names the worked examples for its mode.

## The ten steps

Copy these into your todo list first; a skipped step stays as `skip: <reason>`.

1. **Intake, then the intent.** `pixelate route --intake "REQUEST"` (MCP `intake_request`). Only for disposition `offer`, optionally ask its two questions; accept answers in the user's words, proceed if they skip, and fold explicit answers into the request. For `direct`, ask nothing. Write one line on what the user wants but did not say ([brief.md](brief.md#read-the-intent)).
2. **Route as a hint, with the brief.** `pixelate route "CLARIFIED REQUEST" --brief [STYLE] -o brief.md` (`--full` forces the 11 sections). Section 0 shows the style, runners-up and defaults; rerun with a STYLE if your read disagrees. Routing reads request words, not a photo's geometry.
3. **Expand the brief.** Fill every TODO with a concrete choice, then `pixelate route --lint brief.md` until clean. Read [brief.md](brief.md), `library/lantern-isle/brief.md` (the bar for density) and, for an era piece, [eras.md](../guides/eras.md). For a rebuild, inspect the reference and record horizon, vanishing point(s), crop and near/far scale; `pixelate reference PHOTO -o reference.json` is optional, experimental evidence you correct by hand ([rebuild.md](../guides/rebuild.md#2-pick-the-camera)).
4. **Block-in, then the lead on the brief.** Draw the brief's boxes as flat greys, pass `pixelate check BLOCKIN.png --blockin --brief brief.md`, then give a separate lead the prompt from `pixelate critique --brief brief.md --block BLOCKIN.png`. Apply its ranked fixes, lint again, and request the next round with `--prev LEAD.md`. Within the [review budget](#review-budget), save each external lead report and bind it: `pixelate review record --brief brief.md --critique lead.md`, then `pixelate review status --brief brief.md`. Only READY is an A for this exact brief; it binds file hashes, not who the reviewer was. A short brief skips brief-stage review (no lead, no `review record`), not the greyscale block-in or its gate; once the gate passes it goes to step 5.
5. **The user confirms the brief.** Show a full brief with section 0 on top only at a bound A. Show a short brief as written once its block-in has passed the gate; it has no lead grade. A below-A budget stop is a report and a question, not an approval request ([brief.md](brief.md#confirm)).
6. **Draw it from scratch in code.** Read the mode's guide, run `pixelate tools TOPIC` or `MODULE` (it names the recipe for the subject), and read the section of [drawing.md](drawing.md) for what you draw. Start from a [starter](#starters-and-worked-examples) if useful.
7. **Pass the gate.** `pixelate check FRAME.png --style S --scale N` (add `--pal`, `--pre`, `--actor`, `--used`, `--intent`, `--brief`; `--era E` for an era piece; engine scenes also `pixelate check SCENE`). Redraw until every line passes. That means legal, not good ([delivery.md](delivery.md#gate)). For several images, list them in `piece.json` or `render.json` and run `pixelate render DIR`.
8. **Judge, then the lead on the still.** `pixelate judge FRAME.png --overlay judge.png`; fix each box or say why it stays. Then `pixelate critique FRAME.png --brief brief.md --prev LAST-LEAD.md`, gate again after each fix, and bind the A with `pixelate review record --brief brief.md --frame FRAME.png --critique lead.md` and `pixelate review status --brief brief.md --frame FRAME.png`. The `repeat` and judge findings are pointers for you; they do not replace the lead.
9. **One still to the user.** Only an A still that passed the gate goes up for go/no-go, with its last critique in one line. If review stopped below A, report the grade and unresolved ranked fixes and ask whether to continue or change the brief; do not present it as finished ([delivery.md](delivery.md#still)).
10. **Confirm the animation plan, then animate.** Show loop length in seconds and frames, what moves, each rate and frame count, every period dividing the loop. Animate only after the user says OK, gate every animated frame, and preview with `pixelate shot SCENE t [t...] --grid` ([delivery.md](delivery.md#animation-plan)). Music runs the same discipline: write it yourself, `pixelate check TRACK.wav` until it passes, and optionally `pixelate critique-music` ([music.md](../guides/music.md)).

## Review budget

- Default **three graded lead calls per stage**, round 1 included; an A ends the stage sooner. After the first lead round you may consult at most **two specialists in total per artifact**, each seeing the same brief and artifact and returning observations with no grade. Feed their saved notes to the next lead round with `--consult NOTE.md` (twice at most). They add no graded round.
- Apply the lead's ranked fixes, re-lint or re-gate, then call the lead again with `--prev` (the previous lead report only). The caller counts the rounds; the commands do not enforce it.
- **Stop on an A.** If round 3 is still below A, stop revising and reviewing that stage: report the grade and unresolved fixes, and ask the user whether to continue or change the brief. Only the user can allow more rounds.
- A below-A brief is not ready for drawing, and a below-A still is not finished.
- Music has its own three graded listening calls, only from an agent that actually hears the audio (`NOT REVIEWED` otherwise).
- A saved lead report plus `review record` is evidence for those exact bytes. Any change to the brief or frame makes it stale; record and check again.

## Perspective and camera

`tools/iso.py` renders the five orthographic views; it has no vanishing points. For a one- or two-point rebuild, set the camera from the reference's horizon and vanishing point(s) and draw it in screen space. `starter-rebuild-perspective` is a true two-point pinhole camera (`art/camera.py` solves focal length and yaw from the horizon and two vanishing points, and `art/massing.py` projects block corners) and is not an isometric preset. Replace its placeholder blocks with the reference's forms; keep the camera model a projection.

## Finishing

Export with the commands that exist: `pixelate build SCENE --release`, `pixelate video`, `pixelate gif`, `pixelate audio`, `pixelate assets PACK` ([delivery.md](delivery.md#export)). Report plainly what passed the gate, what grade the lead gave and for which bytes, what the user approved, and what was not checked. For a piece that declares working knobs, `pixelate render DIR --set name=value` renders a variant for any of the three runtimes: a script reads the typed values with `knobs()`, an engine scene's scripts read `PIXELATE_KNOBS.name`, and a pack's knob sets the `pack.json` option of its name ([piece.md](piece.md#knobs)). The report records what was given, not proof the program consumed the values; render the variant and look. Of the library pieces, only `starter-scene-loop` (`horizon`) and `starter-assets` (`scale`) declare knobs. `pixelate deliver DIR` renders every output once more, requires each image's gate and packages the outputs with a script-written `DELIVERY.md` in `DIR/dist/delivery`; `pixelate deliver DIR --verify` checks it without running anything. Neither grades, approves or clears rights ([delivery.md](delivery.md#deliver)).

`pixelate render` reports a non-blocking distance from a matching remix base ([remix.md](remix.md#distance-from-the-base)). MCP clients can use `find_pieces`, `remix_piece`, `render_piece` and `deliver_piece`; their execution tools still run trusted programs through the shell.

For your own inspected source, `pixelate library add DIR --status study --trust-local-code` stages a local contribution after two unsandboxed full renders, generates goldens and rebuilds the index ([CONTRIBUTING.md](../CONTRIBUTING.md)); the PR and rights review are still manual. MCP `add_piece` provides the same staging for an existing workspace catalog only with `trust_local_code=true`; it commits and publishes nothing. Keep its status `study` unless the evidence [piece.md](piece.md#status-evidence) asks for exists, and never infer `accepted` or `reviewed` from a passing gate. Licensing and rights to every source are a separate question that no check answers.
