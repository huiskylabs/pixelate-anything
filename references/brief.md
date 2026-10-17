# Brief: from one line to an approved brief

Steps 1 to 5 of every job: read the intent, route as a hint, expand into a brief, self-review it,
have an independent art director grade it, and get the user's OK. Drawing rules are in [drawing.md](drawing.md); the gate, the art director, the still and
the animation plan are in [delivery.md](delivery.md).

## Write the brief first

A scene is only as good as its brief. Lantern Isle came out almost in one pass because its
brief (`examples/lantern-isle/BRIEF.md`) decided everything before a pixel was placed: the
art rules, every object, the lived-in details, a palette and signature elements per phase,
motion rates, and the technical numbers. Write every new scene's brief to that density, show
it, and only then build. If you can't fill a section, you don't know the scene yet.

Users usually give one line: "make me a pixel island". Turning that line into a brief at the
density of `examples/lantern-isle/BRIEF.md` is the skill's main job. That brief is the floor, not
the ceiling: it predates the light layer, so a brief today also decides the light regime and every
emitter, the allowed post ops, the value budget and the depth planes, which Lantern Isle never had
to. Do it in this order, before drawing anything.

## Read the intent

Before any tool, write one line on what the user most likely wants but didn't say: the feeling
(calm, epic, eerie, cute), the use (a stream cover, a game mock, a wallpaper), the era or game it
recalls, and what would disappoint them. "A pixel island" from someone making lofi videos is a calm
diorama with seasons; the same words from a game developer are a top-down overworld tile.

## Route as a hint

