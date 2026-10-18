# Piece manifest (schema 1)

Read this when authoring or migrating a `library/<id>/piece.json`. A catalog entry is a *declaration*, not a certificate that its commands were run. `pixelate find REQUEST` and `pixelate library list|show ID|index` (also `python3 tools/library.py`) validate declarations without executing a piece. Only `pixelate render DIR` and `pixelate library test` run a piece's commands. Render, gate, golden comparison and independent review verification are separate steps. In particular, a technical gate pass is not approval.

## Layout and identity

A piece lives at `library/<id>/piece.json`. `id` is a lowercase ASCII slug (`[a-z0-9]+(-[a-z0-9]+)*`) equal to its directory name; IDs are unique. JSON objects have unique keys. The catalog rejects symbolic links anywhere in a piece, including unreferenced files. All manifest file references are POSIX paths relative to the piece root, with no empty, `.` or `..` component, leading slash, backslash or NUL. File references must exist as regular files, except the image gate inputs a render writes (below). The library root holds only piece directories, the generated `index.json`, and an optional `README.md` or `.DS_Store`. The index is generated, sorted by id, and is not proof of quality. Keep full videos outside git.

## Required fields

| Field | Contract |
|---|---|
| `schema`, `id`, `title`, `summary`, `request` | Integer `1`, slug, nonempty human-readable strings. `request` is the original request, not a search-optimized paraphrase. |
| `status`, `mode`, `runtime` | Status: `starter`, `study`, `accepted`, `reviewed`. Mode: `scene`, `rebuild`, `era`, `assets`, `music`. Runtime: `script`, `pack`, `engine`. |
| `tags` | `subject`, `setting`: nonempty arrays of distinct lowercase ASCII slug terms (hyphen permitted). `camera`: `side`, `2:1 iso`, `3/4 top-down`, `one-point perspective`, `two-point perspective`, `oblique`, `military`, `none`. `style`: one of the router styles (`lofi`, `pastel-cell`, `native-glow`, `hd-overworld`, `arcade`, `tactics`, `sticker-iso`, `illustrated`, `neon-noir`, `cosy-lightmap`, `contre-jour`) or `none`. `era`: `nes`, `gameboy`, `pico-8`, `genesis`, `gba`, `neogeo`, `snes`, `none`. `motion`: `stills`, `loop`, `sprite-sheet`, `none`. `sound`: `none`, `music`, `sting`, `sfx`. No other tag fields. Use `none` when a field does not apply. |
| `canvas` | `w`, `h`, `scale`: positive integers (not booleans). |
| `outputs` | Nonempty array of distinctly named typed output records below. `run` is a nonempty shell command that `pixelate render` and `pixelate library test` run; index, list, show and find never run it. |
| `anatomy` | Array of `{file, draws, change_for}`: an existing source file, and nonempty plain-language descriptions of what it draws and what to edit for a change. At least one entry for every status. |
| `knobs` | Object keyed by slug. Each value is either `{values: [distinct JSON scalars], default: one of values, edits: source path}` or `{type: "int", default: integer, edits: source path}`. `edits` names an existing source file. Future `--set` and `PIXELATE_KNOBS` support will consume this contract; catalog does not apply knobs. |
| `provenance` | `{made: "YYYY-MM-DD", by: nonempty string}`. This identifies who made the piece; it does not attest review. |
| `license` | `MIT` for library contributions. |

Optional: `recipes` (distinct `tools/recipes.py` function names such as `rock_face`), `kit` (`{tested: nonempty version string}`), `media` (`thumb`, `contact`, `video`, `gif`: optional file paths), `lineage` (`{remixed_from: slug or null}`), `review` (see below). The manifest is limited to 128 KiB.

### Typed outputs

Every output has a unique slug `name`, `kind`, and `run`. The command is metadata, not permission to execute contributed code; unlike `render.json`, a library output always has `run`, because every piece must render in CI.

Image (`kind: "image"`) takes the `tools/render.py` `render.json` image fields, so a `render.json` entry plus `kind` is a valid image output:

| Field | Contract |
|---|---|
| `frame` | Required. The frame the run command writes and the gate checks, at `scale`; must exist. |
| `golden` | The golden 1x frame for `library test`: exactly `out/golden/<name>.png`, never the same file as `frame`; must exist when given. `library test` fails an image without it. |
| `size` | `{w, h}`: positive integers, the 1x size of this image. Defaults to the piece `canvas` `w` and `h`. |
| `style`, `era` | At least one is required for the gate. `style`: a router style (not `none`); `era`: an era above (not `none`). |
| `scene` | A scene variant of `style` (`pixelate style S` lists them); needs `style`. |
| `scale` | Positive integer; the gate defaults to 1. The frame must be `size` times `scale`; `canvas.scale` is not used. |
| `brief` | A source file; must exist when given. Required on the image a `reviewed` record binds. |
| `pal`, `pre`, `actor`, `intent` | Gate inputs the run command may write. Safe relative paths inside the piece; they need not exist before a render, but any component that exists must not be a link, and an existing target must be a regular file. |
| `used` | Comma-separated post ops (`light,shaft`, `rain:hair`). |
| `judge_ignore` | Comma-separated judge defect kinds (`masonry,repeat_units`). |

