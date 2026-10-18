# Remix a library piece

Read this before `pixelate remix`. It covers the copy, its baseline and the distance `pixelate render` reports from the base. `render --set` renders a variant of a script, engine or pack piece that declares knobs ([piece.md](piece.md#knobs)); `pixelate deliver` packages a finished piece ([delivery.md](delivery.md#deliver)), and `pixelate new` is still a plain copy, not an alias of remix.

```
pixelate find "an ancient temple wakes under a jungle at night"
pixelate remix quarry-wakes work/temple --request "an ancient temple wakes under a jungle at night"
```

`PIECE` is a library piece id (`--library L` picks another library folder; default the kit's). `DIR`'s name becomes the new piece id, so it must be a lowercase slug. DIR must not exist, or must be an empty folder that is not a link, and it cannot be inside the library. `find` and the lookup never run piece code. Remix does: the baseline runs the base piece's commands through the shell, without a sandbox. Remix only trusted, checked-in pieces.

## What remix does

1. Validates the base manifest (a link anywhere in the piece is refused) and copies the piece into a temporary folder beside DIR. The copy keeps sources, the brief, media, history and `out/golden/`. It leaves out generated frames and files, the rest of `out/`, `.pixelate/`, `dist/`, `shots/`, `__pycache__/`, `render-report.json` and every `*.visual-review.json` review sidecar.
2. Writes the copy's `piece.json`: `id` from DIR, your `request`, `lineage.remixed_from` set to the base, status `study` (a `starter` stays `starter`), and provenance naming the remix and quoting the base's provenance. `review` is dropped. Approval and review records were bound to the base's bytes, so they are no evidence for the copy, and a remix of an `accepted` or `reviewed` piece starts unreviewed. The `license` declaration is copied as declared. It is not verified, and it does not establish rights to a photo or other source the base was made from.
3. Renders the unedited copy once in a second, clean temporary copy with `pixelate library test --quick` rules (`references/piece.md`). Each output's declared frame or file is deleted before its command runs, so a stale output cannot pass. Every image must match its 1x golden. A `starter` image must also pass the technical gate. A `study` image whose gate fails but which rendered and matched its golden is reported as a diagnostic (`gate_ok: false`): it is not gate-legal and not approved. Quick mode skips audio and exports when the piece has images; they are listed as untested.
4. If nothing failed and at least one output passed, writes `.pixelate/remix-baseline.json` and `REMIX.md` into the copy and moves it to DIR. Otherwise DIR is left as it was, and the report goes to stderr.

`.pixelate/remix-baseline.json` (local; git ignores `.pixelate/`) holds the request, the base id, status and review, the SHA-256 of the base's `piece.json` (`base.piece_sha256`), the SHA-256 of every copied file as tested (`files`, `files_sha256`), the full test report with each rendered output's hash, and the untested outputs. Remix prints the baseline file's own SHA-256. If the copy's files change while the baseline renders, the remix fails.

`REMIX.md` holds the request, the base's summary, status and declared license, the baseline results, the anatomy table, the knobs, a plan table (subject, setting, camera, palette, composition, motion, sound: what stays and what changes) and a checklist. Fill in the plan before editing. Prefer knob files, then the files the anatomy names.

## Distance from the base

`pixelate render DIR` on a piece whose `lineage.remixed_from` names a base measures each image output against the base output of the same name. It reports two numbers:

- **Pixels**: how many 1x pixels differ from the base's checked-in 1x golden (`out/golden/<name>.png`). The frame is reduced to 1x with nearest-neighbor sampling, as `library test` does. Fully transparent pixels count as equal whatever their RGB.
- **Colours**: the share of distinct colours that the frame and the golden do not have in common (1 minus shared over all).

Render measures the frame bytes it read once and hashed, the same bytes the gate, judge and critique checked. It never reads the frame again from DIR, so a process that rewrites the frame afterwards does not change the result. This holds with `PIXELATE_NO_LOG=1` too, when no snapshot is kept. With `--no-run`, the distance is of the frame already in DIR. With `--set`, the variant is measured against the base's golden, which shows the base's default knobs.

The base is looked up only in the kit's checked-in `library/`. It is validated statically like `pixelate find` (a link anywhere in it is refused), its `piece.json` and goldens are read once before any command runs, and none of its code runs. No other folder is searched.

The kit piece counts as the base only when it is the piece the remix was copied from, as far as `.pixelate/remix-baseline.json` records it: the SHA-256 of its `piece.json` must equal `base.piece_sha256`, and each golden must equal the hash of the copied golden under `files`. So a remix made with `pixelate remix --library L` is measured only if L's base manifest and the compared goldens match the kit candidate; other source files are not compared. When L holds another manifest with the same id, the distance is unavailable, even if the two goldens happen to be the same. When the kit piece or one of its goldens changes after the remix, that distance is unavailable too. Your edits to the copy, including its own `out/golden/`, are intended and are not checked against the baseline.

This is a consistency check, not proof of origin. The baseline is a local, unsigned file that anyone can edit, so a match says only that the kit piece agrees with what the file records.

Each image record in `render-report.json` and in `.pixelate/runs.jsonl` carries `distance`: `base` (id, library, output, status, the `piece.json` SHA-256 it matched, golden path and its SHA-256), `pixels` (`differ`, `total`, `share`), `palette` (`colours`, `base_colours`, `shared`, `share`), `request_differs`, `under_remixed`, `warning`, `reason`, `thresholds` and `note`. The run record also names the `base` it looked up, with its `piece_sha256` or the `error`. The line render prints for the image ends with `distance from BASE/OUTPUT: ...`. A number that could not be measured is `null` with a `reason`, never 0:

- the piece has no `.pixelate/remix-baseline.json` (for example, `lineage.remixed_from` was written by hand), or the baseline is unreadable, invalid JSON, not a schema 1 remix baseline, of another piece or base, or older than this check (it records no `base.piece_sha256`; remix the base again to measure). A link at the baseline is never followed, and render refuses a piece with a link in it anyway;
- the kit piece does not match the baseline: its `piece.json` hash differs (another library's piece with the same id, or the kit piece changed since), or a golden's hash differs from the copied golden's;
- the base is not in the kit library, is invalid, has no image output of that name, or that output has no golden;
- the command failed, or the frame was missing, unsafe, unreadable or not `size` × `scale`;
- the 1x size differs from the base golden: colours are still compared, pixels are not, and there is no under-remix verdict.

A piece that is not a remix records `distance` with `base: null` and the reason, and prints nothing.

### The under-remixed warning

When the remix's `request` differs from the base's (ignoring case and spacing) and fewer than 2% of 1x pixels and fewer than 5% of colours differ, the record sets `under_remixed: true` and the line ends with `WARNING under-remixed: ...`. It usually means the copy still draws the base: a changed request with an unchanged or nearly unchanged frame.

The thresholds are an uncalibrated heuristic, chosen to flag near-copies only. No labelled set of good and bad remixes backs them. The warning is not a quality grade or approval, and it is not a gate: it never changes the exit status, which stays the technical gate's. A large distance does not mean the request was met, and no warning does not make the remix good. When you see the warning, look at the frame and at the plan in `REMIX.md`, and check that what the request asks for, such as the new subject, setting or palette, is actually drawn. If it is not, edit the files the anatomy names and render again. If the request really asks for a small change, such as one prop added to the same scene, say so in the plan and keep the frame.

Exit status: 0 when DIR was created; 1 when the baseline failed or DIR could not be written (nothing is created); 2 for an unknown or invalid piece, an empty request or an unusable DIR.

## MCP tools

Clients without a shell get the loop as four tools (`tools/mcp_server.py`), built on the same commands. There is no `add_piece` tool yet: `pixelate library add` is not built.

| Tool | Command | Notes |
|---|---|---|
| `find_pieces(request, mode)` | `pixelate find --json` | Static. Returns the matches' text metadata and each piece's checked-in `media/thumb.png` as an image to look at. It starts no process and imports no piece code; a thumbnail that is missing, linked, too large or not an image is skipped. |
| `remix_piece(piece, dest, request)` | `pixelate remix --json` | `dest` must be a new or empty folder inside the workspace. Reports the quick baseline honestly: audio and exports it skipped are listed as `not_tested`. |
| `render_piece(piece_dir, image, sets, timeout)` | `pixelate render --json` | `sets` are typed `KNOB=VALUE` strings such as `["time=dusk", "seed=4"]`, each passed as one argument, never through a shell. Never passes `--critique`. |
| `deliver_piece(piece_dir, sets, verify, timeout)` | `pixelate deliver --json` | `verify=true` runs no piece code. |

Limits to keep in mind:
- `remix_piece`, `render_piece` and `deliver_piece` run the piece's `run` commands through the shell, with your user's permissions and no sandbox. Use them on checked-in library pieces and on folders you wrote, never on a folder you have not read.
- Writes stay inside the workspace (`$PIXELATE_WORKSPACE`, else the server's directory). A piece folder inside the kit's `library/` is refused: render and deliver write reports, logs and packages there, so remix it into the workspace first.
- The tools read the command's whole JSON report; unlike `cli()`, they do not keep only its last 6000 characters. A failed run, a refused argument or a timeout comes back as `ok: false` with the reason.
- An image comes back only when the file's bytes hash to what that run recorded, read without following a link. A failed command, a missing or linked frame, or a failed delivery returns none, so an earlier frame is never shown as new. A frame that failed its gate is still shown, and its result says it failed.
- No tool runs a critique or a rating. A gate pass is a technical check, a delivery is a package of checked hashes, and neither says the art is good, that the user approved it, or that rights and the license are cleared.
