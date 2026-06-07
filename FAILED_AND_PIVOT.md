# Failed and Pivoted: Root

We gave up on this as a from-scratch game-generation path. The files in this
root still show the abandoned architecture so future work can reuse the parts
that survived without repeating the same experiment.

## Why this is here

Amazing Digital Pet Dentures tried to make Nemotron 3 Nano agents generate
complete, playable single-file HTML games from a chat prompt. The intended flow
was: `app.py` takes the user's vibe, `agents.py` runs the Nemotron 3 Nano path
through a llama.cpp-compatible endpoint, the model writes or edits an `.html`
file in `adventures/`, and the Gradio UI renders the touched file in an iframe
using `srcdoc`.

The model server path in `modal_app.py` worked well enough as infrastructure:
Nemotron is served through llama.cpp's `llama-server` on Modal, using
`MODEL_QUANT = "Q8_0"`, `GPU = "L40S"`, `--reasoning-budget 0`, and `-c 65536`.
The app can also point at another OpenAI-compatible llama.cpp endpoint with
`LLAMACPP_BASE_URL`.

## What we tried

- Multi-agent coordination was replaced by the current single-agent path because
  coordination overhead did not improve game quality.
- Tool/file delivery was tried, but the small model's tool channel was fragile.
  We hit failures such as `unsupported content[].type`, worked around media
  artifact issues with `send_media_to_model=False`, and saw tool calls leak as
  plain text in some trials.
- We moved to `CodingTools` in `agents.py`, scoped to `adventures/`, so the
  agent could `write_file`, `read_file`, and `edit_file`.
- We added Traditional RAG: LanceDB plus a local MiniCPM embedder from
  `requirements.txt`, with `search_knowledge=False` and
  `add_knowledge_to_context=True`.
- We raised llama.cpp context after a real request failed with
  `request (20361 tokens) exceeds the available context size (16384 tokens)`.

## Why it failed

The primary failure was model capability, not plumbing. A roughly 3B-active-param
model could apply isolated code patterns, but it could not reliably design a
coherent, themed, finished game from scratch. Bigger context, Q8, disabled
reasoning, stricter prompts, RAG, and full examples did not fix that.

The checked-in `adventures/space_adventure.html` is the clearest artifact: it has
a tiny 8 by 6 tile map in a huge canvas, mixed maze/shooter/survival/timer
mechanics, pointer-lock style movement in a small 2D room, `alert()`/reload flow,
a displayed score that does not meaningfully change, and an incoherent goal
coordinate on the wall row.

## Pivot

Keep the working pieces: llama.cpp serving, Gradio iframe rendering, the
adventures folder, and the reusable examples. Stop asking this model to architect
games from nothing. The next direction is template remixing/retheming/tuning
using known-working HTML games, and/or evaluating a code-specialized Nemotron
sibling such as Nemotron-Cascade-2-30B-A3B.
