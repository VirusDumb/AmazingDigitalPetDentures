> **Abandoned path:** We gave up on this as a from-scratch game-generation path.
> This skill material remains here as reference/source material for the pivot;
> it is not the current runtime plan.

# Skills — attribution

## `game-engine/`

The `game-engine/` skill (its `SKILL.md`, `references/`, and `assets/`) is **vendored
from the [`github/awesome-copilot`](https://github.com/github/awesome-copilot) repository**
(the community collection of Copilot customizations — skills, chat modes, instructions,
and prompts). All credit for that material goes to the awesome-copilot project and its
contributors. It is used here under that repository's license (MIT at the time of
vendoring — see the upstream `LICENSE`).

### How we use it
We did **not** wire this skill into the agent at runtime. Instead we **distilled** it down
to the ~20% that helps a small model generate single-file HTML games from scratch — see
[`../knowledge/game-patterns.txt`](../knowledge/game-patterns.txt) and
[`../knowledge/README.md`](../knowledge/README.md). The distilled patterns are what the
agent actually retrieves (Traditional RAG over LanceDB; see `agents.py`).

This folder is kept as the **source of truth** for that distillation — if we ever want to
re-distill or pull more patterns, this is where they come from. It is not loaded by the app.
