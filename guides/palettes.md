# Palettes

The palette is the mood, and pixel art lives or dies by it. `pixelate palette` builds,
extracts, shows and exports palettes.

```
pixelate palette list                                    presets (pico-8, sweetie-16, gameboy, the examples' palettes)
pixelate palette ramps sky=#3b5dc9 leaf=#5aa04a skin=#c8805f --steps 4 -o pal/mine
pixelate palette extract reference.png -n 16 -o pal/ref
pixelate palette show pico-8
pixelate palette js pal/mine.json --name dusk            a palettes.js entry for a scene
```

`-o BASE` writes:
- `BASE.hex`
- `BASE.gpl` (GIMP, Aseprite, Krita)
- `BASE.json` (`{slot: hex}`, used by asset packs)
- `BASE.png` (1 px per colour; Aseprite loads it as a palette)
- `BASE-swatch.png` (labelled, for looking at)

## Building one from a brief

1. **List the materials** the art needs:
   - sky
   - water
   - foliage
   - skin
   - hair
   - cloth (one per garment colour)
   - wood
   - stone
   - metal
   - an accent or two
   - one outline colour
2. **Pick one base colour per material** that fits the mood:
   - A warm dusk pushes everything toward orange and violet.
   - A cold night pushes toward teal and blue.
   - A storybook look uses saturated mid-tones.
   - Keep the base colours' brightness varied, so materials separate even in greyscale.
3. **Run `ramps`.** Each base becomes a ramp: darks drift toward blue-violet, lights toward warm yellow, and the base stays exact.
   - `--steps`: use 3-4 for small sprites and 5 for scenes.
   - `--shift`: raise it (30) for a painterly look, or lower it (10) for a natural one.
4. **Look at the swatch.**
   - Every ramp should read as one material lit from one side.
   - Neighbouring ramps should not collide: if leaf and grass are nearly the same, shift one.
5. **Add singles:**
   - one outline (a near-black with the scene's hue, never #000)
   - one near-white highlight
   - accents used sparingly
6. **Count.** Keep it to 16-32 colours for a sprite pack and 40-80 for a full scene with several moods.

## Several moods (scenes with phases)

Keep slot names identical across moods and change only the colours: `F2` is "roof, mid tone" at dusk and in the rain.
Then one sprite works in every mood, and the dissolve between moods stays coherent.

Build the first mood's palette, then derive the others. Shift the whole set's hue and lightness toward the new light, rather than picking colours from scratch.

## From a reference

`extract` clusters the image in OKLab (perceptual), so small saturated accents survive.
Use it to match an existing game or artwork, or to start from a photo's mood.
Then prune near-duplicates and rebuild weak areas with `ramps`.

## Rules

- Avoid pure black and pure white: the darkest tone carries the scene's hue.
- Shift hue along each ramp; don't only change brightness. Shadows go cooler and lights warmer.
- Saturation peaks in the mid tones. Lights are slightly desaturated, and darks are rich but not neon.
- Test in greyscale: if two materials merge, change one's lightness.
