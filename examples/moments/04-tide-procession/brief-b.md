# Tide Procession B: "The door opens" (gate lines)

The full brief is brief.md (same scene, same palette, same camera). This file carries only the lines
the frame gate reads for image B, because the hero moves from the procession to the door.

## 4. The scene (B)

- Hero: 432,160,530,242 (native px); peak value: the moon disc and its halo ring (444,84,492,132); peak chroma: the open portal and its spill
- Value plan: near plane, monastery and pilgrims L .10-.14 (darkest); night sky, far sea, channel L .17-.26 (dark); the moon's glow, the horizon band, the lit shallows and the shaft L .27-.40 (mid); brightest only at the moon (peak L .95, cold) and the open portal (L .86 at the threshold, warm), the wedge stepping down from .7 at the top tread to .3 at the landing; lanterns stay 1-2 px points
- Story: the first pilgrim stands in the portal, a silhouette with warm rims; two more climb the flight in the widening wedge, their hoods rimmed warm; the rest string out along the road; the flood has crept over the road's low stones behind the last pilgrim (x 26-190).

## 7. Light list (B)

- Door: gold #ffc070 Post.lightmap, sigma (46, 36), gain 4.2, one light low inside the portal at (511, 198), blocked by the facade above the terrace (opaque) and by the door leaf (opaque, opened inward against the left jamb: the moving occluder, open drawing), weighted by a soft angular wedge from the threshold down the stair flight (141-179 degrees, fading by 120 px); a warm Post.light wash radius 56 px in the same wedge, and a small glow in the opening.
- Shaft: cold #b9c9d6, width 8 to 34 px, angle 106 (it has breathed west across the water since A), blocked by the island, moon and figures.

## 11. Technical (B)

- Gate: `pixelate check out/04-b.png --style contre-jour --scene beam --scale 3 --brief brief-b.md --pal out/palette.json --pre out/04-b-pre.png --actor out/04-b-actor.png --used light,shaft,glow,lightmap --intent out/04-b-intent.png`.
- Gate override: allow Post.lightmap (the request asks for the door spill as a lightmap with the door leaf as a moving occluder)
