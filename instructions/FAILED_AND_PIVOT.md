# Failed and Pivoted: Instructions

We gave up on this as a from-scratch game-generation path. The prompt in
`adventure_engineer.py` remains here as historical scaffolding and possible
source material for a template-remix pivot, not as the current product direction.

## Why this is here

`adventure_engineer.py` contains the system prompt for the Nemotron 3 Nano
agent path. It tried to make a small Nemotron model act as both game designer
and implementer: talk through a vibe, pitch a concept, then write or edit a
complete single-file Canvas/three.js game through `CodingTools`.

## What we tried

- We tried direct prompting for original game design.
- We tried an inline gold example. That backfired: outputs became clones or
  reskins of the example instead of new games.
- We removed the gold example and added stronger rules: build one complete HTML
  document, use a single game loop, render every entity, handle resize, avoid
  duplicate identifiers, and use the correct `three/addons/` importmap key.
- We added the explicit "ADAPT, DON'T CLONE" instruction after adding compact
  examples to the knowledge base.
- We added concrete code gotchas because generated games repeatedly produced
  blank screens, empty scenes, bad imports, and loop/control mistakes.

## Why it failed

The prompt could reduce specific syntax and browser mistakes, but it could not
turn the model into a reliable game architect. The model often combined several
half-mechanics instead of building one coherent loop, or followed examples too
closely. Prompt pressure helped local code shape more than game design quality.

## Pivot

Future prompts should assume there is already a working game template. The model
should retheme, tune, rebalance, rename, and make bounded edits to a known-good
HTML game instead of inventing the engine and mechanics from scratch.
