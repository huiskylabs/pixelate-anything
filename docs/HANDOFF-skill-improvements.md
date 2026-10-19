# Handoff: making pixelate-anything beat a bare model

**Goal.** Give a user a long, good prompt. With the pixelate-anything skill installed, the result must be better than the same model with the same prompt and no skill, and it must arrive faster. If it isn't, users have no reason to install the skill.

**Where this comes from.** The `examples/moments/` run (PR #21): ten long showcase prompts, each rendered as two stills and a 5-second sample by parallel Claude agents. The agents read `SKILL.md` and used the CLI and kit. A coordinating agent wrote detailed prompts and acted as art director, and that is the problem: most of the final quality came from the coordinator's hand-written fixes, not from the skill. This document turns every place the coordinator had to step in into a change to the skill.

**Status of the claim.** Unproven. The run cannot be shown as "the prompt triggered our skill" (see section 1). Section 5 describes the benchmark that would prove it once there is budget.

---

## 1. What actually happened in the run (the evidence)

| | |
|---|---|
| Agents | 10 painters in parallel, one per prompt, plus one coordinator/art director |
| Cost per painter | about 360k–500k tokens, 7–24 min of agent time per run (several runs each), 23–63 tool calls |
| Art code per piece | 1,200–2,300 lines, mostly written from scratch |
| Kit usage | sparse. Typical imports were `canvas`, `palette`, `colorlib`. 02 and 09 used almost nothing beyond `Canvas` and `artlib.Grid`. The most-called kit functions were `fx.rain_cells`, `shapes.cloud_mask`, `sdf.Cyl`, `era.check_sprites`. |
| Gate | every first draft passed most lines; every piece still needed art-director fixes |
| Fix rounds | 1–3 coordinator rounds per piece; 03 (canyon) needed three |
| Sound | 5 of 10 used the music engine (01–04, 10); 5 needed custom numpy synths (05–09) |
| Interruptions | all 10 agents died mid-run on an account spend limit and were resumed from transcripts |

How the run deviated from "install the skill and paste the prompt":

- The skill was not installed (`pixelate setup` was never run). Agents read `SKILL.md` from the checkout and ran `./pixelate` directly.
- Each agent received a ~1,500-word prompt from the coordinator. It contained the request, the chosen moments, canvas and scale, a craft-rule digest, the exact gate commands and a sound plan. Much of that is knowledge the skill should supply itself.
- The skill's user-confirmation steps (5, 9, 10) were skipped, and so was `pixelate critique`; no painter ran it.
- The coordinator chose the two Pexels reference photos.

---

## 2. Critique: where the skill fell short, with what was observed

### 2.1 The gate passes weak drafts (the biggest gap)

The gate proved that drafts were legal, not that they were good. These failures passed the gate and were caught only by the coordinator looking at the images:

| Failure | Where it appeared | Why the gate missed it | Detector to add |
|---|---|---|---|
| Natural material drawn as masonry: canyon walls, cliffs and quarry benches with long straight grid seams | 03 (twice), 05, 06 | nothing measures seam geometry inside rock | First supply a mask for each named rock/cliff/stone object from the art code; the current `check` path does not derive those masks from brief nouns. Then, inside each mask, measure long straight horizontal/vertical dark seams and T-junction density. Calibrate thresholds on good and bad rock before failing. |
| Rows of near-identical units: pebble clouds, scalloped cloud bands, identical house "cards", identical ship ribs, evenly spaced drips | 02, 10, 07, 06, 08 (dormers) | the `repeat` line only warns | Make `repeat` able to fail, with per-style calibration. Add a spacing-regularity test: the coefficient of variation of gaps between same-slot clusters along a line. |
| Outline loops instead of filled masses (clouds drawn as 1 px light loops) | 04 | not measured | Detect closed 1 px rings of slot A that separate the same slot B on both sides. `drawing.md` already forbids this; the gate should enforce it. |
| Silhouette misreads: glider wing as a tube, hull as a canoe, toad as a bowl, waterfalls as pillars | 05, 07, 09, 03 | numbers can't judge a misread | Vision check (section 2.2): render the object's mask as a flat black shape and ask the critic model whether it reads as X or as the nearest misread named in the brief's "Silhouette keys" line. |
| Real script characters used as "invented glyphs" (one meant "kill") | 01 | not checked | Match 5–12 px glyph clusters against `fonts/ark-pixel-12px.hex` and the 5x7 font, and warn on near matches unless the brief declares real text. |
| Murky frames: most of the frame in one value band | 01, 04 | the budget passes as long as the bounds hold | Add a value-group spread check: at thumbnail size, demand 3–4 separated value groups, with no single band over X% outside calm areas the brief declares. |
| Light that doesn't read (lantern pool invisible at 1x) | 09 | focus lines don't cover secondary lights | A per-emitter check from the brief's light list: each declared emitter changes its neighbourhood by at least a minimum L step. |

### 2.2 The art-director step is the real value, and it is optional

What made the outputs good was the coordinator's notes. They followed one format: a place, a concrete change, and what to keep. Examples: "the walls read as brick masonry; redraw as strata ledges with frayed lips, flake dashes, lit top edge"; "the glider wing reads as a rolled tube; draw a delta with spar, battens, darker underside". Today:

- `pixelate critique` only prints a prompt. It relies on the agent spawning a second agent, and no agent did.
- When the critique doesn't run, nothing tells anyone. The steps say "graded A", but nothing enforces it.

**Change:**

- Design an opt-in `pixelate critique --run` (and MCP equivalent) around the existing lead and specialist prompts. A fresh model must receive the brief and actual images; the caller must choose an available model and authorise its cost. Define model access, image transfer, independent-review separation and failure handling before making this a default. A model call alone does not reproduce the coordinator's briefs, references and decisions.
- Keep #22's default of three graded lead rounds per full brief and still stage, with at most two optional specialist consults per artifact from #23. Stop and ask after a third non-A grade unless the user explicitly allows more; an automated runner must share that budget rather than start another loop.
- Save the lead critique, stage, grade and a hash of the exact brief and frame next to the artifact (`out/critique-a-r1.md` plus metadata), so `--prev` names the prior lead result and stale critiques cannot count for a new render. Seed the critic with the failure catalogue in 2.1 as a checklist.
- Add a separate release/workflow status check for a **final** frame: verify a matching A critique exists. Keep `pixelate check` focused on pixel legality; it also checks block-ins and drafts, which may have no critique yet.

### 2.3 The kit is too thin, and what exists is hard to find

Painters rebuilt the same primitives by hand, sometimes badly enough to need fixes. Kit candidates, ranked by how many pieces needed them:

| Need | Pieces | Suggested home |
|---|---|---|
| One- and two-point perspective scaffold: horizon, vanishing points, receding-edge stepping, shrinking repeats at native size | 01 (wrote its own `geom.py`); any street rebuild | new `tools/persp.py`; `guides/rebuild.md` already describes it but provides no code |
| Waterfall that pours: lip curl, ragged widening sides, splash crown at breaks, spray base, cycling-ramp slots | 03 (three rounds) | `tools/water.py` |
| Cloud masses with long flat undersides and lobes of varied size, so no scallops | 02, 03, 04, 10 | `shapes.cloud_mass` exists but went unused; this is a discovery problem (see below) |
| Aurora curtains: S-curve hem, varied ray heights, fold crease, dither fade | 02 | `tools/sky.py` |
| Rock as strata: ledges, frayed lips, flakes, talus | 03, 05, 06 | `shapes.ledges`, `shapes.fray` and `texture.flakes` exist; add a `rock_face()` recipe that combines them |
| Hand-shaped light pools and spills in palette steps, and a "lamp slot" pattern that is invisible by day and lit by night | 01, 07, 09 | `tools/light.py` |
| Waterline and submerged treatment (deep slots under a wobbling surface) | 06 | `tools/water.py` |
| Iso world rotation in quarter turns for one 3D description | 07 | `tools/iso.py` |
| Crowd vignettes: groups with poses and a story, not scatter | 08 | `tools/compose.py` (it has `check_density` but no vignette builder) |
| Invented sign glyphs with a consistent pen | 01 | `tools/glyphs` (`references/assets/glyphs.py` is read-only) |
| Ship hull lofting: keel, ribs following a sheer line, strakes | 07 | an `sdf` recipe |

**Discovery fix:** `pixelate tools TOPIC` returns signatures. It should also return a 10–20 line runnable starting snippet per topic: the recipe, not just the parts. The router already knows topics, so attach recipes to them.

**Measure it:** log which kit functions each run imports, so the team can see coverage and dead tools.

### 2.4 Music: the engine can't voice most requests

- **Missing instruments:** bells, thunder and weather one-shots, FM (brass stabs, bass), strings, brass, reeds and accordion. Half the samples needed custom numpy synths.
- **No fixed melody:** the engine plays random phrases only, so 10 had to synthesise its own leitmotif lead. Add a `melody: [[step, midi, len], ...]` or `motif` field per phase.
- **No one-shot layer:** add an `events: [[time, 'bell', params], ...]` layer, so the bell on the tram or the clock is engine-native.
- **No game SFX** (09 needed coin, jump, splash and jingle). Add a small `sfx` module with handheld-style channels; it fits the asset-pack mode.
- **Gate false-fails:** `musiccheck` fails tempo on drumless ambient excerpts. Skip or soften the tempo check when beat strength is low, and add a `--use excerpt` mode for short samples.

### 2.5 Gate and process friction (time lost to workarounds)

- **One Hero line per brief:** two-moment jobs invented `brief-b.md` files. Support per-image sections (`## Image B` with its own Hero, Planes and overrides) and `--image b`.
- **Post-op overrides only help lint:** contre-jour bans `Post.lightmap`, yet a door spill is that style's natural use, and the gate can't take an override for a post op. Either allow per-brief op overrides in the gate, or document `Post.light` as the substitute in the style card.
- **Sticker-iso focus bounds** fight dense full-bleed crowds (08 needed `focus_rival <= 3.2`). Add a `--scene crowd` variant like `cosy-lightmap --scene exterior`.
- **Screen-light gating** needs `--pre` and `--used` assembled by hand. Have art modules write a sidecar `frame.json` (style, scale, pre path, ops used, actor mask, named object masks) that `check` reads automatically; require an explicit mask before object-specific detectors run.
- **The 10 steps assume a human at three checkpoints.** Add an explicitly requested autonomous render path to `SKILL.md` for pre-authorised runs. Keep the brief, block-in, gates and art director. Preserve the brief, still and animation confirmations for ordinary users; skip a wait only when the user has delegated that decision in advance.
- **Intake and route are hints only.** Briefs were well formed, but each agent spent many tokens reading guides first. Put the per-mode essentials into the generated brief skeleton, so reading the guides becomes optional.

### 2.6 Speed and cost (the "faster" half of the claim)

Most of each painter's budget went to reading guides, writing scaffolding from scratch and rediscovering conventions.

- **Starter templates per mode:** `pixelate new rebuild-perspective`, `new era-panel --era nes`, `new iso-diorama`, `new cover-vertical`, `new asset-pack` (exists). Each should pre-wire the canvas, palette file, export at scale, sidecar for the gate, block-in script and critique hook, and pass the gate empty, as `new scene` already does.
- **One render-and-gate command** per template (`pixelate render DIR`): run the art, export, gate and write the sidecar. This removes ten manual commands per round.
- **Cache-friendly docs:** a single `SKILL.md` digest per mode (about 1–2k tokens) instead of following links into five files.

### 2.7 Robustness

- The doctor reported Playwright missing although Chromium was installed at `/opt/pw-browsers`; only the pip package was missing. `pixelate doctor` should say "pip install playwright (Chromium already present)" and honour `PLAYWRIGHT_BROWSERS_PATH`.
- A long run should checkpoint by itself. Agents can die mid-task (spend limits); templates that write `progress.md` and keep every render step idempotent make resumes cheap.
- The root `.gitignore` ignores `out/`, so finished showcase art must be force-added. Consider an `examples/**/final/` convention.

---

## 3. Prioritised roadmap

| # | Change | Files | Why first |
|---|---|---|---|
| P0 | Design an opt-in model-backed lead run over the existing prompts, with explicit model/cost choice, three-round budget, artifact-bound critique records and a separate final-release status check | `tools/critique.py`, `tools/mcp_server.py`, release workflow | Make the independent critique usable without confusing drafts with final delivery |
| P0 | Add a `frame.json` sidecar carrying gate inputs and named object masks; then calibrate masonry, spacing, outline-loop and real-glyph detectors against good and bad examples | art modules, `tools/check.py`, `tools/craftcheck.py` | Object-specific failures need trustworthy regions before thresholds can fail a frame |
| P0 | Explicitly opt-in autonomous render path, preserving normal user approvals | `SKILL.md`, `references/delivery.md` | Benchmarks can pre-authorise decisions without silently bypassing user checkpoints |
| P1 | Per-image brief sections that can consume sidecar metadata | `tools/route.py`, `tools/check.py` | Removes the workaround brief files |
| P1 | Recipes in `pixelate tools TOPIC`, plus `persp.py`, waterfall, rock face, aurora, light pools | `tools/route.py` (catalogue), `tools/persp.py`, `tools/water.py`, `tools/sky.py`, `tools/light.py` | Less code from scratch, so faster and more consistent |
| P1 | Music engine: motif field, one-shot events, bell and FM voices; `musiccheck --use excerpt` | `engine/audio.js`, `tools/musiccheck.py`, `guides/music.md` | Half the samples bypassed the engine |
| P2 | Mode templates and `pixelate render DIR` | `templates/`, `tools/cli.py` | Speed |
| P2 | Style variants (`sticker-iso --scene crowd`) and a post-op override in the gate | `tools/styles.py`, `tools/check.py` | Fewer overrides |
| P2 | Vision silhouette check against the brief's misread line | `tools/critique.py` | Catches the hero misreads |
| P2 | Doctor fix, progress checkpoints, `final/` convention | `tools/cli.py`, templates | Robustness |

---

## 4. Reusable assets from this run

- `examples/moments/*/brief.md`: ten long, specific briefs. These are the benchmark prompts.
- The art-director notes and fix histories are a ready-made seed for the critic checklist and for detector test cases. They are summarised in 2.1; the pieces in `examples/moments` show before-and-after effects in their code history on PR #21.
- `examples/moments/*/art/*.py` contains working implementations to mine for kit tools:
  - 01 `geom.py`: perspective
  - 03 `canyon.py`: falls and strata
  - 07 `yard.py`: iso rotation and hull
  - 08 `mfig.py`: iso people
  - 09 `render_map.py`: lamp slots that only show at night
- The sound scripts (`05/sound/theme.py` strings and FM, `06/sound/sting.py` FM, `08/sound/march.py` brass, `04/sound/bell.py` bell, `09/sound/sfx_reel.py` SFX) are prototypes for engine voices.

---

## 5. How to prove the claim later (the benchmark)

1. **Prompts and inputs:** freeze the ten briefs' request sections as prompts. Give both arms the same reference photos, requested outputs (two stills and a 5-second sample where asked), machine and time budget. Neither arm receives the coordinator's extra instructions or fixes.
2. **Arms:**
   - (a) the same model with the prompt and a Python sandbox (Pillow and numpy);
   - (b) that model with the skill and kit installed via `pixelate setup`.
   - No human coaching in either arm; use the same token cap and record any extra tool or model-review calls. This compares the installed bundle, not the skill text alone.
3. **Measure:** wall time, tokens and tool calls to the first deliverable **and** the first acceptable deliverable under a predeclared quality threshold; record failures and gate pass rates for both arms.
4. **Judge:** blind pairwise preference and a quality rubric neutral to the kit's house style. The `references/art-director.md` scores can be a secondary diagnostic, but its Lantern Isle bar should not decide a comparison against a bare model.
5. **Win condition:** arm (b) reaches a better result at the same or lower time and tokens; report the quality/cost trade-off per prompt rather than hiding failures in an average.
6. **Cheap pilot:** 3 prompts × 2 arms × 1 run for feasibility, then repeat enough runs before claiming a win.

Run it before and after the P0 items; the difference is the measured value of the work in section 3.

---

## 6. Lessons from REA (morluto/rea)

[REA](https://github.com/morluto/rea) is a reverse-engineering skill plus MCP server whose skill is hard to replace with a long prompt. These notes come from reading its README, `AGENTS.md`, its main and maintainer skills (`.agents/skills/`), `docs/tool-design.md`, and its evaluation harness. REA was not benchmarked against a bare model; the points below are design differences, not measured results.

| REA practice | What we do now | What to change |
|---|---|---|
| **Tools do what the model can't.** REA wraps Ghidra, Hopper, IDA, JADX and tshark; a model cannot decompile with a prompt. | Most of the kit is drawing primitives a model can rewrite in numpy, and painters did exactly that. | Invest in what a model can't do alone: quality judgment (critic and detectors), defect location, and proven starting assets (templates and recipes). |
| **Evidence, not verdicts.** Each result carries source locations, coverage, limitations and explicit unknowns ("missing coverage is unknown, not absence"). | The gate prints PASS/FAIL with numbers. | Gate and critic return located defects: region, failure type, fix recipe (for example "masonry seams at x 40–120, y 30–90: redraw as strata"). |
| **The skill is a router.** "Route the target first": target type → first tool. Then work summary-first and follow up only on a specific open question. | A 10-step process that sends agents into five guides; about 400k tokens per piece. | Make `SKILL.md` a routing table: request type → template → first command → done condition. Guides become optional depth. |
| **Workflow tools for recurring outcomes** (for example `trace_application_feature`), added only once repeated use shows the need. | About ten manual commands per draw/gate/critique round. | `pixelate render DIR`: draw, export, gate and critique in one call, returning compact defects first and details on request. |
| **Agent tokens first.** `AGENTS.md` ranks agent tokens above analysis time and CPU, and counts the whole task (schemas, retries, extra calls). | Never measured. | Track the tokens, calls and time a standard task costs, and report the change with any skill change. |
| **Claims need real runs.** `tests/evaluation/model-evals/` (including known-answer evals) and `experiments/analysis-efficiency/agent-trial.py` run real agent tasks with an isolated install, pinned revisions and digests, an oracle independent of the implementation, and failed attempts kept. | No evaluation harness. | Add `evals/`: the ten moment briefs as the corpus, skill arm against bare-model arm, recording tokens, time, gate results and blind art-director grades (section 5). |
| **Maintainer skills.** `rea-tool-design`, `rea-analysis-optimization` and `rea-ci-tests-audit` encode how to improve REA itself: start from the user's question, find the earliest unnecessary work, prove correctness with an oracle, measure before and after. | None. | Add `pixelate-tool-design` (when a recurring hand-built object becomes a kit tool, and how to test it) and `pixelate-eval` (how to run and read the benchmark). |
| **Setup and recovery are first class.** `setup --dry-run` with approval and backups, a client-specific `doctor`, a reconnect workflow, and a versioned skill (`version: "42"`) that warns when it is newer than the installed server. | `doctor` misreported Playwright as missing when only the pip package was; the skill has no version. | A client-aware `doctor`, dry-run setup, and a skill version checked against the installed CLI/MCP. |
| **One owner per interpretation.** Facts are normalized once at the producer; CLI and MCP share one implementation and a generated contract catalog. | Style rules, the gate and the critique prompt each restate style facts. | Make the style card the single source; generate the gate limits and the critic's checklist from it. |

**Order to adopt:** evidence-style gate output (with the P0 detectors) → routing `SKILL.md` → `pixelate render` with the built-in critic → `evals/` harness → token accounting → maintainer skills → setup hardening.

**Takeaway.** REA's value is verified facts the model can't produce, proven with measured agent runs. For pixel art, the verified facts we can offer are quality judgment, defect location and proven starting assets; that is where pixelate-anything should invest.
