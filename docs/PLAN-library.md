# Plan: a library of pixel-art programs

This is the concept design and the refactor plan for making pixelate-anything valuable. It builds on `docs/REVIEW-moat.md` (rounds two and three) and on the strategy discussion that followed. It replaces the order of work in `docs/PLAN-moat.md`; the judge, recipes, `pixelate render` and the evals harness built under that plan all keep a place here.

## 0. Summary

**The pitch:** *every piece is a program. Your agent finds the closest one, remixes it, renders and checks it, and the best results go back into the library.*

Today the skill hands a model about 22,000 words of instructions and a low-level kit, and the model writes 1,200–2,300 lines from a blank file. That cost 360k–500k tokens per piece in the showcase run, and every draft still needed an outside art director. Meanwhile the repo holds 17 finished, mostly reviewed programs (about 36,000 lines, more than the kit itself) that the workflow treats as reading material.

The plan turns those programs into the product:

1. **A library of pieces.** Each piece is a reviewed, tagged, runnable program with a manifest that says what it draws, which file to change for what, and which settings ("knobs") make variants for free.
2. **A remix loop.** `pixelate find` picks the closest piece, `pixelate remix` copies it, the agent edits it, and `pixelate render` and `pixelate deliver` check and package it. Weaker models stay on this narrow path; it should cut tokens to a fraction of drawing from scratch.
3. **An author path** for new pieces, which uses today's rigorous process. That rigor pays off because a library piece is reused many times.
4. **A flywheel.** Accepted work goes back into the library; parts that repeat become recipes; fixes the critic keeps asking for become checks; every run becomes a row of data.
5. **Proof**, measured before we claim anything.

What stays the same: the kit under `tools/`, the engine, the gate, the judge, the critic, review binding and the MCP server. What changes: what the skill asks the model to do first.

## 1. The concept

### 1.1 Why programs

| What you ship | What the user gets | Reproducible? | Variants? | Compounds? |
|---|---|---|---|---|
| A prompt | A different, usually weaker result each time | No | No | No |
| An image (image model, PixelLab) | One fixed picture or sprite | Yes, as a file | Only by regenerating | No |
| **A program (this plan)** | The piece itself, plus every variant its knobs allow | **Exactly** | **Free: season, palette, time, size, loop, camera** | **Yes: each one is the next request's starting point** |

The repo already proves the variant claim:
- Lantern Isle loops through four seasons from one program.
- San Francisco turns from day to dusk to night: one render, three palettes.
- The Canyon Cycle decodes sunset and night from one index array.
- Turntable Shipyard shows dawn and night a quarter-turn apart from one 3D description.

### 1.2 Who it is for

| User | Job | What the library gives them |
|---|---|---|
| Content creators | Lofi or ambient loops with music, covers, video backgrounds | Living scenes that loop seamlessly, with a soundtrack, as video or a live page |
| Indie and retro developers | Game screens, title screens, tilesets, console-accurate art | Pieces that hold console limits, export sprite sheets and tilemaps, and come in day and night variants |
| People with a place to rebuild | A photo of a city, a street, a landmark | Rebuild pieces in the photo's own camera, ready to relight |
| Agent users in general | "Make me pixel art of X" | A good starting point instead of a blank page |

**What it is not for:** single pretty stills (image models win on speed), or sprites and characters as standalone products (PixelLab and Retro Diffusion win, and they already plug into the same agents).

### 1.3 The four parts

```
          ┌──────────────── flywheel ─────────────────┐
          ▼                                           │
   LIBRARY (pieces) ──find──► REMIX ──edit──► RENDER + CHECK ──► DELIVER
          ▲                     ▲                    │
          │                     │                    └── runs.jsonl (data)
       harvest            ENGINE + KIT
   (pieces, recipes,   (tools/, engine/: drawing,
    checks, data)       checks, export, music)
```

### 1.4 What we stop doing

- Making the 10-step process the default for every request.
- Growing `SKILL.md` and the guides. More prose costs every run tokens, and models absorb it anyway.
- Adding low-level drawing functions agents don't call. In the showcase run they imported only `canvas`, `palette` and `colorlib`, yet half of them used the declarative music engine.
- Competing on sprites and characters.

