# Music: lofi, chiptune and ambient loops

`music.js` defines `SCENE_MUSIC = { phases: [...], trans: [...] }`, with one entry of
each per phase, in the order of `config.js`. Every sound is synthesised (no samples, nothing to license).

**Lofi:**
- FM Rhodes, plucked guitar, felt piano, music box, pad and upright-style bass.
- Drums, ambience beds (rain, waves, cicadas, wind, leaves, fire) and vinyl crackle.
- Tape wobble.

**Chiptune:**
- NES-style pulse waves with a 4-bit stepped volume.
- A 32-step triangle bass.
- LFSR noise drums.

**Ambient:** pads with sparse voices over a sub drone.

All of it runs through reverb, a glue compressor and a limiter.

## Music on its own (game loops, soundtracks)

`pixelate new music my-track` gives a music-first project (a chiptune phase handing off
to an ambient one) with a small equaliser for the page. Edit `music.js`, keep `cycle` as
`check` reports it, then:

```
pixelate check my-track
pixelate audio my-track theme.ogg      # .ogg for games, .wav for editing or video, .flac, .mp3
```

- **Exact loop:** the file is exactly one loop long (`cycle x grand` seconds) and its end flows into its start.
- **Formats:** OGG and WAV loop gaplessly in game engines. MP3 adds encoder padding, so avoid it for loops.
- **Length:** use `grand: 1` for a single pass through the phases, or more for longer, varied loops.

## Styles

Set `style` on a phase. The style fills in defaults, and anything the phase sets itself wins:

| style | defaults |
|---|---|
| (none) = lofi | as below: Rhodes, guitar, piano or musicbox, swung drums, ambience |
| `chiptune` | lead `pulse` (25% duty), comp `arp` (16th-note `pulse2` arpeggio), bass `tri` in octaves, noise kit (`ckick`, `csnare`, `chat`), no swing, no vinyl or tape |
| `ambient` | comp `pad` with `padVoice` notes on top, `bassMode: 'drone'` (a sub pad), no drums, `mel` 0.5 |

Phases of different styles can follow each other: the turnaround blends them as usual.

Typical chiptune tempos run 110-160 bpm with simple triads, I-V-vi-IV or vi-IV-I-V, and a melody `scale` an octave up.
Ambient runs 60-75 bpm with 7ths and 9ths, a slow `mel`, and `amb` wind or waves.

Texture is global: `SCENE_MUSIC.texture = { vinyl: 0.4, tape: true }`. If every phase is chiptune, the default is neither.

## A phase

```js
{ name: 'rain',
  swing: 0.25,                   // 0.15 to 0.28: how far off-beat 16ths lean
  style: '',                     // '' (lofi) | 'chiptune' | 'ambient'
  lead: 'piano', comp: 'piano',  // lead: rhodes | guitar | piano | musicbox | pulse; comp also 'pad' or 'arp'
  padVoice: 'musicbox',          // comp 'pad': the instrument that plays over the pad
  arpInst: 'pulse2',             // comp 'arp': the arpeggio instrument
  bass: 'bass', bassMode: '',    // bass: bass | tri ; bassMode: '' (walking) | 'octaves' | 'drone'
  drums: true,                   // false: no drums in this phase
  amb: [['rain', 0.5]],          // rain | waves | cicadas | wind | leaves | fire, with levels 0.05 to 0.6
  chords: [[45, [55, 59, 60, 64]], [41, [52, 57, 60, 65]], [38, [53, 57, 60, 64]], [40, [56, 59, 62, 64]]],
  scale: [64, 67, 69, 71, 72, 74, 76, 79, 81],   // notes the melody may use (MIDI)
  mel: 0.65,                     // chance of a 2-bar melody phrase
  alter: { 3: { 67: 68 } },      // optional: bend melody notes over chord 3 (here G -> G#, for E7)
  kick: [[0, 0.85], [6, 0.45], [9, 0.7]],        // [16th step 0..15, velocity]
  snare: [[4, 0.6], [12, 0.6]],
  snd: 'brush',                  // snare | brush | rim
  hats: 8,                       // 0 | 8 | 16 per bar
  shaker: 0,                     // level; 0 = off
  shakerStep: 1,                 // 1 = every 16th, 2 = every 8th
  ohat: 0 }                      // chance of an open hat at the end of a bar
```

- **Chords** are `[bass, [voicing]]` in MIDI (60 = middle C). The loop plays through the phase's bars; four chords over 8 bars is the classic lofi pace.
- **Voicings** have 4 or 5 notes between 47 and 69. Use 7ths, 9ths and 13ths, close voiced, without doubling the bass.

## Giving each phase its own character

Change several things at once so a phase change is felt, not just heard:

- **Key and mode.** Use major 9ths for warm or open phases, minor 9ths and half-diminished chords for rain or night, and suspended or quartal voicings for cold.
- **Tempo** (`bpm` in config.js), roughly 62 to 82. Faster and swingier feels summery; slower and straighter feels wintry.
- **Lead instrument.** Rhodes is soft and nostalgic, guitar is bright and outdoorsy, felt piano is intimate and rainy, music box is cold and twinkly over a pad.
- **Drum feel.** Snare for a crisp groove, brushes for gentle rain, rim and shaker only for sparse winter. Hats at 16 per bar are busy; 0 is still.
- **Ambience** that matches the picture: rain when it rains on screen, a fire in winter, cicadas at a summer dusk.

## Turnarounds (`trans`)

Between phases there is one bar where the tempo ramps from one phase to the next
(a DJ-style blend: the outgoing bus fades and filters down, the incoming one fades up
and opens). Over that bar the harmony walks a **ii-V into the next phase's first
chord**, and the bass steps chromatically onto its root:

```js
{ pre: [47, [53, 57, 59, 62]],    // ii (pre-dominant): Bm7b5
  dom: [40, [56, 59, 62, 65]],    // V (dominant): E7b9
  approach: 44 }                  // bass note on the last half-beat: G#, a half step below the target A
```

Recipe for a target chord with root `r`:
- **ii:** root `r + 2`. Use m9 if the target is major; use m7b5 if the target is minor.
- **V:** root `r + 7` (or `r - 5`). Use a 13 chord if the target is major; use 7b9 if the target is minor.
- **approach:** `r - 1` (or `r + 1`).

The incoming lead often plays a short pickup over the V, and the riser swells into
the downbeat.

## Loudness and loop

- The mix lands near -13 LUFS integrated with peaks around -0.7 dBFS. For YouTube that is fine (it normalises to -14).
- `pixelate audio` renders one picture loop seeded so it repeats exactly. It checks the seam: audio after the loop must match the start, below -60 dB.
- Ambience beds and tape wobble are fitted automatically so they turn a whole number of times per loop.
- If you add a continuous sound source to the engine, it must do the same, or the seam check fails.
- Keep every stereo source out of the per-voice panners, or mono voices sharing that panner jump 3 dB louder. The engine's riser goes straight to the bus input for this reason.
