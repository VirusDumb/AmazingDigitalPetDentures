# Failed and Pivoted: Skills

We gave up on this as a from-scratch game-generation path. The vendored
`game-engine/` skill remains here as reference/source material only.

## Why this is here

`game-engine/` was vendored from `github/awesome-copilot`. It contains broad game
development guidance, references, and templates for HTML5 Canvas, WebGL,
JavaScript, Phaser, Three.js, Babylon.js, A-Frame, publishing, terminology, and
other topics.

## What we tried

We tried treating this as a mandatory skill/tool chain: fetch the skill
instructions, fetch references or scripts, then build the game. That was too
many moving pieces for the small low-precision model. The agent often spent its
turn reasoning around the chain or failed to ship a playable game.

The current repo no longer loads this skill at runtime. `skills/README.md`
correctly says it was distilled into `knowledge/game-patterns.txt`, and the
agent uses Traditional RAG over that distilled file instead.

## Why it failed

The skill was too broad for the actual product constraint: one small model,
one turn, one complete no-build HTML game. It included useful material, but also
too much irrelevant surface area for publishing, alternate engines, architecture
essays, and multi-file workflows. As an active tool chain it reintroduced the
same fragility we were trying to remove.

## Pivot

Do not wire this skill back into the runtime by default. Use it only as source
material when deliberately re-distilling patterns or building a human-authored
template library.