## 2. The unit: a piece

### 2.1 Definition and status

A **piece** is a folder holding a program that renders one or more outputs (stills, loops, sprite sheets, music), plus a manifest. Every piece has an honest status:

| Status | Meaning | Required |
|---|---|---|
| `starter` | An empty piece for one mode; the fallback when nothing is close | Renders, passes the gate empty |
| `study` | Works, but not reviewed; a reference, not a recommended base | Renders in CI; manifest with tags and anatomy |
| `accepted` | Passed the gate and was approved by the user or the art director | The above, plus at least two knobs, golden frames, media, review notes |
| `reviewed` | A from an independent critic, bound to the exact bytes | The above, plus a `pixelate review record` manifest that matches |

`find` ranks `reviewed` above `accepted` above `study`. Remix bases should normally be `accepted` or better.

### 2.2 Layout

Program files stay where their runtime expects them, so no drawing code has to change in the migration.

```
library/<id>/
  piece.json      manifest (schema below)
  brief.md        what it should look like (short brief, or the authoring brief)
  art/            the program (Python runtimes); engine pieces keep scene.js and friends at the root
  sound/          music or SFX program, when the piece has sound
  out/            golden 1x frames used by the library test (small PNGs)
  media/          thumb.png (256 px), contact.png, preview.gif or preview.mp4 (short, with sound) when it moves
  history/        optional: draft frames at 1x, critiques and fixes (the critique trail)
```

A short preview clip with sound (`media/preview.mp4`, about 1–2 MB at most) may be committed so a piece shows both picture and audio. Full-length videos and full-size renders are not committed; they go on the project website later, and `piece.json` links to them.

### 2.3 Manifest: `piece.json`

Example for The Quarry Wakes, with real file names. It is a schema example (`references/piece.md` is the spec), not evidence that the piece has earned `accepted`:

```json
{
  "schema": 1,
  "id": "quarry-wakes",
  "title": "The Quarry Wakes",
  "status": "accepted",
  "summary": "A dredging machine breaks out of a flooded quarry; its leg slams the rim.",
  "request": "the original request, word for word",
  "mode": "scene",
  "tags": {
    "subject": ["quarry", "machine", "boss", "water", "rock", "dust"],
    "setting": ["industrial", "outdoor", "day"],
    "camera": "side",
    "style": "arcade",
    "era": "neogeo",
    "motion": "stills",
    "sound": "sting"
  },
  "canvas": {"w": 304, "h": 224, "scale": 4},
  "runtime": "script",
  "outputs": [
    {"name": "a", "kind": "image", "run": "python3 art/scene.py A", "frame": "out/06-a.png",
     "style": "arcade", "scale": 4, "brief": "brief.md", "pal": "out/palette.json"},
    {"name": "b", "kind": "image", "run": "python3 art/scene.py B", "frame": "out/06-b.png",
     "style": "arcade", "scale": 4, "brief": "brief.md", "pal": "out/palette.json"},
    {"name": "sound", "kind": "audio", "run": "python3 sound/sting.py", "file": "sound/06-sample.mp3"}
  ],
  "knobs": {
    "time": {"values": ["day", "dusk"], "default": "day", "edits": "art/pal.py"},
    "seed": {"type": "int", "default": 17, "edits": "art/scene.py"}
  },
  "anatomy": [
    {"file": "art/pal.py", "draws": "palette slots and ramps", "change_for": "colour, time of day"},
    {"file": "art/world.py", "draws": "terrain, rock strata, water", "change_for": "the setting"},
    {"file": "art/boss.py", "draws": "the machine", "change_for": "the hero creature or machine"},
    {"file": "art/soldier.py", "draws": "small figures", "change_for": "people, scale cues"},
    {"file": "art/fx_cells.py", "draws": "dust and spray", "change_for": "effects"},
    {"file": "art/scene.py", "draws": "composition of moments A and B", "change_for": "camera, framing, story beat"}
  ],
  "recipes": ["rock_face"],
  "kit": {"tested": "1.0.0"},
  "review": {"notes": "history/notes.md", "approved_by": "art-director", "record": null},
  "media": {"thumb": "media/thumb.png", "contact": "media/contact.png", "video": null},
  "lineage": {"remixed_from": null},
  "provenance": {"made": "2026-10-17", "by": "agent with art director"},
  "license": "MIT"
}
```

