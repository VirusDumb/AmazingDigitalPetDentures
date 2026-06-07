# Failed and Pivoted: Knowledge

We gave up on this as a from-scratch game-generation path. The files in this
directory remain useful, but mainly as reusable template/reference assets for
the pivot.

## Why this is here

`game-patterns.txt` is the distilled game-development knowledge base. It was
created from the vendored `skills/game-engine/` material and later expanded with
10 compact complete HTML exemplars in `examples/`.

`agents.py` loads this material through Traditional RAG: LanceDB, a local
MiniCPM embedding model, `search_knowledge=False`, and
`add_knowledge_to_context=True`. That avoided making the small model call a
knowledge-search tool during the game-generation turn.

## What we tried

- We distilled the large game-engine skill down to single-file browser-game
  patterns: game loop, Canvas sizing, input, collision, tilemaps, HUD, audio,
  and three.js boilerplate.
- We moved from tool-based retrieval to auto-injected RAG to reduce tool-call
  fragility.
- We added 10 complete exemplars:
  `top-down-racer`, `pseudo-3d-racer`, `canvas-platformer`, `snake`, `tetris`,
  `sokoban`, `raycaster-fps`, `three-space-flight`, `canvas-space-shooter`, and
  `three-obstacle-runner`.
- We added header-aware chunking in `agents.py` so examples and pattern sections
  stayed coherent instead of being split arbitrarily.

## Why it failed

RAG gave the model better local patterns, but it did not solve the design
problem. Code is a weak semantic retrieval target compared with prose: matching
the user's genre to the right implementation pattern was noisy. Even when a good
example was injected, the model either cloned too much or mixed incompatible
mechanics.

The dependency cost was also high: `requirements.txt` had to carry LanceDB,
`sentence-transformers`, `transformers==4.57.6`, `tiktoken`, `sentencepiece`,
`protobuf`, and `einops` just to support the embedder stack.

## Pivot

Treat `examples/*.html` as working templates/assets, not merely few-shot prompt
context. The next approach should select a known-good game and let the model
retheme, adjust, and polish it within bounded edit surfaces.

