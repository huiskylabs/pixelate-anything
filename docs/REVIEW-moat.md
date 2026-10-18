# Review: what makes pixelate-anything better than using a model directly?

This is round two, written after the judge, recipes, `pixelate render` and the evals harness were merged (#26, #27). It uses [REA](https://github.com/morluto/rea) as the reference again. It is a critique, not a victory lap: most of the value below is still a claim, because no benchmark has been run.

## 1. What REA's value actually is

REA's README never compares itself with a bare model. It doesn't need to, because its value is obvious at the first call:

1. **It gives the model eyes it does not have.** A model cannot decompile a binary, read an APK or parse a pcap from a prompt. REA wraps Ghidra, Hopper, IDA, JADX, tshark, Binwalk and more, and returns pseudocode, symbols and references. Nothing in a prompt replaces that.
2. **Every answer carries its evidence.** It returns "the evidence and limitations behind each conclusion" and lists unknowns, so the agent and the user can check it.
3. **Its showcase is verified by an oracle.** The DX-Ball reconstruction "passes 3,205 original-x86 cases and reproduces all 63 compiled function bytes." No one argues with that number.
4. **Setup is one line, and the skill only routes.** `npx rea-agents setup` adds the MCP server and installs matching workflow instructions. The heavy work lives in the tools, not in prose.

The lesson is not "write more instructions". **REA is worth using because the tools return facts the model cannot produce, and its showcase is checked by something other than taste.**

## 2. Who we are actually competing with

The first review compared the skill with a bare LLM writing numpy. That is too narrow. Someone who wants pixel art has three options:

| Option | What they get in about a minute | Where it fails |
|---|---|---|
| **An image model** ("pixel art of a quarry at dusk") | A striking picture | It is not pixel art. Pixel sizes are mixed, the image is off-grid, it has thousands of colours, anti-aliased edges and no source. It can't loop, can't hold an NES palette, and can't be edited one pixel at a time or exported as a sprite sheet. |
| **An LLM writing code, no skill** | A real pixel grid, slowly | It rewrites rock, water and perspective from scratch and gets them wrong. It can't see its own pixel-level defects. It is sloppy about scale, palette, seams and export. |
| **The LLM with pixelate-anything** | A real pixel grid, gated, judged, exported | It costs 360k to 500k tokens and 7 to 24 minutes per piece (from the showcase run). Quality is unproven against either alternative. |

Image models are the real competitor for "make me something pretty". We cannot win on prettiness per second, and we should stop implying we can.

## 3. Our honest value proposition

We win where the output must be **correct as an asset**, not just look right. That is our REA-style "facts the model can't produce", and like REA's byte-exact claim, it is checkable by an oracle:

| Claim | How it is checked | Image model | Bare LLM | Skill |
|---|---|---|---|---|
| A true pixel grid: one whole scale, square pixels | `check`: grid and scale detection | fails | usually | by construction |
| The palette is exact and limited (a slot map, so you can swap palettes) | `check --pal`, the colour count | fails | sometimes | by construction |
| Era legal (NES master palette, 4-colour blocks, Game Boy 4 shades, tile counts) | `pixelate era` (check and force) | fails | rarely | checked and forced |
| Loops are seamless (period divides the loop) | `check` loop-seam line | fails | rarely | checked |
| Game-ready export (Aseprite JSON, atlas, gapless audio) | `assets.py` validation | none | hand-rolled | built in |
| Editable and re-renderable source (day and night, seasons, a new camera) | the art is code | none | yes | yes, structured |
| Sound that matches the scene, gated | `musiccheck` | none | ad hoc | built in |

**One-sentence value:** *pixelate-anything turns a prompt or a photo into pixel art that is technically correct as a game or loop asset (on-grid, palette-exact, era-legal, seamless, exportable), and it is editable as code, which neither an image model nor a bare model delivers reliably.*

Taste (composition, light, "it looks great") is the second claim, carried by the judge, critic and recipes. It is real but much harder to prove. Lead with the first claim.

## 4. Critique of what we just built

### The judge (workstream 1): a lint, not judgment yet
- It has five heuristic detectors (masonry, repeated units, scallops, outline loops, murky). It catches the synthetic failures, but recall on even-scallop clouds is about 50%. On the 20 accepted finals it is mostly quiet, which shows it is not noisy; it does not show it is useful.
- What art directors actually rejected in the showcase run was composition, focal clarity, scale cues and light logic. The judge sees none of that. It locates texture defects, and only some of them.
- **It is not tied to grades yet.** Nobody has checked whether frames with fewer judge defects get better critic grades. Until that holds, "the judge improves art" is unproven.
- **Next:** log judge and critique pairs (the corpus hooks exist) and measure agreement. Add detectors only for defects the critics keep naming. Remove any detector that never predicts a fix.

### Recipes (workstream 2): the right idea, too few, not yet used
- There are five recipes (rock face, pouring fall, cloud bank, perspective, crowd vignettes). They were built from what painters struggled with, which is correct.
- No agent run has used them yet, so their adoption and win rate are unknown.
- Copyability is not the point. Anyone can read `recipes.py`, but a bare model in a fresh session still won't have it, the same way anyone can read Ghidra's source.
- **Next:** the README's own scenes (snow, aurora, lamplight on water, iso blocks) should come from recipes. Every recipe needs a gallery strip and a test that passes the gate and the judge as it ships.

### `pixelate render` (workstream 3): convenience, not yet "by construction"
- It chains commands; it does not prevent errors. Seam checks, export validation and a sidecar `frame.json` are still in phase 2.
- **The strongest version of our claim is here.** Make `render` refuse to emit a still that is off-grid or off-palette, and refuse to emit a loop with a seam. That is the "verified by default" contract, and it is what an image model can never offer.

### The evals (workstream 4): built, not run, and biased as built
- **Goodhart risk.** `score.py` scores both arms with `pixelate judge`, but the skill arm is told to run the judge and fix what it finds. The skill arm is graded by its own training signal. Judge defects must be a secondary metric, never the headline.
- **The wrong competitor is missing.** There is no image-model arm. The most persuasive result would be the oracle table in section 3, run on image-model output, bare-model output and skill output.
- **The headline should be blind pairwise preference.** Show the two arms' stills side by side, unlabeled and order-randomized, to human raters if possible, otherwise to a different model family. Report the win rate with the sample size.
- **Cost must be reported alongside quality.** REA ranks agent tokens first. Our 360k to 500k tokens per piece is a real cost. Report tokens and minutes per accepted piece, and set a target (for example, under 150k).

## 5. What to change, in order

1. **Lead with correctness.** Rewrite the README's first screen around the oracle table and a side-by-side: an image-model "pixel art" crop at 8×, with mixed pixel sizes and thousands of colours, next to ours at 8×, with a whole scale and 24 slots. This is our DX-Ball moment, and it costs no tokens.
2. **Fix the eval design** before spending tokens:
   - add an `image` arm (any image API, prompt only), scored with the correctness checks;
   - make blind pairwise preference the headline;
   - demote judge defects to a diagnostic;
   - report tokens per accepted piece.
3. **Make `render` refuse wrong output:** grid, palette, seam and export checks on by default. Add a `--loose` flag for drafts.
4. **A cheap-path mode.** Many requests don't need the 10-step loop. Route short requests to one template plus `render`, with no brief-stage review, and measure the token cost.
5. **Close the judge-to-grade loop.** Use the logged corpus to keep only the detectors that predict critic fixes.
6. **Recipe coverage for the showcase scenes,** each with a gallery strip.

## 6. Bottom line

People should use pixelate-anything when they need pixel art that **works as an asset**: on the grid, palette-exact, era-legal, seamless and exportable, with sound, and editable as code. No image model or bare model gives that reliably, and it can be checked by machine. That is our REA-style core.

"It looks better" is our second claim, and right now it rests on taste and a critic. Prove it with blind pairwise runs, not with our own judge.

---

# Round three: mode by mode, on main at d713b00

The question for each mode: **where does the kit make the final pixels better than a model writing them from scratch?** Rules of thumb, docs and gates help the process. Quality comes from code that has already been proven to draw the hard part well, and from feedback that names a specific place in the image. In the showcase run, painters imported only `canvas`, `palette` and `colorlib`, and wrote 1,200 to 2,300 lines of art code by hand (handoff section 1). Until more of the final image comes from kit code, the skill mostly changes the process, not the pixels.

**What changed since round two:** `pixelate reference` (#29) writes an editable record of a photo (value bands, a 12×12 lightness grid, edge directions, manual camera and landmark marks, all tied to the photo's hash). The evals now refuse bundled prompts for live runs, copy a filtered kit, require a spend ceiling, and anonymize what the critic sees. Both changes are sound and honest about their limits.

## Scoreboard

| Mode | What a bare model gets wrong | What the kit already does better | Biggest gap | Advantage today |
|---|---|---|---|---|
| **era** | Hard hardware limits: NES 4-colour attribute blocks, 3-colour sprites, sprites per scanline, unique tile counts, Game Boy 4 shades | `era.check` and `enforce`, `check_sprites`, scanline counts, `check_tiles`, era gate lines | No `pixelate new era` starter; no hardware export (CHR tiles, nametable, palette bytes) | **Strong and provable** |
| **assets** | Frame-to-frame consistency, pivots, sheet packing, tags, silhouettes that read | `.px` format, Aseprite-style JSON, atlas, contact sheet, silhouette sheet, lone-pixel and colour checks, `topx` | No checks that the animation reads (drift across frames, volume kept, arcs) and no directional sets (4 or 8 facings) | **Strong for the technical part, weak for motion** |
| **scene** | Loops that seam, palette cycling, light done in palette steps, muddy values, repeated stamps | Slot canvas, light, sky, water, veg and fx modules, recipes, judge, loop-seam check, Lantern Isle as the bar | Too few recipes (aurora, light pools, foliage masses); the starter is the JS engine while painters write Python | **Real for loops, thin for stills** |
| **rebuild** | Keeping the photo's camera; simplifying into readable masses; picking the few details that make the place itself | `iso.py` (five orthographic views), `Perspective` recipe, guide, now `pixelate reference` | **No comparison of the render against the reference**; no perspective starter | **Weak; the most to gain** |
| **music** | Seamless loops, genre feel, mixing levels | Lofi, chiptune and ambient engine, `musiccheck`, music critic prompt | Missing instruments (bells, FM, strings), no fixed melody, no one-shot events, no SFX (handoff 2.4, all still open) | **Moderate** |

## Per mode: what would move quality most

### era: lead with it, and finish it
This is the one mode where a machine can prove the skill beats both a bare model and an image model. A bare model draws an "NES-style" screen with 40 colours and 9-colour sprites; `era check` fails it with numbers. Two additions turn "checked" into "usable":
1. **`pixelate new era --era nes`**: a starter canvas that passes `era check` empty, with the palette, attribute grid and sprite layer already wired.
2. **Hardware export**: write CHR tiles, a nametable, attribute and palette bytes (and the Game Boy equivalents), plus a tiny ROM or emulator-loadable test. "It runs on the console" is our version of REA's byte-exact showcase.

### assets: add motion checks
The export side is already better than anything a model writes in one session. The quality gap is motion. Cheap, located checks:
- **Volume drift:** the sprite's pixel area per frame should stay within a band, apart from squash and stretch.
- **Pivot jitter:** the anchor moves only when the brief says so.
- **Palette consistency:** every frame uses the same slots.
- **Facings:** the same character's 4 or 8 directions keep height and colour mass.

Each comes back as a frame index and a box, like the judge's findings.

### scene: more recipes, in the medium agents actually use
- Painters write Python stills; `pixelate new scene` gives a JS engine. Add a Python still starter (`new still`) that wires the canvas, palette, export at scale, `render.json` and the brief, and passes the gate empty.
- Recipes named in the handoff but still missing: **aurora curtains, light pools and spills in palette steps, foliage masses, waterline and submerged areas.** These are where the coordinator's fixes went in the showcase run.
- A recipe must take the scene's palette slots, geometry and seed, and the judge's repeated-units detector should catch the same recipe stamped twice with the same parameters.

### rebuild: compare the render with the reference
`pixelate reference` already computes a 12×12 lightness grid on the photo. Computing the same grid on the block-in or the render gives a **located fidelity report** at no cost:
- where the value layout differs from the photo (cells far apart in rank);
- whether the marked horizon and vanishing points line up with the render's receding edges;
- whether each marked landmark box holds a distinct mass in the render.

That is "review the render against the source", not the artist's account of it, and it answers "did the perspective problem actually get fixed?" from round to round. It should stay a diagnostic (a stylised rebuild is allowed to move values), but it turns the rebuild guide's "put the render next to the reference" into a measurement. Then add **`pixelate new rebuild-perspective`**, which builds the `Perspective` scaffold from the marked horizon and vanishing points.

### music: close the four known gaps
Fixed melody per phase, a one-shot event layer (bells, thunder), a few FM and plucked instruments, and a small SFX set for asset packs. Half the showcase samples needed custom numpy synths, so these gaps are measured, not guessed.

## Cross-cutting

1. **Measure how much of each image comes from the kit.** Log the kit functions each run imports and calls (handoff 2.3). If agents still write everything by hand, recipes and starters are not reaching them, and a better `SKILL.md` will not fix that.
2. **Starters per mode are the cheapest quality lever.** Only `scene` (JS), `music` and `assets` exist. A starter that passes the gate empty removes hundreds of lines of from-scratch code, which is where the masonry rock and stamped rows came from.
3. **One ordered report.** `render` should return the gate failures, then judge findings, then (for rebuilds) reference differences, then the lead's top fixes, each with a place. Specialists only with a stated question.
4. **Bug fixed in this round:** `pixelate new --help` (or `new` with missing arguments) crashed with an `IndexError`; it now prints the usage and the template kinds.

## Recommended order

1. **Era:** a starter, then hardware export. It is our provable advantage and the smallest amount of work.
2. **Rebuild:** `pixelate reference --compare RENDER` plus a perspective starter built from the marks.
3. **Scene:** a Python still starter plus four recipes (aurora, light pools, foliage masses, waterline).
4. **Assets:** motion checks with frame-and-box findings.
5. **Music:** melody, events, instruments, SFX.
6. **Throughout:** log kit usage per run. Run the held-out benchmark only once 1 to 3 have landed, so the paid runs measure the kit we want to defend.
