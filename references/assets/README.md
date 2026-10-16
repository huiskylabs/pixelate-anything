# Asset examples (reference only)

These modules draw finished things: boats, docks, carts, crates, barrels, pipes (`props.py`), people,
cats, gulls, slimes (`figures.py`), runes (`glyphs.py`) and baked lofi particles (`particles.py`).

They are here to read, not to call. When a scene needs a boat or a cat, draw your own in the scene's
code, at its size, in its style and pose. Read these to see how one was built: the silhouette, the
slot map, how the ramp runs, where the outline and the lit edge go, how the frames change. A scene
that calls them looks like every other scene that called them, and the point of the kit is that it
can draw anything, not the same few things.

Whatever you draw goes through the same gate: `pixelate check FRAME --style S --scale N`, then a
still for the user's go/no-go.

The drawing tools that carry no look of their own stay in `tools/`: the canvas and slot grid,
palettes and ramps, outlines, dither, shapes and masks, material textures, light layers, projections,
animation timing and the checks.