Field notes:
- **`outputs`** replaces `render.json`; it is the same format that `pixelate render` already uses (gate fields per image), plus sound and export entries. `render` keeps reading `render.json` while the migration runs.
- **`anatomy`** is what makes remix work for weaker models. It says which file draws what, and which file to change for which intent. It is written by hand and required from `accepted` up.
- **`knobs`** are the settings a program reads to make variants (section 2.4).
- **`tags`** use a fixed vocabulary per field, kept in `tools/library.py`, so search stays predictable.

### 2.4 Knobs

The contract is the same for every runtime:
- `pixelate render DIR --set time=dusk --set seed=4` writes the chosen values to a temporary JSON file and passes its path in the `PIXELATE_KNOBS` environment variable.
- The program calls `knobs()` from a small helper (`tools/piece.py`), which merges the defaults in `piece.json` with any values set.
- **Engine pieces:** `scene.json` already is the knob surface, so `--set` edits a copy of it.
- **Packs:** `--set` maps onto `pack.json` options.

Knobs are how "variants for free" becomes something anyone can use. They are also the cheapest possible remix: no code edits at all.

### 2.5 Runtimes

| Runtime | Used by | Render | Notes |
|---|---|---|---|
| `script` | the ten moments and new Python pieces | `run` commands per output (as in `render.json` today) | default for stills and offline animation |
| `pack` | San Francisco, Santorini, retro, indie, projections, Meadow Kit | `pixelate assets DIR` | sprites, sheets, iso dioramas, tilemaps |
| `engine` | Lantern Isle, music projects | `pixelate shot`, `video`, `gif`, `audio`, `build` | live scenes with generative music |

`tools/library.py` hides the differences: `render`, `test` and `deliver` call one function per runtime.

## 3. User flows

### 3.1 Remix (the default; any model)

```
pixelate find "an ancient temple wakes under a jungle at night"
  → 1. quarry-wakes      (scene, side, creature from stone, dust; 0.71)
    2. lanternmoss-mire  (scene, night, glow, jungle-like; 0.55)
    3. starter: scene-still
pixelate remix quarry-wakes work/temple --request "an ancient temple wakes under a jungle at night"
  → copies the piece, writes REMIX.md, renders the untouched copy once to prove it works here
(agent edits only what REMIX.md's plan names: pal.py for night, world.py for jungle and temple, boss.py for vines)
pixelate render work/temple --critique
  → gate, judge, distance from the base piece, one outside critique
pixelate deliver work/temple
  → final checks, exports, DELIVERY.md with facts written and fingerprinted by the script
```

`REMIX.md` holds the request, the base piece's summary, its anatomy table and knobs, and a short plan the agent fills in: *what stays* and *what changes* (subject, setting, camera, palette, composition, motion, sound). It ends with a checklist.

Rules for this path:
- **Render the copy before editing.** That separates "the base is broken here" from "my edit broke it".
- **Prefer knobs, then the files the anatomy names, then anything else.**
- **No brief, no block-in, no specialist reviewers.** One outside critique at the end.
- **A budget target of 150k tokens or less per accepted result**, measured in phase 4.
- `render` reports the **distance from the base** (a thumbnail difference plus a palette difference). If the request differs from the base but the result is too close, it warns "under-remixed".

### 3.2 Vary (no code)

`pixelate render library/lantern-isle --set season=winter`, `pixelate render work/temple --set time=dusk`. Use it for variant sets, seasonal versions and day and night pairs for games.

### 3.3 Author (new pieces; strongest models or no close match)

This is today's process, moved to `references/authoring.md`: intake, brief, block-in, gate, judge, critique, review record. The rigor is worth it here because the result becomes a library piece that others will remix. It ends with `pixelate library add` (section 3.4) at status `accepted` or `reviewed`.

