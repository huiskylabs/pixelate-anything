# evals: does the skill beat a bare model?

This harness runs exploratory pairs. It does not prove that the skill wins. The ten bundled prompts come from `examples/moments`, whose answers are in this repository. Use them for dry runs, not comparisons. Live runs require prompts outside this checkout. The runner rejects exact copies of bundled prompts. A human must check for paraphrases and prior exposure.

## Arms and contract

- **bare**: the model with a shell and Python (Pillow, numpy, ffmpeg); no skill.
- **skill**: the same model and deliverable contract, told to use a filtered snapshot of the kit. The snapshot omits `examples/moments`, `evals`, `docs` and `tests` so prior answers and maintainer notes are not in the advertised kit.

Both arms get the same prompt, deliverable contract, timeout and per-run spend ceiling. The contract requires `out/a.png`, `out/b.png` and `out/sample.wav`. The runner does **not** sandbox the agent, enforce a token cap or prove that a prompt is unseen. For a defensible comparison, isolate each agent and pin the model and tools. Only the skill should differ. If you pass `--refs`, provide `NN.jpg` for **every selected task**. The runner now rejects missing files before either arm starts. For reference-dependent tasks, do not omit `--refs`.

## Running

    python3 evals/run.py --tasks 01,05,08        # bundled dry run only
    python3 evals/run.py --prompts /outside/held-out --refs /outside/refs --budget-usd 5 --go
    python3 evals/score.py evals/runs/<stamp>   # diagnostic scores, not a winner
    python3 evals/score.py evals/runs/<stamp> --critique  # model grades cost extra

Live runs require `--prompts` and a positive `--budget-usd`. The default `claude -p` command receives `--max-budget-usd`. A custom `--agent-cmd` must contain one `{budget_usd}` placeholder. Its wrapper must enforce the ceiling at the provider. The runner cannot verify that a custom wrapper honors it. Runs cost money. Get approval before using `--go`. Use a fresh `--out` for each run. It holds the filtered `_kit` and agent workspaces. Count setup, queueing and critic costs when comparing the arms.

`meta.json` records reported input, output and cache tokens, plus total tokens when usage is complete. It also records cost, wall time, model command, kit revision and spend ceiling. Missing usage is **unknown**, not zero. A dollar ceiling does not enforce an equal token limit. If the experiment needs equal tokens, enforce the limit through the provider and retain its configuration.

## Reading results

`score.py` checks delivered files, judge warnings and audio format and peak. With `--critique`, it copies each frame to an arm-neutral temporary path before a model critic sees it. A model grade is not independent human preference. An empty image may have no judge defects. The skill arm also uses that judge, so its defect count is not an independent quality rating. Use blind human pairwise ratings of brief fit, readability, composition and pixel craft. Check technical legality and exports separately. Predeclare a win as better human-rated art without a material cost regression, **or** non-inferior art in less time and fewer tokens. Report failures and uncertainty. Do not pick a winner from three pairs or detector counts.

## Status

The harness and fake-agent tests exist. **No paid skill-vs-bare run or human study has been performed.** An image-generation arm needs an equal usable-asset contract and full cost accounting. It is not equivalent to these two code-drawing arms by default.
