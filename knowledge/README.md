# Knowledge base — `game-patterns.txt`

`game-patterns.txt` is the agent's game-development knowledge base: a code-forward
reference of single-file HTML game patterns plus compact complete exemplars (game loop,
canvas + DPR sizing, input, collision, physics, entities, HUD, tilemaps, audio, a minimal
three.js boilerplate, GOTCHAS, and 10 playable genre examples). ~49 KB / ~12.3K tokens.

## Where it came from
It was **distilled** from the vendored `game-engine` skill in
[`../skills/game-engine/`](../skills/game-engine/), which is itself vendored from the
[`github/awesome-copilot`](https://github.com/github/awesome-copilot) repository (credit and
license noted in [`../skills/README.md`](../skills/README.md)). We kept only the ~20% that
helps a small model write **single-file, no-build** browser games (raw Canvas 2D + three.js
via CDN importmap) and dropped the rest (publishing/marketing, glossary, architecture
essays, Phaser/Babylon/A-Frame, Haxe, multi-file project tooling).

## Complete compact exemplars
The `Complete Compact Game Exemplars` section gives the small model concrete games to
imitate when patterns alone are not enough. Standalone copies live in `examples/` so they
can be opened and tested directly:

- `top-down-racer.html`
- `pseudo-3d-racer.html`
- `canvas-platformer.html`
- `snake.html`
- `tetris.html`
- `sokoban.html`
- `raycaster-fps.html`
- `three-space-flight.html`
- `canvas-space-shooter.html`
- `three-obstacle-runner.html`

Each exemplar is intentionally compact: one HTML file, inline CSS/JS, no build step,
visible HUD, working controls, actual mechanics, and retry/win/lose behavior.

## How the agent uses it (Traditional RAG)
`agents.py` embeds this file into a **LanceDB** vector store (`db/lancedb/`) with a local
`sentence-transformers` embedder, and the agent runs **Traditional RAG**
(`search_knowledge=False`, `add_knowledge_to_context=True`): the patterns relevant to each
request are searched and injected straight into the prompt — the model never calls a search
tool to fetch them.

## Editing / regenerating
- Edit `game-patterns.txt` directly to change what the model gets.
- If an exemplar changes, update both `game-patterns.txt` and the matching file in
  `examples/`.
- After editing, **delete `db/lancedb/`** so the patterns are re-embedded on next startup
  (insertion uses `skip_if_exists=True`, so unchanged content is not re-embedded).
- Keep examples compact — retrieved chunks share the model's context window with chat
  history and the game it has to generate.
