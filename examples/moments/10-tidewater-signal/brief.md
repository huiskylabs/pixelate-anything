# Signal from Tidewater: J-card cover stills (scene brief, short)

Request: a five-cue original soundtrack for an invented coastal adventure game, one 5-note leitmotif in every cue, and a 270x480 lofi cassette J-card cover: a lighthouse keeper's radio on a windowsill with the storm outside; the tape spools and VU needle animate in a short loop. This brief covers the two cover stills (the best moments) and the 5 s overworld sample.

## 0. Choices to confirm

- **intent**: a quiet, warm-against-cold cassette cover a stranger stops on: the radio's amber dial is the only warm thing in a blue storm night, and it reads as "someone is listening for a signal". Disappointing would be a generic window, a radio that reads as a microwave, a busy sky or a loud title.
- **style**: `lofi` (palette-step light, Bayer bands, own-material outlines); runners-up `cosy-lightmap` (needs a light layer), `contre-jour` (no warm interior).
- **projection**: side, straight-on to the window; the sill top seen slightly from above (52 rows deep).
- **time and weather**: night storm; rain driven from the right off the sea.
- **phases**: two stills of one loop: A "The radio in the storm", B "Lightning" (the flash frame).
- **figures**: none (the keeper is implied by the mug, logbook and pencil).
- **purpose and outputs**: cover stills 1080x1920 (270x480 at 4x), 1x copies, palette JSON; a 5.0 s sound sample (wav + mp3).
- **music**: chiptune overworld cue at 132 bpm in A major, I-V-vi-IV, the leitmotif E5 F#5 C#6 B5 E6 on a 25% pulse.

## 1. Purpose and delivery
- A cassette J-card cover for an invented game soundtrack ("SIGNAL FROM TIDEWATER"), seen full size and as a 270 px wide thumbnail in a showcase.
- out/10-a.png and out/10-b.png at 1080x1920 (270x480 native, 4x nearest), out/10-a@1x.png, out/10-b@1x.png, out/palette-a.json, out/palette-b.json.
- Loop (for the later animated cover, not delivered here): 20 s = 600 ticks (one engine cycle of the overworld cue); spools turn 4 drawings at 10 fps (period 12 ticks), the VU needle 5 positions on a hold table of 30 ticks, the beam 8 angles held 15 ticks (period 120 ticks), one lightning strike per loop held 3 ticks (B is that frame).

## 2. Style and light regime
- Style `lofi`: light layer none, palette-step blend, `lofi` ramps, own-material outlines, Bayer 4x4 only in the sky and sea bands (10-16 row seams).
- No post ops at all: the dial glow, the sill pool, the beam and the flash are palette slots and slot changes.
- Learn the grammar of Lantern Isle only; no real radio model, brand, logo or existing character. The title is invented and set in the kit's pixfont.

## 3. Art direction rules
- Every object is a slot map written in art/cover.py: the radio front built plane by plane with hand-placed parts (ASCII grids for knobs, spools, VU meter, mug, logbook corner); clouds from seeded `shapes.cloud_mask` masses placed by hand; sea crests and rain from hand-listed or hashed positions, never a grid.
- Outlines in each material's darkest step; the window frame and the room are a dark near plane that frames the lit storm (a proscenium).
- The radio cabinet takes a cool 1 px rim on its top and window-side edges (the window is behind it); its front is lit only by its own dial: warm steps around the dial bezel, on the knob tops and in a hand-shaped pool on the sill in front of it.
- Silhouette keys: radio = a boxy cabinet with rounded top corners, a wide lit dial window with scale ticks and a pointer, two round knobs, a speaker grille of vertical frets, a cassette door with two visible spools, a bent telescopic antenna (not a microwave or a TV: the grille, the antenna and the spools decide it); lighthouse = a tall tapered banded tower, a gallery rail, a lantern room with a lit lamp and a cap, on a rock (not a chimney or a post); mug = a cylinder with a handle and a dark enamel rim; logbook = a flat cloth-bound book with a page edge and a folded corner.
- Built imperfections: a cracked lower pane taped over with two strips of masking tape (crossed, one torn short); a chip in the mug's enamel rim; a dog-eared logbook corner; the antenna bent at its second section; one replaced wainscot board a step darker; the cassette PLAY key held down.
- Light direction: inside, the dial (radio front, left half) is the one warm light, falling forward and down onto the sill; outside, cool storm light from the window behind everything, and the lighthouse beam from the right. In B the flash comes from the window: every room edge that faces the glass takes a cold rim.
- Wind: from the right (off the sea), strong: rain slants down to the left (1 px left every 3 rows), wave crests lean left, surf spray blows left off the far rock.
- Hand-placed and asymmetric: rain streaks 3-9 px in two layers, drops on the glass 1x2 to 3x4 in clusters thicker near the bottom rail, crests and whitecaps of mismatched length with uneven gaps.