As in `render.py`, an empty string means an optional string field is unset; no other fields are allowed. Audio: `kind: "audio"`, `file` (audio file). Export: `kind: "export"`, `file` (exported artifact). Gate fields do not belong on audio or export entries. Audio and export files must exist at validation time.

Example (the frame, brief, sources and media must exist inside `library/quarry-wakes/`; `out/palette.json` and `out/06-a-actor.png` are written by the run command; approval must be evidenced, not inferred):

```json
{
  "schema": 1, "id": "quarry-wakes", "title": "The Quarry Wakes",
  "summary": "A machine rises from a flooded quarry.", "request": "a machine rises from a flooded quarry",
  "status": "accepted", "mode": "scene", "runtime": "script",
  "tags": {"subject": ["machine", "quarry"], "setting": ["industrial"], "camera": "side",
           "style": "arcade", "era": "neogeo", "motion": "stills", "sound": "sting"},
  "canvas": {"w": 304, "h": 224, "scale": 4},
  "outputs": [
    {"name": "a", "kind": "image", "run": "python3 art/scene.py A", "frame": "out/06-a.png",
     "style": "arcade", "scale": 4, "brief": "brief.md", "pal": "out/palette.json", "actor": "out/06-a-actor.png"},
    {"name": "sting", "kind": "audio", "run": "python3 sound/sting.py", "file": "sound/sting.mp3"}
  ],
  "anatomy": [{"file": "art/scene.py", "draws": "quarry and machine", "change_for": "subject and composition"}],
  "knobs": {"time": {"values": ["day", "dusk"], "default": "day", "edits": "art/scene.py"},
            "seed": {"type": "int", "default": 17, "edits": "art/scene.py"}},
  "provenance": {"made": "2026-10-18", "by": "agent with art director"},
  "media": {"thumb": "media/thumb.png", "contact": "media/contact.png"},
  "review": {"notes": "history/approval.md", "approved_by": "art-director", "record": null},
  "license": "MIT"
}
```

## Render and test

`pixelate render DIR` reads `DIR/piece.json` (validated as above, so the folder name must equal `id`) or a legacy `DIR/render.json`; a folder with both is an error. Image outputs get the `render.json` behavior: run, gate, era check, judge, optional critique, `render-report.json` and a run record. Audio and export outputs are run and hashed, and their records carry `kind` and `file`. They are never gated: an audio file does not pass the image gate. `--image NAME` selects any output by name. After a piece command runs, a frame, file or existing gate input (`brief`, `pal`, `pre`, `actor`, `intent`) that is reached through a link or is not a regular file fails that output, and nothing is hashed, gated or judged for it. The recorded hash is of the bytes read without following links. The gate, era check and judge then reopen the paths, so `render` does not guard against a process the command leaves running. Legacy `render.json` images keep their old path handling.

Piece commands run in the piece folder through the shell, with the kit's `tools/` first on `PYTHONPATH` and the kit root first on `PATH`. A program imports kit modules and calls `pixelate assets .`, `pixelate shot . 0` or `pixelate audio . music.wav` without a hard-coded kit path. Legacy `render.json` commands run with the caller's environment, as before.

`pixelate library test [ID...] [--quick] [--timeout S]` tests the named pieces, or every piece:

