# Knowledge base — `game-patterns.txt`

`game-patterns.txt` is the agent's game-development knowledge base: a lean, code-forward
reference of single-file HTML game patterns (game loop, canvas + DPR sizing, input,
collision, physics, entities, HUD, tilemaps, audio, a minimal three.js boilerplate, and a
GOTCHAS list). ~14.8 KB / ~3.7K tokens, 14 sections.

## Where it came from
It was **distilled** from the vendored `game-engine` skill in
[`../skills/game-engine/`](../skills/game-engine/), which is itself vendored from the
[`github/awesome-copilot`](https://github.com/github/awesome-copilot) repository (credit and
license noted in [`../skills/README.md`](../skills/README.md)). We kept only the ~20% that
helps a small model write **single-file, no-build** browser games (raw Canvas 2D + three.js
via CDN importmap) and dropped the rest (publishing/marketing, glossary, architecture
essays, Phaser/Babylon/A-Frame, Haxe, multi-file project tooling).

## How the agent uses it (Traditional RAG)
`agents.py` embeds this file into a **LanceDB** vector store (`db/lancedb/`) with a local
`sentence-transformers` embedder, and the agent runs **Traditional RAG**
(`search_knowledge=False`, `add_knowledge_to_context=True`): the patterns relevant to each
request are searched and injected straight into the prompt — the model never calls a search
tool to fetch them.

## Editing / regenerating
- Edit `game-patterns.txt` directly to change what the model gets.
- After editing, **delete `db/lancedb/`** so the patterns are re-embedded on next startup
  (insertion uses `skip_if_exists=True`, so unchanged content is not re-embedded).
- Keep it lean — it shares the model's 16K-token context window with chat history and the
  game it has to generate.
