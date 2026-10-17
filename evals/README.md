# evals: does the skill beat a bare model?

The claim to prove (docs/PLAN-moat.md, workstream 4): given the same long prompt, an agent with the
pixelate-anything skill delivers a better result, faster, than the same model without it.

## Corpus

`prompts/01..10-*.md` are the ten showcase requests from `examples/moments`, written as the
user would send them. The rebuild tasks expect a reference photo: put `NN.jpg` files in a folder and
pass `--refs DIR`; each one is copied into its run's workspace as `reference.jpg`.

## Arms

- **bare**: the model with a shell and Python (Pillow, numpy, ffmpeg); no skill.
- **skill**: the same model, told where the kit is and to follow its `SKILL.md`.

Both get the same prompt, the same deliverable contract (`out/a.png`, `out/b.png`, `out/sample.wav`),
the same timeout and no human coaching. The steps that ask the user to confirm are skipped.

## Running

    python3 evals/run.py --tasks 01,05,08                # dry run: prints the plan, runs nothing
    python3 evals/run.py --tasks 01,05,08 --go           # the pilot: 3 prompts x 2 arms x 1 run
    python3 evals/score.py evals/runs/<stamp>            # judge, sample checks, per-arm summary
    python3 evals/score.py evals/runs/<stamp> --critique # plus blind art-director grades (tokens)

The agent command defaults to `claude -p --output-format json --permission-mode bypassPermissions`
(set `--agent-cmd` or `PIXELATE_EVAL_AGENT` to use another). It reads the prompt on stdin and runs in
the workspace; when it prints JSON usage, tokens and cost go into `meta.json`.

Each run is a full agent session: the pilot costs real tokens. `evals/runs/` is not committed.

## What is measured

Per run: delivered files, wall time, output tokens, cost, turns, `pixelate judge` defects and
severity on both stills, the sample's length, peak and clipping, and (with `--critique`) a grade from
an art director who does not know which arm made the image. Both arms are scored by the same tools.
The judge was calibrated on accepted art, not on either arm's output.

## Status

The harness is built and tested (`tests/test_evals.py`, using a fake agent). No benchmark has been
run yet. Re-run the pilot after each workstream lands and publish the paired results.
