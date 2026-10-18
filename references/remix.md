# Remix a library piece

Read this before `pixelate remix`. It covers the copy and its baseline only. `render --set` renders a variant of a script, engine or pack piece that declares knobs (`references/piece.md`); distance from the base is not built yet, `pixelate deliver` packages a finished piece ([delivery.md](delivery.md#deliver)), and `pixelate new` is still a plain copy, not an alias of remix.

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

`.pixelate/remix-baseline.json` (local; git ignores `.pixelate/`) holds the request, the base id, status and review, the SHA-256 of every copied file as tested (`files`, `files_sha256`), the full test report with each rendered output's hash, and the untested outputs. Remix prints the baseline file's own SHA-256. If the copy's files change while the baseline renders, the remix fails.

`REMIX.md` holds the request, the base's summary, status and declared license, the baseline results, the anatomy table, the knobs, a plan table (subject, setting, camera, palette, composition, motion, sound: what stays and what changes) and a checklist. Fill in the plan before editing. Prefer knob files, then the files the anatomy names.

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
