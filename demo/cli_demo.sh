#!/usr/bin/env bash
# The CLI half of the gallery: every image, palette and clip in examples/gallery/{image,sprites,swap,palettes,video}
# comes from these commands. Run from anywhere: demo/cli_demo.sh   (about 3 minutes on 2 cores)
set -euo pipefail
cd "$(dirname "$0")/.."
px() { python3 ./pixelate "$@"; }
S=examples/gallery/sources
G=examples/gallery
mkdir -p $G/image $G/sprites $G/swap $G/palettes

# ---- palettes: pulled from art, or built as hue-shifted ramps
px palette extract $S/starry_night.jpg -n 16 -o $G/palettes/starry-night
px palette extract $S/great_wave.jpg -n 12 -o $G/palettes/great-wave
px palette extract $S/elephant_sunset.jpg -n 10 -o $G/palettes/savanna-sunset
px palette ramps sky=#3b5dc9 roof=#b13e53 stone=#8b9bb4 leaf=#38b764 lamp=#ffcd75 water=#41a6f6 \
   --steps 5 --shift 24 -o $G/palettes/dusk-village

# ---- photos and paintings to pixel art
px image $S/great_wave.jpg       -o $G/image/great-wave.png      --width 160 --palette $G/palettes/great-wave.hex --scale 6
px image $S/starry_night.jpg     -o $G/image/starry-night.png    --width 160 --palette $G/palettes/starry-night.hex --scale 6
px image $S/elephant_sunset.jpg  -o $G/image/elephant-sunset.png --width 120 --colors 14 --dither ordered --scale 8
px image $S/surfer.jpg           -o $G/image/surfer.png          --width 96  --colors 12 --smooth 2 --scale 8
px image $S/balloons.jpg         -o $G/image/balloons.png        --width 128 --colors 14 --smooth 2 --scale 8
px image $S/peacock.jpg          -o $G/image/peacock.png         --width 96  --colors 16 --smooth 2 --scale 8
px image $S/tubingen.jpg         -o $G/image/tubingen.png        --width 160 --colors 16 --smooth 2 --scale 6
px image $S/sunrise_panorama.jpg -o $G/image/sunrise.png         --crop 0.3,0.3,0.4,0.4 --width 200 --colors 16 --dither ordered --scale 5
px image $S/cat.png              -o $G/image/cat-gameboy.png     --width 96  --palette gameboy --smooth 2 --scale 8
px image $S/astronaut.png        -o $G/image/astronaut-avatar.png --crop 0.22,0,0.48,0.48 --width 64 --colors 12 --scale 8

# ---- a photographed object becomes a game sprite: cut out the background, outline it
px image $S/butterfly.jpg -o $G/sprites/butterfly.png --cutout --outline --width 40 --colors 10 --scale 10
px image $S/moon.jpg      -o $G/sprites/moon.png      --cutout 0.15 --outline --width 32 --colors 6 --scale 10

# ---- one picture, six palettes (a fixed palette dithers the tones that fall between its colours)
px image $S/elephant_sunset.jpg -o $G/swap/sunset-own.png --width 120 --colors 14 --dither ordered --scale 4
for p in pico-8 endesga-32 sweetie-16 c64 gameboy; do
  px image $S/elephant_sunset.jpg -o $G/swap/sunset-$p.png --width 120 --palette $p --dither ordered --scale 4
done