## 4. The scene
- Projection: side. Canvas 270x480. Horizon at y 236 (49% down: the radio, not the sea, owns the lower half).
- Hero: 56,284,214,386 (native px); peak value: the dial window; peak chroma: the dial window's amber glow
- Planes: room near plane 33% (1), far rock and tower 1% (1), cloud deck 31% (2), sea 11% (2), sill top 6% (2), sky gap under the deck 8% (3), radio cabinet 9% (3), mug and logbook 2% (3), dial window 1.5% (4)
- Layout: window glass x 26-251, y 0-333 (upper sash y 0-159, meeting rail y 160-169, lower sash y 170-333); left jamb x 0-25, right jamb x 252-269; bottom rail y 334-341; sill top y 342-397; nosing y 398-409; wainscot y 410-479. Radio x 56-214, y 284-386, its dial window x 66-144, y 297-320. Lighthouse x 214-227, y 182-234 on a rock x 196-250, y 228-242. Title block x 62-207, y 16-38 in the calm top band.
- Calm areas: the top sky band y 0-58 (title only: no rain or drops inside the title box), the wainscot (board seams only), the far sea band y 236-250.
- Masses: three storm masses in the upper pane, about 60%, 30% and 10% of the window width, billowed tops with lobes of radius 9-27 px, long flat undersides (one 1 px step), one lit edge on the beam side (right); under the rail the storm's low ragged base lies over the pale gap; the sea has three swell bands of different depth (14, 40 and 50 rows) with crests of 4-26 px, never even.
- Value plan: darkest: the room near plane, L .11-.23; dark: the sea and the sill top, L .13-.31 (the sill steps up to .60 only in the dial's pool); mid: the storm sky L .17-.57 and the radio cabinet L .21-.45, the title L .70 in 21 small letters; brightest: the dial window L .80-.92, with its one repeat the lighthouse lantern (L .86, 4x3 px); the beam steps from .74 at the lantern down to .52 at its far end, so it is brightest only at its source.
- Objects (counts are maximums): 1 radio with 1 antenna, 2 knobs, 1 dial, 1 VU meter, 1 cassette (2 spools), 1 grille; 1 lighthouse on 1 rock; 1 beam (from the lantern leftward, ending at the antenna tip: the leading line lands on the hero); 1 mug (right of the radio); 1 spare cassette case on the radio's top; 1 logbook with 1 pencil (front left); 1 sash lock; 1 taped crack; 1 power cord from the radio's right foot over the nosing to a socket on the wainscot.

## 5. Lived-in details
- Chipped enamel mug, 15x20 px, right of the radio: off-white body a step above the sill, navy rim, a 2x2 chip; its window side takes the cool rim.
- Logbook, 52x18 px, front left in the dial's pool: bottle-green cloth cover, cream page edge 3 px, top-right corner folded (dog-eared, 6 px triangle a step lighter).
- Pencil, 30x3 px, diagonal across the logbook: natural wood, graphite tip, a dull red eraser.
- Cracked lower-left pane with two crossed strips of masking tape, 4x18 px each, a step above the sea behind.
- Cassette PLAY key held down (2 px lower than its neighbours); the spools carry uneven tape packs (left full, right thin).
- A spare cassette case lying on the radio's top, 28x7 px (its J-card a cream step above the cabinet), breaking the cabinet's long top edge.
- A cassette case leaning against the wainscot at bottom left, 16x14 px, cropped by the frame edge, its hand-lettered label a step off the wall.
- Sash lock on the meeting rail, 10x5 px, a brass step above the rail.
- Power cord from the radio's right foot across the sill and over the nosing to a socket on the wainscot, 2 px cable, socket 10x12 px; a worn notch in the nosing 6x3 px.

## 6. Phases
- A "The radio in the storm": palette by roles: slate-teal storm sky, deep teal sea, pale cool rain and foam, a pale lamp-white beam, blue-violet room darks, worn blue-grey window paint, walnut radio, oak sill, cream paper, amber-to-cream dial. Signature: the beam reaching the bent antenna, rain streaks and drops on the glass, the dial glow pooling on the sill.
- B "Lightning": palette.flash on the window slots only (sky, sea, rain, foam, beam, tape) toward a cold white-blue (#e6efff); the room, the radio and the dial keep A's colours. Signature: a forked bolt into the sea left of the lighthouse, passing behind the meeting rail; the lighthouse and its rock drop to a hard silhouette; the beam is washed out; rain streaks over the sea turn bright; cold rims on every room edge facing the glass (radio top, antenna, mug rim, logbook back edge, sill back edge, frame inner edges); the dial still warm. Same pixels as A everywhere nothing moves (the spools and the VU needle are one step on).
- Accent ration: amber/orange (C above .10) only in the dial window and the VU meter face; dull red (C .13) only on the dial pointer and the pencil eraser; brass only on the dial bezel and the sash lock; everything else stays under C .08.
- Music: chiptune overworld cue, 132 bpm, A major, I-V-vi-IV (A - E - F#m - D), 25% pulse lead playing the leitmotif E5 F#5 C#6 B5 E6 (sol la mi re sol: a step up, a fifth up, a step down, a fourth up, ending open; rhythm 2-2-4-2-6 sixteenths), answered over E by E5 F#5 B5 G#5 E5 (the first idea, F#5 A5 E6 D6 C#6, was dropped: its last four notes are the opening of Moon River), a 16th-note pulse2 arpeggio, a triangle bass in octaves, a noise kit (ckick, csnare, chat); sync point: a downbeat on the strike in the animated loop.

## 7. Light list
- Dial window (x 66-144, y 297-320): amber to cream slots Y0-Y4, a warm bezel ring (brass A1-A2), the pool on the sill in front of it as a hand-shaped mask stepping the oak ramp O2 to O5; no blur.
- VU meter face (x 124-143, y 326-343): Y2-Y3, backlit, needle kicked to the right.
- Lighthouse lantern (x 218-223, y 189-192): L .86, 4x3 core; the beam from it as a stepped wedge B3 to B1, 3 px wide at the lantern to 13 px at the antenna tip; rain inside the beam steps up one slot.
- Storm light: cool rims (frame paint F3-F4, wood W3 on the cabinet top) on edges facing the window.
- B only: the flash from the window: X0-X1 cold rims and the sill strip along the window rail outside the radio's shadow.

## 8. Motion table
- Spools: 4 drawings at 10 fps, held 3 ticks each (12 ticks per turn).
- VU needle: 5 positions on a hold table [0,1,1,2,4,3,2,1,1,0], 3 ticks each (30 ticks).
- Beam: 8 angles held 15 ticks each (120 ticks per sweep).
- Lightning: 1 strike per loop of 600 ticks at 30 fps: 1 pre-flash tick, 3 flash ticks (frame B), 2 decay ticks.
- Rain: streaks fall 2 whole spans per loop on the 15 Hz clock (period 300 steps); drops on the glass slide on a 60-tick hold table.
- Periods 12, 30, 120, 600 and 300 (15 Hz) ticks all divide the 600-tick loop at 30 fps (anim.check_periods).

## 9. Particles
- Rain outside the glass: about 140 streaks over the window (two layers: 90 far streaks 3-5 px in N0, 50 near streaks 6-9 px in N1), slanting left; none inside the title box. Drops on the glass: 34 drops in 5 sizes, clustered toward the bottom rail, 6 with 4-14 px trails.

## 10. Never
- glow blur, bloom, lens effects, soft shadows, a light layer, vignette, grain.
- narrow gradient bands that read as stripes; an even row of crests, drops or lobes.
- a real radio model, brand or logo; a second warm light in the room; a title brighter than the dial.

## 11. Technical
- Budget (styles.check, lofi): L<0.1 <= 0.01; black <= 0.001; L>=0.7 <= 0.04; L>0.8 <= 0.02; median_C 0.02..0.1 (A keeps every bound; B's flash moves two, listed below).
- Native 270x480, 4x nearest to 1080x1920; strict palette of about 80 slots for A, the same slots lifted for B; palettes saved as JSON.
- Gate override: L>=0.7 <= 0.42 (frame B is the lightning flash: the window, about 40% of the frame, blows out to cold white-blue by design; A keeps the style's 4%)
- Gate override: focus_contrast >= 0.02 (frame B: the flash turns the far lighthouse and the window frame into hard silhouettes against the blown-out sky, so the strongest edges leave the radio; the dial still holds the peak value and the peak chroma; A measures 75%)
- Gate: `pixelate check out/10-a.png --style lofi --scale 4 --brief brief.md --pal out/palette-a.json` (and the same for B with palette-b.json), plus `--intent` for rain, drops and sparkle; block-in: `pixelate check out/blockin-a.png --blockin --brief brief.md`.
- Sound: 5.0 s from bar 1 of the overworld cue, 20 ms fade-in, 400 ms fade-out, 48 kHz 16-bit stereo wav and mp3; `pixelate check sound/10-sample.wav --style chiptune --use song --bpm 132 --key A`.