`pixelate route "the request" --brief` routes and writes the brief skeleton in one call: section 0
names the picked style, the runners-up, and the defaults for what the request leaves open. It
matches keywords, so it is a hint, not the decision: choose from its picks and your read of the
intent, rerun with `--brief STYLE` if you disagree, and say why in section 0. Plain
`pixelate route "the request"` ranks the styles with reasons when you want to compare first.
`pixelate style NAME` prints everything one style fixes; `pixelate style --list` gives one line per
style. Only when none of the picks fits, read "Picking a style"
([guides/styles.md](../guides/styles.md#picking-a-style)).

## Expand into a brief

`pixelate route "the request" --brief -o brief.md` writes the 11 sections with everything the
style decides already filled in, plus section 0, the choices to confirm. Each TODO names the
section to read and the command to run. Fill every TODO yourself with a concrete choice: the
objects with counts and positions, five to ten lived-in details, the palette by named roles, every
light, every motion rate. Invent the specifics the user didn't give; never leave them to the user.

Each TODO names the command it needs; run those, not a tour of the kit. `pixelate tools TOPIC`
(rain, fog, water, 雨) gives the techniques for a subject the brief lacks, `pixelate tools MODULE`
one line per function, `pixelate tools MODULE.NAME` one function in full; `pixelate tools` alone
is the index, for when no topic fits. The brief names the primitives each object is built from (wet
cobbles from `texture.wet_streaks`, a scarf on `sprite.chain`) and calls everything else a slot map
with its size and parts. Finished objects in `references/assets/` are examples to read, never calls
in a brief.

## Self-review

`pixelate route --lint brief.md` flags TODOs left, thin or missing sections, vague words, a motion
table without numbers, periods that don't divide the loop, kit names that don't exist, and a
scene with no hero, masses or value plan line. Read
the brief against Lantern Isle's: would it build at least that quality in one pass? Is every
object specific enough to draw, every imperfection named, every phase more than a recolour? Fix
what falls short and lint again.

## Art director on the brief

The brief already shows the level the picture will reach, so it is graded before anything is drawn.
`pixelate critique --brief brief.md` prints a prompt for a separate agent that did not write the
brief: the 12 points of [art-director.md](art-director.md) read as what the brief makes certain (a
hero with its size, masses of different size, a value plan, a projection that shows the subject, a
signature moment), each scored 1 to 5, and ranked changes to the brief text. Apply them, lint again
and request another critique within the stage's review budget ([delivery.md#art-director](delivery.md#art-director)).
A short brief skips this.

Give it a block-in too: the brief's boxes drawn at native size as flat greys, one grey per value
group, no detail (a few lines of `canvas.Canvas.rect` and `fill`). It shows in one look whether the
hero owns the brightest value, the planes have their shares and the masses differ in size. It
passes `pixelate check BLOCKIN.png --blockin --brief brief.md` and goes to the art director with
`--block BLOCKIN.png`. Drawing waits for the A; if the budget ends below A, report the grade and
unresolved ranked fixes and ask the user whether to continue or change the brief.

## Confirm

Show a full brief for approval only at A, with section 0 on top: "these are the choices I made; say
OK, or change any line". One OK should be enough to build. If they change something, revise the
brief and show only what changed. A below-A budget-stop report is not a brief approval request.
Build only from an approved brief; a short brief skips brief-stage review and is confirmed as
written below.

## Short brief

**Small asks get a short brief.** A palette, one sprite, an icon set or a pixelated photo does not
need 11 sections. Write section 0 (the choices to confirm) and only what the ask decides: the use
and size, the style, the palette by named roles, the parts of each sprite or icon, the frames if it
moves, and the checks. Confirm it the same way. `--brief` writes the short brief by itself for a
small ask; `--full` forces the 11 sections.

## The 11 sections

Each one is concrete: names, counts, positions, colours, rates.

### 1. Purpose and delivery

What it is for (a video cover, a game key art, a showcase of one style), the loop length, the
outputs (MP4, GIF, page, still) and where it will be seen (full screen, a thumbnail, a README).

### 2. Style and light regime

One preset from `tools/styles.py` (or `lofi`), and what that fixes: light layer `none`, `native`
or `screen`, the blend, the ramp style, the outline mode, the dither vocabulary, the value budget
(`pixelate style NAME` prints all of it). Name the reference style it learns from and what it must
not copy (characters, places, logos, UI layouts). See [drawing.md#light](drawing.md#light).
When the scene needs a light op its style does not allow (rays in `pastel-cell`), say so in one
line with the reason, `- Gate override: allow Post.shaft (the rays through the cloud gap are the
subject)`; `pixelate route --lint` accepts the op then, and rejects the line without a reason.

### 3. Art direction rules

Six to ten rules written for this scene, not generic ones: how objects are authored (slot maps,
seeded shapes), where anti-aliasing and dither are allowed (name the zones), which silhouettes must
read, where rim light falls, which imperfections to build in (a leaning tree, a sagging roof, a
missing plank, a mismatched shutter). Three lines are asked by name: **Silhouette keys** (for each
must-read object, the 2-3 features that make it that thing and its nearest misread: a kite is a tall
diamond with spars, not an envelope), **Light direction** and **Wind**, each stated once, so every
rim, lean and trail follows the same line. See [drawing.md#drawing-objects](drawing.md#drawing-objects).

### 4. The scene

Camera and projection, what fills how much of the frame, the horizon line, and the full object
list with counts as maximums ("4 houses, no more") and rough positions. For a rebuild, inspect the
reference and record its horizon (or that it is outside the crop), visible vanishing point(s),
near/far scale and framing at native size. Routing knows only the request text, not the photo's
camera. Keep an explicit one- or two-point view when requested; decide any stylization with the
user instead of silently changing it to iso. Name the screen-space pixel construction and which
edges and repeated forms must converge. These lines decide most of the grade, so the template
asks for them by name, and the gate reads the first two:

- **Hero**: `x0,y0,x1,y1 (native px); peak value: OBJECT; peak chroma: OBJECT`. A figure stays at
  least 40 px tall at the delivered cell; no other mass over 0.6x its area or within 0.1 L of its peak.
- **Planes**: `street 45% (mid), sky 20% (light), houses 25% (dark), ...`: each object or place and
  the share it takes, named by what it is, never regrouped by value. A band tag (darkest, dark, mid,
  light, brightest, or 1-4 from the darkest) says which grey it takes in the block-in, and several
  planes may share one; only tagged planes are checked. 3/4 top-down gives the ground 40% or more and
  shows roofs as planes seen from above, or it reads as a facade (lint checks this, not the block-in).
- **Layout**: what owns each region as boxes, and the calm areas as boxes with what may sit in them.
- **Masses**: three or four masses of very different size, with sizes, for every field that fills
  a band (cloud sea, roofs, crowd); never an even row of equal lobes.
- **Value plan**: three or four value groups and what falls in each, one of them dark, and the one
  focal light that alone holds the brightest values.

See [drawing.md#composition](drawing.md#composition).

### 5. Lived-in details

Five to ten small, specific things that tell a story: a cat on the sill, a mug on the rail,
firewood by the wall, a patched tile, a worn path. Give each its native size (4x3 px or more) and
its value step against what it sits on: three readable details beat eight invisible ones. Say which
change per phase.

### 6. Phases

For each: a palette written as named roles ("misty teal sky, sage canopy, blossom pink, warm amber
windows"), its signature elements (things only it has, not a recolour), and what its music does.
A **Music** line gives every scene its style's music direction (`pixelate style S`): voices, metre,
mode, tempo and one sync point to the loop (a bell when the beam breathes); an era piece uses the
console's chip voices. It is direction only, never `none` unless the request asks for silence. An **Accent ration** line names each accent hue, the only objects that may carry it and its
share of the frame. See [drawing.md#phases](drawing.md#phases) and [drawing.md#palette](drawing.md#palette).
For music, give each phase a style (lofi, chiptune, ambient), a tempo, a key and its lead
instrument; that is all the brief needs. `cycle` is one pass through all
phases in seconds: each phase's bars at its own tempo plus one transition bar, summed, so phases
may differ in tempo and length (`pixelate check SCENE` prints the right number). `grand` is how
many passes make the delivered loop, usually 1, and the picture loop is `TICKS = cycle x grand x 30`. The music itself is written at step 6
([guides/music.md](../guides/music.md)).

### 7. Light list

Every emitter: what it is, where, its colour, its size or radius, how it moves or flickers, and
what it lights or what hides it (the near plane, a door frame). Say whether each occluder is
opaque, partial (a float opacity) or gapped (slits between curtain panels): a light map's occlusion
is flat 2D, so a thin strip drawn opaque blocks a whole wedge.

### 8. Motion table

Every moving thing with its rate and frame count: "flames 4 frames at 10 fps on a hold table;
trees sway 2 frames at 2 fps; clouds one trip per loop; a character cycle of 4 drawings held 3
ticks". Every period must divide the loop. See [drawing.md#motion](drawing.md#motion).

### 9. Particles

Kinds, sprite variants, densities, depth layers and paths (petals on irregular paths in 3
variants, about 200 rain streaks at 480x270 in two layers).

### 10. Never

What this scene must not do: the effects its style bans, symmetry, clutter, text, people (if so),
anything that would make it read as a filter.

### 11. Technical

Native canvas, scale to the delivered size, fps, loop length in frames, palette size, and the
checks it must pass (the gate `pixelate check FRAME.png --style S --scale N`, the loop seam, a
thumbnail test). See [delivery.md#gate](delivery.md#gate). An era piece adds its tile budget (unique 8x8 tiles against
the console's limit) and its sprite limits per scanline and on screen ([guides/eras.md](../guides/eras.md)).
