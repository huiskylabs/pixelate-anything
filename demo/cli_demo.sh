#!/usr/bin/env bash
# The CLI half of the gallery: the same work an agent does, typed by hand.
# Run from anywhere: demo/cli_demo.sh   (a few minutes; needs ffmpeg for the MP4s)
set -euo pipefail
cd "$(dirname "$0")/.."
px() { python3 ./pixelate "$@"; }

# ---- plan a palette: hue-shifted ramps, one per material, with a swatch sheet
px palette ramps ember=#e8562a gold=#f2c14e stone=#5b5470 steel=#8e9bb0 cape=#2f58b8 \
   --steps 7 --shift 24 -o examples/gallery/palettes/dragonfire

# ---- render scenes: PNG, @Nx PNG, GIF and MP4 into each pack's out/
px assets examples/dragon          # Dragonfire Keep, an original 16-bit boss fight
px assets examples/retro           # Rooftop Run, Island Village, Pixel Harbor

# ---- hold a screen to its console's limits
px era examples/retro/out/rooftop_run.png --era nes
px era examples/retro/out/island_village.png --era gameboy
