# Piece manifest (schema 1)

Read this when authoring or migrating a `library/<id>/piece.json`. A catalog entry is a *declaration*, not a certificate that its commands were run. `python3 tools/library.py index|list|show ID|find REQUEST` validates declarations without executing a piece. Render, gate, golden comparison and independent review verification are separate later steps. In particular, a technical gate pass is not approval.

## Layout and identity

A piece lives at `library/<id>/piece.json`. `id` is a lowercase ASCII slug (`[a-z0-9]+(-[a-z0-9]+)*`) equal to its directory name; IDs are unique. JSON objects have unique keys. The catalog rejects symbolic links anywhere in a piece, including unreferenced files. All manifest file references are POSIX paths relative to the piece root, with no empty, `.` or `..` component, leading slash, backslash or NUL. File references must exist as regular files; directory references must exist as directories. The index is generated, sorted by id, and is not proof of quality. Keep full videos outside git.

## Required fields

| Field | Contract |
|---|---|
| `schema`, `id`, `title`, `summary`, `request` | Integer `1`, slug, nonempty human-readable strings. `request` is the original request, not a search-optimized paraphrase. |
| `status`, `mode`, `runtime` | Status: `starter`, `study`, `accepted`, `reviewed`. Mode: `scene`, `rebuild`, `era`, `assets`, `music`. Runtime: `script`, `pack`, `engine`. |
| `tags` | `subject`, `setting`: nonempty arrays of distinct lowercase ASCII slug terms (hyphen permitted). `camera`: `side`, `2:1 iso`, `3/4 top-down`, `one-point perspective`, `two-point perspective`, `oblique`, `military`, `none`. `style`: one of the router styles (`lofi`, `pastel-cell`, `native-glow`, `hd-overworld`, `arcade`, `tactics`, `sticker-iso`, `illustrated`, `neon-noir`, `cosy-lightmap`, `contre-jour`) or `none`. `era`: `nes`, `gameboy`, `pico-8`, `genesis`, `gba`, `neogeo`, `snes`, `none`. `motion`: `stills`, `loop`, `sprite-sheet`, `none`. `sound`: `none`, `music`, `sting`, `sfx`. No other tag fields. Use `none` when a field does not apply. |
| `canvas` | `w`, `h`, `scale`: positive integers (not booleans). |
| `outputs` | Nonempty array of distinctly named typed output records below. `run` is a nonempty command string for a future trusted renderer; indexing/search never executes or shells it. |
| `anatomy` | Array of `{file, draws, change_for}`: an existing source file, and nonempty plain-language descriptions of what it draws and what to edit for a change. At least one entry for every status. |
| `knobs` | Object keyed by slug. Each value is either `{values: [distinct JSON scalars], default: one of values, edits: source path}` or `{type: "int", default: integer, edits: source path}`. `edits` names an existing source file. Future `--set` and `PIXELATE_KNOBS` support will consume this contract; catalog does not apply knobs. |
| `provenance` | `{made: "YYYY-MM-DD", by: nonempty string}`. This identifies who made the piece; it does not attest review. |
| `license` | `MIT` for library contributions. |

Optional: `recipes` (distinct slug array), `kit` (`{tested: nonempty version string}`), `media` (`thumb`, `contact`, `video`, `gif`: optional file paths), `lineage` (`{remixed_from: slug or null}`), `review` (see below). The manifest is limited to 128 KiB.

### Typed outputs

Every output has a unique slug `name`, `kind`, and `run`. Image: `kind: "image"`, `frame` (declared golden 1x PNG), `style` (router style), `scale` (positive integer), `brief` (file), optional `pal` (file). Audio: `kind: "audio"`, `file` (audio file). Export: `kind: "export"`, `file` (exported artifact). Image-only gate fields do not belong on audio or export entries. An image output's frame, audio file and export file must exist at validation time. The command is metadata, not permission to execute contributed code.

Example (paths must exist inside `library/quarry-wakes/`; approval must be evidenced, not inferred):

```json
{
  "schema": 1, "id": "quarry-wakes", "title": "The Quarry Wakes",
  "summary": "A machine rises from a flooded quarry.", "request": "a machine rises from a flooded quarry",
  "status": "accepted", "mode": "scene", "runtime": "script",
  "tags": {"subject": ["machine", "quarry"], "setting": ["industrial"], "camera": "side",
           "style": "arcade", "era": "neogeo", "motion": "stills", "sound": "sting"},
  "canvas": {"w": 304, "h": 224, "scale": 4},
  "outputs": [
    {"name": "scene", "kind": "image", "run": "python3 art/scene.py",
     "frame": "out/scene.png", "style": "arcade", "scale": 4, "brief": "brief.md"},
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

## Status evidence

| Status | Required static evidence | Still requires outside catalog validation |
|---|---|---|
| `starter` | A tagged, anatomized piece with at least one output and provenance. | Render and gate on the *empty starter* before use. It is a fallback, not a recommended finished base. |
| `study` | Same static declaration. | CI render; no approval implied. |
| `accepted` | At least two knobs; at least one image output with a golden frame; `media.thumb` and `media.contact` files; `review.notes` file and `review.approved_by` (`user` or `art-director`). | Verify approval is genuine, render determinism and gate result. Review notes are not a technical gate result. |
| `reviewed` | All accepted evidence plus `review.record` file (a visual-review sidecar) and matching A-grade artifact-bound review via `tools/review_status.py`. | Recheck exact-byte binding after any file change; review alone does not grant licensing or user approval. Relocation invalidates absolute-path review bindings: re-record against the final library paths rather than carrying an old record forward. |

`review` is `{notes: path or null, approved_by: "user" | "art-director" | null, record: path or null}`. For `starter`/`study` it may be absent; if supplied, all references are checked, but it cannot elevate status. `record` is a sidecar produced by `pixelate review record`, beside an image output's `frame`; its brief and frame must match that image output, and its report must live inside the piece. Accepted review notes must be nonempty. A grade B/C, missing file, changed bytes or mismatched path fails `reviewed` validation. For `accepted`, review notes/approval are declarations to audit, never inferred from a passing gate. Do not promote migrated work to accepted without evidence.

## Search contract

Search requires a mode match and a subject/setting or descriptive-text word match; explicit camera, style, era or motion mismatches are not interchangeable. Subject/setting terms and request/title/summary text supply relevance. A status bonus only orders relevant results; it cannot turn an unrelated popular or reviewed piece into a match. `find` returns at most three matched pieces plus `starter` fallback(s) for the requested mode. When nothing is close it abstains from recommending a finished piece and returns the starter plan, or an author-new-piece plan if no matching starter exists. The 20 labelled synthetic cases in `tests/test_library.py` test this contract; they are not evidence of real-corpus accuracy.
