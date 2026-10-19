# Delivery: gate, art director, still, animation plan

Steps 7 to 10 of every job, after the brief is approved ([brief.md](brief.md)) and the frame is
drawn ([drawing.md](drawing.md)). Nothing is shown or delivered before the gate passes.

## Gate

`pixelate check FRAME.png --style S --scale N` on the delivered frame, plus `--pal palette.json`,
`--pre prelight.png` (the frame before its light layer), `--actor mask.png`, `--used op,op` (the
post ops you ran) and `--intent mask.png` (flecks placed on purpose) when they apply. Engine scenes
also run `pixelate check SCENE`. Redraw until every line passes.

A brief that serves several images can give each one a `## Image B` section with its own Hero,
Planes and `- Gate override:` lines; `--brief brief.md --image b` gates still B against them (the
Technical section's overrides still apply). `pixelate render DIR` does the whole loop for every image
listed in `DIR/render.json` (draw command, frame, style or era, scale, brief, palette, pre-light
frame, actor): it runs the command, gates, era-checks era images, judges (overlay beside the frame)
and, with `--critique`, runs the art director, then prints one line per image and writes
`render-report.json`. `pixelate render --help` shows the format. It reads a library piece's `DIR/piece.json` the same way
(`references/piece.md`); `library/quarry-wakes` is one.

The frame gate checks budget, square pixels, palette (`--pal`, `--pre`), readability (`--actor`),
allowed post ops (`--used`), pixel craft (`--intent` marks deliberate flecks) and composition. `pixelate style S`
prints the style's value budget and craft limits the gate holds the frame to.

When the scene and the budget disagree, there are three sanctioned ways out, and the report shows each:

- `--scene NAME` picks a style's scene variant, for budgets measured on one kind of scene:
  `cosy-lightmap --scene exterior` (snow or a street at night) and `contre-jour --scene beam` (one
  big beam). `pixelate style S` lists them; the router writes the flag when the request matches.
- `--era gameboy|nes|snes|genesis|gba|pico-8|neogeo` replaces the value budget with the era's own
  checks: screen size, colour count, fixed palette or bit depth, colours per block, unique tiles.
  `--style` still sets the craft limits. Era briefs write this gate line.
- A brief can move one bound with a reason, one line each in its Technical section:
  `- Gate override: L>0.75 <= 0.02 (the beam is the subject)`. The bound is `<= V`, `>= V`,
  `LO..HI` or `off`, for a budget rule, a craft limit or a composition limit. `--brief brief.md`
  applies them; `--budget 'RULE BOUND (reason)'` adds one on the command line. An override without
  a reason is rejected, and the report still prints how far the frame sits from the style's own
  bound, so a reviewer sees the cost. A `- Gate override: allow Post.OP (reason)` line is an
  allowed-effect override for route lint; the gate notes it and moves no bound.

The composition lines catch what a first draft gets wrong and the numbers above miss. `empty_low`:
most of the bottom third has nothing in it (a half-empty street); `empty` (sticker-iso): too much
of the frame is bare ground; `blocky` (pastel-cell, contre-jour): a mass reads as a brick, its
outline mostly long straight runs; `slab` (pastel-cell, contre-jour): one straight edge runs a
quarter of the frame or more, a flat-slab mountain; `banding` (the screen-light styles): smooth light
quantised into concentric rings. A cell "has something in it" when a few of its pixels depart
strongly from its own ground colour, so even snow or paving texture still counts as empty. Each
failing line says what to change. The limits sit in `craftcheck.COMPOSITION` per style, measured
on the showcase finals and drafts and the style references; a style with no failing draft to
calibrate on has no limit yet. Readability also needs a lightness difference now: an actor that
differs from its surroundings by hue alone, with under 0.025 L between them, fails.

The focus lines check that there is one hero. They need the hero's place: the brief's section 4 line
`- Hero: x0,y0,x1,y1 (native px); peak value: OBJECT; peak chroma: OBJECT` (with `--brief`), or the
bbox of the `--actor` mask. The bbox is at 1x and inclusive. The frame is read at thumbnail size
(about 160 cells across, so stars, flecks and dither melt into their ground), and each line says in
plain words what to change when it fails:

- `focus value`: at least half of the frame's brightest cells (its top 0.5%) sit on the hero.
- `focus contrast`: the same for the strongest local light-dark contrast.
- `focus chroma`: no more than 2.5 times as many cells of the hero's own hue, at least as saturated
  as the hero's top 5%, sit outside it (skipped for an era palette and for a block-in).
- `focus rival`: no mass outside the hero weighs more than 0.6 of the hero (weight is size times
  how far it departs from its surroundings), the art director's own cap.
- `focus size`: with both `--actor` and the Hero line, the drawn hero fills at least 85% of the
  planned bbox.

When the peak belongs to a light that is not the hero (a sun, a lamp), the brief names it with its
own bbox in brackets, `peak value: the sun disc (244,6,268,32)`, and that region may hold the peak
and is never a rival. The limits were measured on the ten showcase stills: the kite (both rounds)
and the canal (both rounds) fail, as the art director found, while the observatory, the noodle shop,
the lighthouse round 2 and Lantern Isle pass. The lighthouse round 1, whose boat was a speck inside
its bbox, also passes: a bbox cannot tell a readable hero from a speck, so the art director still
judges that.

The `repeat` line looks for the most common procedural tell: rows of near-identical lobes (cloud
scallops, heather domes, gumdrop waves, cut at the cusps of each colour region's top or underside)
and rows of near-identical units (the same house or roof stamped along a line). It prints WARN,
never FAIL, because it does not separate reliably yet: it finds the kite's cloud sea and the canal's
round-2 row of houses and passes Lantern Isle, but misses some rows the art director flagged and
flags a few rows in good frames. Read it as a pointer to look. A scene that repeats on purpose
writes `- Gate override: repeat off (the reason)`, or `repeat <= N (the reason)`; the focus keys take
overrides the same way (`focus_rival <= 1.2 (reason)`, `focus off (reason)`).

### Block-in

Before drawing, the layout can be judged as a greyscale block-in: flat value masses, one grey per
plane, the hero's light the brightest, no detail. `pixelate check BLOCKIN.png --blockin [--scale N]
[--brief brief.md] [--style S]` checks:

- `value bands`: 3 or 4 distinct greys, each over 1% of the frame (greys within 0.05 L are one band).
- `focal light brightest` and `hero placement`: most of the brightest band, and 80% of its largest
  patch, sit inside the brief's hero bbox (or the light the Hero line names with a bbox).
- `hero size`: what stands out from its surroundings inside the hero bbox fills at least 85% of it.
- `plane shares`: with a brief line `- Planes: street 45% (mid), canal 10% (mid), sky 20% (light),
  houses 25% (dark)`, the shares of the planes tagged to a band are summed, and each band must be
  within 8 points of that sum. Brightest is the top band (the hero's light), darkest the bottom one,
  dark, mid and light spread over the bands below the top, and 1-4 count from the darkest. Untagged
  planes are listed, not matched: never sink a house into a dark band or rename planes as value
  groups to pass.
- `block-in empty` and `empty_low`: on a coarse 16-column grid, a cell is empty when one grey covers
  97% of it; the bottom third stays under 88% empty, and `--style` adds the style's own `empty` limit.
- `block-in slab`: one straight inner edge running over half the frame. A block-in is made of
  rectangles, so the frame limit (a quarter) would always fire; `blocky` is skipped for the same reason.
- the focus lines, without chroma.

The art director still judges whether the frame has one clear focal point (below); the focus lines
only catch the cases where the numbers already show it does not.

The music gate does
the same for sound: write the music yourself in any code, render it, `pixelate check TRACK.wav`
until it passes (`guides/music.md`).

## Art director

The gate passes weak drafts; an outside eye catches what it can't. A full brief is reviewed before
drawing ([brief.md](brief.md#art-director-on-the-brief)); a short brief skips brief-stage review.
The still is reviewed after it passes the gate. Run
`pixelate judge FRAME.png --overlay judge.png` first: it boxes what the gate passes and an art director
rejects (masonry-like rock, rows of identical units, scalloped edges, masses drawn as 1 px outlines,
murky values), each with a fix; fix each box or say why it stays. `--log` keeps the run in
`.pixelate/judge-log.jsonl`, the corpus the detectors are calibrated on. Then
`pixelate critique FRAME.png --brief brief.md [--style S]`: it writes a 480 px thumbnail and its
greyscale next to the frame and prints a ready prompt (the rubric in
[art-director.md](art-director.md), the brief's section 0, signature elements, rules, scene and
lights, the image paths and the bar). Send that prompt to a fresh agent or a second model that did not draw the frame; it
returns a grade, 12 scores and up to 5 ranked fixes. Your own report of a fix is not evidence, and passing the gate
means legal, not good: never grade your own still. Don't argue with a fix; if the brief causes it,
change the brief.

**Review budget (visual and music).** Each full-brief and still stage allows at most three graded lead
calls by default (including round 1); an A ends review sooner. After the first broad lead
round, when needed, consult at most **two visual specialists total per artifact**, chosen from
`composition`, `lighting`, `set` (architecture, props and story of place) and `character`:
`pixelate critique FRAME.png --brief brief.md --role composition` (or use the full brief and block-in).
Each sees the same artifact and brief and gives concrete observations, no grade. Feed their saved
notes into a subsequent lead round using repeatable `--consult NOTE.md` (at most two); the lead
reconciles disagreements and remains the sole A/B/C grader, 12-score rubric user and author of up
to five ranked fixes. Specialists do not add graded rounds. `--prev LAST.md` is only the prior
**lead** critique, never specialist notes. After a non-A lead grade, apply its ranked fixes, re-lint
the brief or pass the frame gate again, then request the next lead critique with `--prev`; it checks
earlier fixes as fixed, partly or not.

Music review is separate and opt-in after rendering and passing `pixelate check TRACK.wav` (MCP
`check_music`). `pixelate critique-music TRACK.wav --brief brief.md [--prev LAST.md]` (MCP
`music_critique_prompt`) prints a prompt for a separate agent to actually listen to the rendered
audio and read the brief. The tool does not listen or invoke an agent. If the reviewer cannot hear
the audio, it returns `NOT REVIEWED`, never a grade. Music has its own default three graded review
calls, counting the initial call; `--prev` is the previous music critique.

Save each externally produced lead critique to a report file. To bind evidence to the exact
artifact bytes after review, run `pixelate review record --brief brief.md --critique lead.md`
for a full brief, or `pixelate review record --brief brief.md --frame still.png --critique lead.md`
for a still (MCP: `record_visual_review(brief, report, frame='')`). The versioned manifest is
adjacent to the reviewed brief or frame, separate for each still. It records SHA256 hashes of the
brief, frame when present, and report, plus stage, grade and report location. The report must follow
the [lead visual rubric](art-director.md#what-you-return): standalone A/B/C grade, twelve 1–5
scores and originality, signature moment, biggest problem, up to five ranked fixes (3–5 below A),
and KEEP. Specialist observations, music critiques, NOT REVIEWED and structurally malformed reports
are rejected. The parser cannot judge whether a fix really names where, what and how; the independent
reviewer must provide substantive fixes. Neither command asks a model to review or invents a grade.

Run `pixelate review status --brief brief.md [--frame still.png]` (MCP:
`visual_review_status(brief, frame='')`) before claiming an A: only matching A evidence prints
READY with CLI exit 0. Missing evidence, changed bound brief/frame/report bytes, a malformed
manifest or a non-A grade is not ready (nonzero with a reason). Brief status is only for the full-brief stage; still status
is only for that particular still. Short briefs skip brief-stage review. Status catches a malformed
manifest or changed bound files, but someone with write access can replace a valid manifest and
report together. These hashes bind local files, **not reviewer independence or authenticity**;
even READY does not attest that the frame passed `pixelate check` or that the user approved the
brief, still or animation plan.

Stop on an A. If round 3 is still below A, stop automatic revision and review for that stage:
report the grade and unresolved ranked fixes to the user, and ask whether to continue reviewing
or change the brief. Only a user who explicitly allows more rounds may extend that stage's budget.
A below-A brief is not ready for approval or drawing; a below-A still is not a finished still for
go/no-go or delivery. Prompt commands generate one prompt per call; the caller tracks rounds and
specialist consults.

## Still

Show one still for go/no-go: one frame, at the delivered scale, gate passed and graded A by the art
director, with its last critique in one line (`AD: A, signature: ..., kept: ...`). Only an A still
is presented as finished; if review stops below A, report the status and ask the user as above,
not for go/no-go on a finished still. The user accepts an A still or says what to change; change it,
gate it and follow the review budget above before showing it again.

## Animation plan

Confirm the animation plan, then animate. Before any motion, show the plan: the loop length in
seconds and frames, what moves, and each rate and frame count (the motion table, with every period
dividing the loop; see [drawing.md#motion](drawing.md#motion)). Animate only after the user says
OK. Every animated frame passes the gate like the still did. Preview with
`pixelate shot SCENE t [t...] --grid` and look at the frames.

## Export

Export at whole-number scales with nearest neighbour, so pixels stay square. For video, use even
scales, which keep colours exact. `pixelate build SCENE --release` makes the live page,
`pixelate video SCENE out.mp4 --audio loop.wav`, `pixelate gif SCENE out.gif`.

## Failure checklist (look at shots at zoom 3-4 for each)

Run the gate first: `pixelate check FRAME.png --style S --scale N` (with `--pal`, `--pre`,
`--actor`, `--used`, `--intent` as they apply) must pass every line before a frame is shown or
final; engine scenes also run `pixelate check SCENE`. It measures palette, budget, square pixels,
readability, post ops and pixel craft. The rest of this list is judged by eye.

- [ ] Any colour outside the palette, or blur in the pixel layer? The gate's palette line catches it (`--pal`, `--pre`): light belongs in the light layer, and only in styles that have one.
- [ ] Sky or sea reads as stripes: widen the dither transitions, or walk the strata boundaries.
- [ ] A canopy reads as a ball, a roof as a brick wall, rock as noise: redraw with clumps, offset courses, shaped cells.
- [ ] Smoke, mist or light reads as dots or squares: hand-shape it.
- [ ] A trailing scarf or tail reads as a stick: shorten the chain and fix its segment length.
- [ ] Too busy: cut particles and motion.
- [ ] Subject too small, or empty half-frame: recompose. The art director grades it (`pixelate critique`).
- [ ] A phase only looks like a recolour: add signature elements.
- [ ] The gate fails a budget or craft line (orphans, jaggies, stripes, doubled outlines, pillow shading, clusters): redraw, then run it again.
- [ ] The seam jumps at loop end: `pixelate check` flags it in engine scenes; in Python scenes compare `frame(T)` with `frame(0)`.
- [ ] The brief has a section you skipped: go back and write it.
- [ ] Animating before the still got a go and the animation plan an OK: stop and show them.