**When to author instead of remix:** `find` returns nothing above the closeness threshold, the user asks for something new, or we are filling a gap on the coverage map (section 9).

### 3.4 Give back (harvest)

`pixelate library add DIR [--status accepted|reviewed]`:
1. Validates `piece.json` against the requirements for its status.
2. Renders every output from a clean copy twice; the results must match byte for byte.
3. Checks that every still passes the gate. For `reviewed`, it verifies the review record against the files' hashes.
4. Writes golden 1x frames, `media/thumb.png`, `contact.png` and `preview.gif`.
5. Copies the piece to `library/<id>/` and rebuilds `library/index.json`.

Others contribute by opening a PR with the folder. CI runs the same checks.

### 3.5 Game developer flow

Remix an asset-pack piece (Lanternmoss Mire, Meadow Kit), set the palette and time knobs, then `pixelate deliver` exports sprite sheets, Aseprite JSON, an atlas and tilemaps. This uses `tools/assets.py` as it stands today.

## 4. Commands and MCP

| Command | New, changed or kept | What it does |
|---|---|---|
| `pixelate find "REQUEST" [--mode M] [--json]` | new | Top 3 pieces with why they match and what differs; a starter when nothing is close |
| `pixelate remix PIECE DIR --request "..."` | new | Copy, write `REMIX.md`, render the untouched copy, record lineage |
| `pixelate render DIR [--set k=v] [--critique]` | changed | Reads `piece.json`; adds knobs and distance from the base |
| `pixelate deliver DIR` | new | Final gate, exports, `DELIVERY.md` facts written by the script (`--verify` checks them) |
| `pixelate library list / show ID / index / test [--quick] / add DIR` | new | Browse, rebuild the index, render-test every piece, contribute |
| `pixelate new KIND DIR` | kept as an alias | Same as `pixelate remix starter-KIND DIR` |
| `route`, `style`, `tools`, `check`, `judge`, `critique`, `review`, `era`, `assets`, `video`, `gif`, `audio`, `build` | kept | Unchanged; `route` also supplies the query tags for `find` |

**MCP:** add `find_pieces` (returns thumbnails as images, so the agent can look before choosing), `remix_piece`, `render_piece`, `deliver_piece` and `add_piece`, built on the same functions as the CLI.

**Search, kept simple:** deterministic, pure Python, no embeddings at first.
- The router's style, mode and era detection turns the request into tags.
- Score = tag overlap (mode required, then camera, style, motion and subject words) + keyword matching over title, summary and request + a bonus for status.
- A labelled set of requests and their expected pieces is kept as a regression test, like `route_regression_cases.py`.

## 5. The new `SKILL.md`

Target: **at most 1,500 words**, enforced by a test so it cannot creep back.

Outline:
1. **What this is**, in one paragraph: the library, the loop, and where the commands live.
2. **The loop:** find, remix, render, deliver, give back, with the five commands.
3. **Remix rules** (section 3.1), the default for every model.
4. **When to author** a new piece instead, with a link to `references/authoring.md`.
5. **Hard rules:**
   - original subjects only;
   - effects in code;
   - no borrowed characters, logos or UI;
6. **Modes:** a one-line pointer each to the starter pieces and the mode guides.

Path selection is by task, not by model name. If `find` returns a close piece, any model remixes; strong models may still author when they choose. This is more reliable than asking a model to identify itself, which is what huashu-art-motion does.

## 6. Repo refactor

### 6.1 Target layout

```
SKILL.md          the router (≤1,500 words)
README.md         pitch, three-command quickstart, gallery generated from the library
pixelate          the CLI
library/          THE PRODUCT: one folder per piece, index.json (generated), starters
tools/            the kit (same path and API): drawing, checks, recipes, plus library.py, remix.py, deliver.py, piece.py
engine/           JS runtime for live scenes and generative music
guides/           depth per mode, pointing at library pieces as worked examples
references/       authoring.md (today's 10 steps), piece.md (the manifest spec), art director rubric, contracts
evals/            the benchmark (held-out prompts live outside the repo)
tests/            unit tests, plus library tests (render and golden comparison)
docs/             plans, reviews, the source of the gallery page
```

