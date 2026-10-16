# Delivery: gate, art director, still, animation plan

Steps 7 to 10 of every job, after the brief is approved ([brief.md](brief.md)) and the frame is
drawn ([drawing.md](drawing.md)). Nothing is shown or delivered before the gate passes.

## Gate

`pixelate check FRAME.png --style S --scale N` on the delivered frame, plus `--pal palette.json`,
`--pre prelight.png` (the frame before its light layer), `--actor mask.png`, `--used op,op` (the
post ops you ran) and `--intent mask.png` (flecks placed on purpose) when they apply. Engine scenes
also run `pixelate check SCENE`. Redraw until every line passes.

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
differs from its surroundings by hue alone, with under 0.025 L between them, fails. The gate does
not judge whether there is one clear focal point; the art director does (below).

The music gate does
the same for sound: write the music yourself in any code, render it, `pixelate check TRACK.wav`
until it passes (`guides/music.md`).

## Art director

The gate passes weak drafts; an outside eye catches what it can't. The brief was graded A before
drawing ([brief.md](brief.md#art-director-on-the-brief)); now the still is. Run
`pixelate critique FRAME.png --brief brief.md [--style S]`: it writes a 480 px thumbnail and its
greyscale next to the frame and prints a ready prompt (the rubric in
[art-director.md](art-director.md), the brief's section 0, signature elements, rules, scene and
lights, the image paths and the bar). Send that prompt to a fresh agent or a second model that did not draw the frame; it
returns a grade, 12 scores and up to 5 ranked fixes. Apply the fixes, pass the gate again and run a
new critique with `--prev LAST.md`, so the art director first checks each earlier fix as fixed,
partly or not, until it grades A. Your own report of a fix is not evidence, and passing the gate
means legal, not good: never grade your own still. Don't argue with a fix; if the brief causes it,
change the brief.

## Still

Show one still for go/no-go: one frame, at the delivered scale, gate passed and graded A by the art
director, with its last critique in one line (`AD: A, signature: ..., kept: ...`). Only an A still
goes to the user. The user accepts it or says what to change; change it, gate it, critique it again
and show it again.

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
