# Plan: the four parts of the moat

Why the skill should beat a bare model given the same long prompt, and what to build so it does. The background is in `docs/HANDOFF-skill-improvements.md` (sections 2 and 6). Instructions are not a moat: models absorb them and anyone can copy `SKILL.md`. These four can be.

Round-two review of this plan, after phase 1 landed: `docs/REVIEW-moat.md`.

| # | Workstream | What a bare model lacks | Status |
|---|---|---|---|
| 1 | **The judge**: detectors that locate defects, a built-in critic, and a corpus of draft → critique → fix | It can't reliably see its own pixel-art failures, and it starts from zero every time | phase 1 implemented |
| 2 | **Recipes**: composed generators that work on the first try | It rewrites the same hard parts (rock, water, clouds, perspective, crowds) in hundreds of lines and gets them wrong | phase 1 implemented |
| 3 | **Exactness by construction**: one command from art to verified deliverables | It is sloppy about seams, era limits, export formats and whole-pixel scaling | phase 1 implemented |
| 4 | **Proof**: a benchmark of skill against bare model | Without numbers, the other three are claims | phase 1 implemented (harness only; not yet run) |

## 1. The judge

**Phase 1 (this change).**

- `tools/judge.py` and `pixelate judge FRAME.png [--scale N] [--json] [--overlay OUT.png] [--log]` find the failures an art director kept catching in the `examples/moments` run. Each defect has a kind, a native-pixel box, a severity, why it reads wrong, and a fix recipe. The detectors:
  - `masonry`: straight seam grids with T-junctions, so rock reads as brickwork.
  - `repeat_units`: rows of same-size units at even spacing, such as stamped houses, ribs or drips.
  - `scallops`: an edge made of near-identical bumps, such as cloud or wave scallops.
  - `outline_loop`: a 1 px ring of one colour around the same colour it sits on, a mass drawn as a contour.
  - `murky`: most of the frame in one narrow value band, with a short value range.
- The overlay draws numbered boxes on the frame, so an agent sees what to fix and where.
- `pixelate critique` adds the detector findings and the overlay to the art director's prompt as a checklist.
- `pixelate critique ... --run` runs the art director itself through a separate model process. That is the `claude` CLI by default, or any command in `PIXELATE_CRITIC_CMD` that reads the prompt on stdin. It saves the critique as `critique-<frame>-rN.md` beside the frame, so the next round's `--prev` is one argument.
- `--log` appends each judge run, and each `--run` critique, to `.pixelate/judge-log.jsonl` (frame digest, scale, defects, critique path). This is the start of the corpus.

**Phase 2.**

- Calibrate the detector thresholds on the corpus (true and false positives, by style) and on the ten reference measurements.
- Promote calibrated detectors from report-only into the frame gate (`check.py`) as FAIL lines with per-style limits.
- Add `glyph`: real script characters used where the brief asks for invented glyphs, matched against `fonts/ark-pixel-12px.hex` and `pixfont`.
- Add `silhouette`: mask the brief's must-read objects, render them flat, and ask the critic whether each reads as itself or as the brief's named misread.
- Feed the before/after pairs from the corpus back into the critic prompt as worked examples.

**Done when:** on a held-out set of drafts, the judge and critic find at least 80% of the defects a human art director marks, with low false positives on the showcase finals.

## 2. Recipes

**Phase 1 (this change):** `tools/recipes.py`, listed by `pixelate tools TOPIC` for the matching topics.

- `Perspective`: a one- or two-point scaffold on the native grid. It gives the horizon, vanishing points, hand-stepped receding edges, and spacing for repeated units that shrink into depth (windows, posts, paving). Topics: buildings, stairs.
- `rock_face`: strata ledges of uneven thickness with lit lips, recesses under the lips, flake dashes and frayed edges. It avoids the masonry failure by construction. Topic: rock.
- `pouring_fall`: a waterfall that leaves its lip, curls forward, widens raggedly, throws detached streaks, and breaks into spray. It wraps `water.waterfall`. Topic: water.
- `cloud_bank`: three cloud masses of very different width with flat undersides, a lit top tier and a darker belly. It avoids scallop rows by construction. Topic: sky.
- `crowd_vignettes`: groups (cluster, ring, line) with at least three poses, faces toward each group's focus, and open ground between groups, so people never fall as confetti. It returns placements; the sprites are the caller's. Topics: crowds, figures, procession.

Every recipe uses the caller's palette slots, is deterministic for a seed, and is tested to produce output that `pixelate judge` does not flag for the failure it exists to avoid.

**Phase 2.**

- Add aurora curtains, hand-shaped light pools (with lamp slots that show only at night), a waterline treatment, iso quarter-turn rotation, and hull lofting. Each has a working version in `examples/moments/*/art`.
- Make `pixelate tools TOPIC` print a runnable 10-20 line snippet per recipe.
- Log which kit functions each run imports, to find dead tools and missing recipes.

**Done when:** the moments briefs redrawn with recipes need noticeably less art code and fewer critique rounds (measured by workstream 4).

## 3. Exactness by construction

**Phase 1 (implemented).** `pixelate render DIR` reads `DIR/render.json` (one entry per image: draw command, frame, style or era, scale, brief, palette, pre-light frame, actor) and for each image runs the command, gates it with that image's brief lines, era-checks era images, judges it (overlay plus corpus log) and, with `--critique`, runs the art director. It prints one line per image, writes `render-report.json` and exits 1 on a failed command or gate. `pixelate check --brief brief.md --image b` reads a `## Image B` section (its Hero, Planes and Gate override lines, plus the Technical section's overrides). The doctor now tells a missing Playwright pip package apart from a browser that won't launch. Example: `examples/moments/06-quarry-wakes/render.json`.

**Phase 2.** The rest of the list below: a sidecar `frame.json`, seam and export checks on every render, a skill version check, and starter templates.

- `pixelate render DIR`: run the art module, export at a whole scale, write a sidecar `frame.json` (style, scale, pre-light frame, post ops, actor mask), gate, judge, and optionally critique, in one call. It returns compact defects first, with details on request.
- Allow per-image sections in one brief (`## Image B` with its own Hero, Planes and overrides), plus `--image b`.
- Make loops, era legality and export formats verified by default on every render: seam checks, `era` checks for era briefs, and Aseprite JSON, atlas and gapless OGG validation.
- Fix the doctor's Playwright detection (Chromium present, pip package missing), and version the skill against the installed CLI and MCP server.
- Add starter templates per mode (perspective rebuild, era panel, iso diorama, vertical cover) that pass the gate empty.

## 4. Proof

**Phase 1 (implemented, not yet run).** `evals/` holds the ten prompts, `evals/run.py` (two arms, the same prompt, contract and timeout; a dry run unless `--go`) and `evals/score.py` (deliverables, judge defects, sample checks, optional blind grades, a per-arm summary). See `evals/README.md`. The pilot below is the next step, and it costs tokens.

- Add `evals/` with the ten `examples/moments` requests as the corpus.
- Run two arms with the same model, prompt and token cap, and no human coaching: a bare model with a Python sandbox, and the model with the skill installed.
- Record wall time, tokens, tool calls, whether it delivered, gate results, judge defects, and a blind art-director grade.
- Pilot: 3 prompts × 2 arms × 1 run. Re-run after each workstream lands and publish the paired results.
