# Brief: from one line to an approved brief

Steps 1 to 4 of every job: read the intent, route as a hint, expand into a brief, self-review it,
and get the user's OK. Drawing rules are in [drawing.md](drawing.md); the gate, the still and the
animation plan are in [delivery.md](delivery.md).

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

`pixelate route "the request"` ranks the styles with reasons, names the mode (scene, rebuild, era,
assets, music), suggests kit calls for the subject, and lists what the request leaves open with
defaults. It matches keywords, so it is a hint, not the decision: choose with the questions in
"Picking a style" ([guides/styles.md](../guides/styles.md#picking-a-style)) and your read of the
intent, and say why in section 0. `pixelate style NAME` prints everything one style fixes.

## Expand into a brief

`pixelate route "the request" --brief -o brief.md` writes the 11 sections with everything the
style decides already filled in, plus section 0, the choices to confirm. Each TODO names the
section to read and the command to run. Fill every TODO yourself with a concrete choice: the
objects with counts and positions, five to ten lived-in details, the palette by named roles, every
light, every motion rate. Invent the specifics the user didn't give; never leave them to the user.

Know the whole kit: `pixelate tools` lists every topic and module, `pixelate tools TOPIC` (rain,
fog, water, 雨) gives the techniques for a subject, `pixelate tools MODULE` the functions with
their signatures. The brief names the primitives each object is built from (wet cobbles from
`texture.wet_streaks`, a scarf on `sprite.chain`) and calls everything else a slot map with its
size and parts. Finished objects in `references/assets/` are examples to read, never calls in a
brief.

## Self-review

`pixelate route --lint brief.md` flags TODOs left, thin or missing sections, vague words, a motion
table without numbers, periods that don't divide the loop, and kit names that don't exist. Read
the brief against Lantern Isle's: would it build at least that quality in one pass? Is every
object specific enough to draw, every imperfection named, every phase more than a recolour? Fix
what falls short and lint again.

## Confirm

Show the user the brief with section 0 on top: "these are the choices I made; say OK, or change
any line". One OK should be enough to build. If they change something, revise the brief and show
only what changed. Build only from an approved brief.

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

### 3. Art direction rules

Six to ten rules written for this scene, not generic ones: how objects are authored (slot maps,
seeded shapes), where anti-aliasing and dither are allowed, which silhouettes must read, where rim
light falls, which imperfections to build in (a leaning tree, a sagging roof, a missing plank, a
mismatched shutter). See [drawing.md#drawing-objects](drawing.md#drawing-objects).

### 4. The scene

Camera and projection, what fills how much of the frame, the horizon line, and the full object
list with counts and rough positions (left third, on the ridge, by the door). Name the subject and
the calm areas where the eye rests. See [drawing.md#composition](drawing.md#composition).

### 5. Lived-in details

Five to ten small, specific things that tell a story: a cat on the sill, a mug on the rail,
firewood by the wall, a patched tile, a worn path. Say which change per phase.

### 6. Phases

For each: a palette written as named roles ("misty teal sky, sage canopy, blossom pink, warm amber
windows"), its signature elements (things only it has, not a recolour), and its music if there is
any. See [drawing.md#phases](drawing.md#phases) and [drawing.md#palette](drawing.md#palette).

### 7. Light list

Every emitter: what it is, where, its colour, its size or radius, how it moves or flickers, and
what it lights or what hides it (the near plane, a door frame).

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
thumbnail test). See [delivery.md#gate](delivery.md#gate).
