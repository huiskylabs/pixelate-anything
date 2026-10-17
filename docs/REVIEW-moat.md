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