`examples/` and `templates/` disappear into `library/`. `tools/` keeps its name: renaming it would break every doc, the MCP server and users' habits for no gain.

### 6.2 Migration map

| Today | Becomes | Runtime | Starting status |
|---|---|---|---|
| `examples/lantern-isle` | `library/lantern-isle` | engine | `accepted` (it is "the bar"; `reviewed` once a review record exists) |
| `examples/moments/01`–`10` | `library/monsoon-street`, `endless-ascent`, `canyon-cycle`, `tide-procession`, `four-machines`, `quarry-wakes`, `turntable-shipyard`, `market-day`, `lanternmoss-mire`, `tidewater-signal` | script (09 is a pack) | `accepted` (art-directed in the showcase run) |
| `examples/san-francisco`, `santorini` | `library/san-francisco`, `santorini` | pack | `study` until audited |
| `examples/retro` | `library/retro-screens` (three outputs) | pack | `study` |
| `examples/indie` | `library/rose-squall` | pack | `study` |
| `examples/meadow-kit` | `library/meadow-kit` | pack | `study` |
| `examples/projections` | `library/projections` | pack | `study` |
| `examples/gallery` | `docs/gallery/` (source notes, not a piece) | | |
| `templates/starter`, `music`, `assets` | `library/starter-scene-loop`, `starter-music`, `starter-assets` | engine, engine, pack | `starter` |
| new | `library/starter-scene-still`, `starter-era-nes`, `starter-rebuild-perspective` | script | `starter` |

That is 17 pieces and 6 starters. The run commands come from `examples/moments/README.md`, the `render.json` in 06, and each pack's `pack.json`. Use `git mv` so history survives, and update the paths in the docs (about 20 references) in the same PR.

### 6.3 What is demoted, and where it goes

