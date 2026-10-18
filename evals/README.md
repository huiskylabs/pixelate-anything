# evals: does the skill beat a bare model?

This harness is for exploratory paired runs, not a proof that the skill wins. The ten bundled prompts are derived from `examples/moments`; their answers are available in the repository and **must not be used for a comparative claim**. Dry runs can list them, but `--go` requires a separate, held-out prompt directory outside this checkout. Exact copies of bundled prompts are rejected; a human must also check for paraphrases or other prior exposure.

## Arms and contract

- **bare**: the model with a shell and Python (Pillow, numpy, ffmpeg); no skill.
- **skill**: the same model and deliverable contract, told to use a filtered snapshot of the kit. The snapshot omits `examples/moments`, `evals`, `docs` and `tests` so prior answers and maintainer notes are not in the advertised kit.

Both get the same prompt, requested `out/a.png`, `out/b.png` and `out/sample.wav`, timeout and per-run provider spend ceiling. The harness does **not** sandbox the agent's filesystem, enforce a token cap, or prove the prompt is genuinely unseen. Run agents in isolated environments for a defensible comparison, with identical tool access apart from the skill and pinned model/provider. Supply reference images as `NN.jpg` files in a `--refs` directory for tasks that require them; confirm that both arms receive the same file. Do not run a reference-dependent prompt without its photo.

## Running

    python3 evals/run.py --tasks 01,05,08        # bundled dry run only
    python3 evals/run.py --prompts /outside/held-out --refs /outside/refs --budget-usd 5 --go
    python3 evals/score.py evals/runs/<stamp>   # diagnostic scores, not a winner
    python3 evals/score.py evals/runs/<stamp> --critique  # model grades cost extra

With `--go`, `--prompts` and a positive `--budget-usd` are required. The default `claude -p` command receives `--max-budget-usd`; custom `--agent-cmd` commands must include one `{budget_usd}` placeholder and their wrapper must enforce it at the provider. The harness cannot independently verify that an arbitrary wrapper honours the cap. Runs are sequential and cost real money; get approval before using `--go`. Use a fresh `--out` per run: it contains the filtered `_kit` and run workspaces. Setup, queueing and any external critic costs must also be reported when comparing total cost.

`meta.json` records reported input/output/cache tokens, total tokens when both input and output usage are present, cost, wall time, model command, kit revision and ceiling. Missing usage is **unknown**, not zero. A dollar ceiling is not an equal token ceiling; if equal tokens are the experimental constraint, enforce them through the provider/wrapper and retain its configuration as evidence.

## Reading results

`score.py` checks delivered files, judge warnings and audio format/peak. With `--critique`, it copies each frame into a randomized arm-neutral temporary path before showing it to a model critic. This removes the arm label from the shown image path, but a model grade is not independent human preference. Judge defects are diagnostic: an empty image may have none, and the skill arm is trained to respond to that judge. Use held-out blind human pairwise ratings of brief fit, readability, composition and pixel craft, plus technical legality and valid exports. Predeclare success: better human-rated art without a material cost regression, **or** non-inferior art in less time and fewer tokens. Include failures and uncertainty; do not choose a winner from three pairs or from detector counts.

## Status

The harness and fake-agent tests exist. **No paid skill-vs-bare run or human study has been performed.** For a broader product comparison, an image-generation arm needs an explicit, equal usable-asset contract and full cost accounting; it is not silently equivalent to these two code-drawing arms.
