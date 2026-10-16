#!/usr/bin/env bash
# The CLI half of the gallery: the same work an agent does, typed by hand.
# Run from anywhere: demo/cli_demo.sh   (a few minutes; needs ffmpeg for the MP4s)
set -euo pipefail
cd "$(dirname "$0")/.."
px() { python3 ./pixelate "$@"; }

# ---- plan a palette: hue-shifted ramps, one per material, with a swatch sheet
px palette ramps sea=#1d3a5f snow=#dfe8f2 lamp=#f2a541 pine=#2e5a4a aurora=#3fd49a \
   --steps 7 --shift 24 -o examples/gallery/palettes/winter-night

# ---- render scenes: PNG, @Nx PNG, GIF and MP4 into each pack's out/
px assets examples/retro           # Rooftop Run, Island Village, Pixel Harbor

# ---- hold a screen to its console's limits
px era examples/retro/out/rooftop_run.png --era nes
px era examples/retro/out/island_village.png --era gameboy