| Today | After |
|---|---|
| The 10 steps in `SKILL.md` | `references/authoring.md`, used by the author path only |
| `render.json` | `piece.json` `outputs` (still read during the migration) |
| `route --brief` as the default first step | Author path only; `route` tagging feeds `find` |
| Examples as "reading" in `references/drawing.md` | Guides cite pieces by id ("strata rock: see `quarry-wakes`, `art/world.py`") |
| The bundled `evals/prompts` | Dry-run fixtures only (already the case since #29) |

## 7. Quality system

1. **Runnable, always.** A CI workflow (the repo has none today) runs:
   - the unit tests;
   - `pixelate library test --quick`, which renders every piece at 1x and compares it with its golden frames within a tolerance;
   - `SKILL.md` size and manifest-schema tests.

   A kit change that alters renders updates the golden frames in the same PR, so reviewers see the before and after thumbnails.
2. **Honest status.** Section 2.1. Self-assessed grades never set a status: huashu-art-motion measured makers' self-scores about 10 points above an independent reviewer's.
3. **A check blocks delivery only if it is calibrated.** A detector becomes a blocking gate only when it cleanly separates labelled good work from bad work, with margin. Accepted pieces supply the good examples; curated rejected drafts from `history/` supply the bad. Otherwise it stays a warning. This replaces calibrating on synthetic failures, which is how the judge was tuned.
4. **Under-remix and sameness checks.** Section 3.1. The library index also flags remixes that drift toward looking like each other.
5. **Facts written by the script.** `pixelate deliver` writes the facts block of `DELIVERY.md` (outputs, hashes, gate and judge results, critique grade, distance from the base) with a fingerprint. The agent adds notes but cannot change the facts. This extends the existing review binding.
6. **Versioned kit.** `pixelate --version`; each piece records the kit version it was tested with; `SKILL.md` metadata carries the same version.

## 8. Flywheel and data

**Run log:** `.pixelate/runs.jsonl`, local, never committed automatically. One record per render, critique or delivery:
- the request and the pieces `find` offered;
- the chosen base, the files changed and the diff size;
- tokens, when the agent reports them;
- the hashes of frames;
- gate, judge and critique results;
- whether it was accepted.

The judge log already does part of this.

**Critique trail:** a piece's `history/` keeps its 1x draft frames, each critique and what fixed it. These before-and-after pairs:
- teach the critic;
- calibrate the checks (section 7.3);
- are exactly the preference pairs a model can later be trained on.

**Recipes from repetition:** when the same part appears in two or more pieces, it becomes a recipe in `tools/recipes.py`, lists the pieces that use it, and gets a test. This is how `rock_face`, `pouring_fall` and `cloud_bank` came about.

**Training, later (phase 6):** once there are about 1,000 accepted programs with their trails, fine-tune a small open code model on them and compare it with a frontier model plus the library. That dataset and those weights are something a fork does not get.

## 9. Coverage map

Remix only helps when a close piece exists, so the library has to cover the requests people actually make. A first target is about 40 pieces:

| Area | Have | Gaps to author first |
|---|---|---|
| Scene loops with sound | island (Lantern Isle), storm at a window (Tidewater), rainy street (Monsoon), sky and clouds (Endless Ascent), canyon (Canyon Cycle), causeway (Tide Procession) | **cosy interior**, **night sky and space**, **underwater**, train or road journey, café or shop front, vertical cover |
| Rebuild | one-point street (Monsoon), aerial iso (San Francisco, Market Day), coastal town (Santorini) | **two-point street corner**, landmark facade, interior from a photo |
| Console screens | four consoles (Four Machines), NES platformer and Game Boy town (retro), Neo Geo boss (Quarry) | **RPG overworld**, shmup stage, battle screen, menu and dialogue UI |
| Assets | tileset and hero (Lanternmoss, Meadow Kit) | **item and icon set**, **UI kit**, character set |
| Isometric | shipyard (Turntable), projections, San Francisco | small diorama starter, interior room |
| Music only | engine projects inside pieces | lofi, chiptune overworld, ambient bed as standalone pieces |

**Measuring coverage:** keep a held-out list of about 50 realistic requests. For each, judge whether `find`'s top result is close enough to remix. Target 70% or more. The misses decide what to author next.

## 10. Distribution

- **The README's first screen is the gallery, generated from `library/index.json`:** media, the request, and the `pixelate remix <id>` command for each card. The same data builds a static page under `docs/` for GitHub Pages.
- **Every gallery card is honest:** it shows what the piece is, and the remix command reproduces it exactly, because it *is* the program. That fixes the "can I claim this prompt made this?" problem.
- **One signature piece made to be shared:** a personal, funny, original piece in the spirit of huashu-art-motion's platformer film, but with original characters and no borrowed IP.
- **The benchmark result goes in the README** once phase 4 runs, wins and losses both.

## 11. Proof

This updates the evals harness (`evals/`) to four arms, each on held-out requests that someone outside the project writes:

| Arm | What the agent gets |
|---|---|
| A, bare | The request |
| B, gallery card | The request plus the nearest card's image and prompt (no code): the "prompt collection" option |
| C, remix | The library and the remix loop (the default `SKILL.md`) |
| D, author | The full author path |

The skill arms include the library, minus any piece that answers a held-out request. Results are blind side-by-side ratings by at least three people, plus tokens and time.

**Decision rules, agreed in advance:**
- **C clearly beats A and B:** the library is the product. Keep building it.
- **B ties C:** the value is curation. Make the gallery with code the product and keep the skill minimal.
- **A ties B ties C:** for these tasks the skill adds nothing. Narrow to console screens and living scenes, or become a gallery.
- **D against C:** whether the author path earns its tokens.
- **Small-model probe:** C on a small model against A on a frontier model.

## 12. Phases

Each phase is one to three PRs and ends with something that can be checked.

| Phase | Scope | Done when |
|---|---|---|
| **0. Groundwork** | CI running the unit tests; `pixelate --version`; `.pixelate/runs.jsonl` logging from `render` (standalone `critique` still logs only to the judge corpus via `--log`; run records for `critique` and `deliver` move to phase 2, where `deliver` is built) | CI green on main; a render writes a run record that hashes the bytes each image was checked with |
| **1. Pieces and library** | `references/piece.md` (the spec); `tools/library.py` (schema, index, `list`, `show`, `find`, `test`); migrate all 17 examples and 3 templates with manifests, anatomy, golden frames and thumbnails; `render` reads `piece.json`; CI runs `library test --quick` | Every piece renders in CI; `find` puts the expected piece in its top 3 for at least 80% of 20 labelled requests |
| **2. Remix loop and new `SKILL.md`** | `pixelate remix`, `render --set`, distance from the base, `pixelate deliver` with script-written facts; MCP tools; `SKILL.md` rewritten (≤1,500 words) with `references/authoring.md`; guides cite pieces; three new starters (scene still, NES, rebuild in perspective) that pass the gate empty | A dry pilot by us: three remixes to new requests on a mid-tier model reach gate pass and critique B or better, with tokens recorded |
| **3. Give back and gallery** | `pixelate library add`; `history/` trails; curated rejects; gallery generated in the README and a Pages site; `CONTRIBUTING.md` with the piece checklist; recipes list their pieces | Adding a piece is one command and one PR; the gallery rebuilds from the index |
| **4. Proof** | Four-arm benchmark on held-out requests; blind ratings; small-model probe; results published | Numbers in the README and a decision taken by the rules in section 11 |
| **5. Growth and calibration** | Author about 20 pieces from the coverage gaps; calibrate detectors on library positives and curated rejects, promoting only those that separate cleanly; the signature piece | Coverage of 70% or more on held-out requests; remix success tracked per release |
| **6. Later** | Export the dataset; fine-tune a small open code model; consider a hosted library (open core) if adoption warrants it | Decided on evidence from phases 4 and 5 |

The benchmark comes after phase 2 on purpose: the paid runs should measure the product we intend to defend, not today's workflow.

## 13. Metrics

| Metric | Why | Target |
|---|---|---|
| Remix success rate | Share of pilot requests that reach gate pass and critique B or better within two rounds | Rising every release |
| Tokens and minutes per accepted result | The "faster and cheaper" half of the claim | Remix at a third of drawing from scratch, or less |
| Coverage | Share of held-out requests with a close piece | 70% or more |
| Library health | Share of pieces green in CI | 100% on main |
| Library growth | Accepted pieces per month, and how many come from outside contributors | Growing |
| Benchmark | Blind win rate of C against A and B | Published, whatever it says |

## 14. Decisions

Taken on 2026-10-18:

| # | Decision | Outcome |
|---|---|---|
| D1 | License | **MIT** for everything, including the library. |
| D2 | External sprites (characters from the user or a sprite generator) | **Not pursued.** Pieces stay drawn in code; no import path is planned. |
| D3 | Media | **Thumbnails, preview GIFs and short preview clips with sound in git** (each about 1–2 MB at most, so a piece shows both picture and audio); full-length videos go on the project website later. Keep the repo under 50 MB. |
| D4 | Naming | **As proposed:** library, piece, `find`, `remix`, `deliver`. |
| D5 | Who writes the held-out requests and rates the benchmark | **Deferred** to phase 4. |

## 15. Risks

| Risk | Mitigation |
|---|---|
| Remixes look like their base (sameness) | Distance-from-base warning; `REMIX.md` must name what changes; the author path when nothing is close; coverage growth |
| Kit changes quietly break pieces | CI renders every piece against golden frames; versioned kit |
| Search misses | Starters as the fallback; labelled search tests; the coverage map |
| Weak models break a working program | Render the untouched copy first; knobs before code; anatomy names the files to edit; small diffs; revert to the base |
| Contributions lower the bar | Statuses with requirements; review binding for `reviewed`; CI checks |
| Borrowed IP slips in through contributions | The original-subjects rule; source and license fields; a review checklist |
| Repo bloat | Media policy (D3): short clips only; full videos on the website |
| Process creeps back | `SKILL.md` word limit enforced by a test; new process goes into the author path only |
| The benchmark says no | The decision rules in section 11; even then the library has value as a gallery with source code |
