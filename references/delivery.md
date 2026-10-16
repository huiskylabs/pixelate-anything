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
- `plane shares`: with a brief line `- Planes: ground 45%, sky 20%, buildings 25%`, the planes are
  matched to the bands by share (largest plane to largest band, the brightest band left out when it
  is the hero's light), and each must be within 8 points of the brief.
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