1. Validate the manifest and copy the piece to a temporary folder. The source piece is never written.
2. Group the outputs that are not skipped by identical `run` command, in order of first appearance. Outputs meant to come from one command must declare the same command string.
3. For each group, delete the group's declared `frame` and `file` paths from the copy, then run its command once. Neither a stale committed file nor another command's side effect can pass. A command that runs longer than `--timeout` seconds (default 300) is killed with its process group. Generated gate inputs (`pal`, `pre`, `actor`, `intent`) are not deleted, since they may be checked-in files; they are used as the copy holds them after the group runs.
4. Right after a group runs, check each of its outputs. A path reached through a link, or one that is not a regular file (a folder or a pipe), fails, and nothing is read from it. Every hash, comparison and gate uses bytes opened without following a link.
5. For an image, the frame must exist and be `size` × `scale` pixels. The frame is reduced to 1x with nearest-neighbor sampling, and its RGBA pixels must equal `golden` exactly. A difference reports the pixel count, the bounding box `[x0, y0, x1, y1]` and the largest channel delta. To accept a change, update the golden in the same commit. Separately, the frame runs the same technical gate as `pixelate render` (`pixelate check` with the image's `style`, `era`, `scene`, `scale`, `pal`, `pre`, `actor`, `used`, `intent` and brief section, plus `pixelate era` when it names an era). The gate runs on a private snapshot of the frame and gate inputs; the brief is taken from the source piece. The report keeps `golden`, `gate` and `era` apart and sets `gate_ok`. For a `starter`, `accepted` or `reviewed` piece, an image passes only if the golden matches and the gate passes. A `study` only has to render (plan section 2.1). Its gate failure is reported (`gate_ok: false`, the failing lines, and a `diagnostic`) and does not fail the image. A gate that errors instead of finishing, such as a crash on a malformed gate input or a failed era check run, fails the image whatever the status. A link or non-regular gate input also fails it.
6. For audio and export: the file must exist and be nonempty; its SHA-256 is reported. `--quick` skips audio and export outputs and reports each as `skipped`.

The command prints JSON: `{ok, gate_ok, quick, pieces: [{id, ok, gate_ok, outputs: [{name, kind, path, status, ...}]}]}`, where `status` is `passed`, `failed` or `skipped`. A piece's `gate_ok` is true only when every one of its images ran and passed the gate, so `ok: true` with `gate_ok: false` means a study rendered and matched its goldens but is not gate-legal. It exits 0 when no output failed, 1 when one did, and 2 for a malformed or unknown ID, an invalid manifest, or when no piece is selected (for example, an empty library). A golden match is a regression test, and a gate pass is a technical check. Neither is a quality judgment or approval.

`library test` is for trusted, checked-in pieces. The shell is not a sandbox: a run command can read and write anything the user can, before or after the checks. The link checks keep a trusted piece's mistakes from being verified as its own output; they do not contain hostile code. Do not run it on contributed or pull-request code until the project adopts a trust and sandbox policy.

The root `.gitignore` ignores `out/` folders. Under `library/<id>/out/` it ignores everything except `golden/`, so `git add` picks up golden frames. A scaled frame needs `git add -f` unless git already tracks it.

## Status evidence

| Status | Required static evidence | Still requires outside catalog validation |
|---|---|---|
| `starter` | A tagged, anatomized piece with at least one output and provenance. | Render and gate on the *empty starter* before use. It is a fallback, not a recommended finished base. |
| `study` | Same static declaration. | CI render; no approval implied. |
| `accepted` | At least two knobs; at least one image output; `media.thumb` and `media.contact` files; `review.notes` file and `review.approved_by` (`user` or `art-director`). | Verify approval is genuine, render determinism and gate result. Review notes are not a technical gate result. |
| `reviewed` | All accepted evidence plus `review.record` file (a visual-review sidecar) and matching A-grade artifact-bound review via `review_status.piece_status`. | Recheck exact-byte binding after any file change; review alone does not grant licensing or user approval. |

`review` is `{notes: path or null, approved_by: "user" | "art-director" | null, record: path or null}`. For `starter`/`study` it may be absent; if supplied, all references are checked, but it cannot elevate status. `record` is a sidecar produced by `pixelate review record`, named `<frame>.visual-review.json` beside an image output's `frame`, with the critique report saved inside the piece (for example `history/lead.md`) before recording. The record keeps the absolute paths it was made at, so a moved piece is checked by `review_status.piece_status`: the recorded frame must end in the output's `frame` path under a directory with the piece's id, the recorded brief must be the output's `brief` under that same directory, and the report must have been inside it. Only those paths are reanchored to the piece's current folder; no link is followed. A report recorded outside the piece, a renamed piece, a different path relation, a link, noncanonical record bytes, changed brief/frame/report bytes, or a B/C grade fails `reviewed` validation. Plain `pixelate review status` keeps binding absolute paths. Accepted review notes must be nonempty. For `accepted`, review notes/approval are declarations to audit, never inferred from a passing gate. Do not promote migrated work to accepted without evidence.

## Search contract

Search requires a mode match and at least one request word that matches a `tags.subject` term; explicit camera, style, era or motion mismatches are not interchangeable. Words are lowercased and singularized, and common function and filler words (`its`, `out`, `up`, `old`, `make`, `pixel`) never count. Setting tags (`day`, `outdoor`) and words of the title, summary and request add score to a piece that already matches a subject, but cannot make a match on their own, so choose subject tags for what the piece can be remixed into. A status bonus only orders relevant results; it cannot turn an unrelated popular or reviewed piece into a match. `find` returns at most three matched pieces plus `starter` fallback(s) for the requested mode. When nothing is close it abstains from recommending a finished piece and returns the starter plan, or an author-new-piece plan if no matching starter exists. The 20 labelled synthetic cases and the realistic false-match cases in `tests/test_library.py` test this contract; they are not evidence of real-corpus accuracy.
