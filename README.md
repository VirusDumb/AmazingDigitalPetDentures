---
title: AmazingDigitalPetDentures
emoji: 🔥
colorFrom: pink
colorTo: gray
sdk: gradio
sdk_version: 6.16.0
python_version: '3.13'
app_file: app.py
pinned: false
short_description: The Amazing Digital Pet Dentures feeds on your Adventures
---

# 🦷 Amazing Digital Pet Dentures

A circus-themed **game generator**. You chat a vibe or an idea, and a single AI agent
(NVIDIA **Nemotron**, served through an OpenAI-compatible **llama.cpp** endpoint) writes a
complete, **fully playable 2D/3D HTML game** that renders live in the app — right next to
the chat.

Built for the **Build Small Hackathon**.

> ℹ️ **Hugging Face note:** the `---` block at the very top of this file is the Space
> config. **Do not delete it** — it tells the Space how to run. Everything below it is just
> this page.

---

## How it works (architecture)

| File | Role |
|---|---|
| `app.py` | Gradio UI: chat + the adventure window (renders games in an `<iframe>`), per-browser history |
| `agents.py` | The single **Adventure Engineer** agent + its model + a SQLite history db |
| `instructions/adventure_engineer.py` | The agent's system prompt (build original, playable worlds) |
| `skills/game-engine/` | An Agno **skill** (game-dev references/templates) the agent must consult every turn |
| `modal_app.py` | Serves Nemotron on a Modal GPU via `llama-server` (the cloud backend) |

The model backend is chosen by **one env var** (`LLAMACPP_BASE_URL`) — point it at a local
`llama-server` or at a Modal URL, no code change.

---

## Prerequisites

- **git**
- **Python 3.13**
- **[uv](https://docs.astral.sh/uv/)** (fast Python package manager)

---

## Step 1 — Pick your model backend

Choose based on your hardware:

### Option A — Run it locally (powerful machine)

Use this if you have a **Mac with ≥ 32 GB unified RAM**, **or** a GPU with **≥ 24 GB VRAM**
(e.g. RTX 4090 / 5090). The model weights are ~23 GB.

1. **Install llama.cpp** — follow the official guide:
   👉 https://github.com/ggml-org/llama.cpp
   (macOS: `brew install llama.cpp`. Windows/Linux: see the repo's install/build docs.)

2. **Start the model server** (first run downloads the GGUF automatically):
   ```bash
   llama-server -hf unsloth/Nemotron-3-Nano-30B-A3B-GGUF:UD-Q4_K_XL \
     --jinja --temp 0.6 --top-p 0.95 --min-p 0.01 -c 16384 -ngl 99 --port 8080
   ```

3. In your `.env` (see Step 3):
   ```
   LLAMACPP_BASE_URL=http://localhost:8080/v1
   LLAMACPP_API_KEY=sk-no-key
   LLM_MODEL_ID=nemotron
   ```

### Option B — Use Modal (everyone else)

No big GPU? Serve the **same** Nemotron on a cloud GPU using Modal's **free hackathon
credits**. Full details are documented in the header of `modal_app.py`; the short version:

1. Install the dev deps (adds `modal`) and log in:
   ```bash
   uv pip install -r requirements-dev.txt
   modal token new
   ```
2. Create the API-key secret once (pick any long private value):
   ```bash
   modal secret create adpd-llama LLAMA_API_KEY=sk-pick-something-long
   ```
3. Deploy and copy the printed URL:
   ```bash
   modal deploy modal_app.py
   ```
4. In your `.env`:
   ```
   LLAMACPP_BASE_URL=https://<your-workspace>--adpd-llama-serve.modal.run/v1
   LLAMACPP_API_KEY=sk-pick-something-long
   LLM_MODEL_ID=nemotron
   ```
   > The first request cold-starts the GPU and downloads ~23 GB (≈10–15 min). After that
   > it's fast, and it scales to **$0** when idle.

---

## Step 2 — Set up the environment (uv)

```bash
uv venv --python 3.13
# Activate it:
#   Windows (PowerShell):  .venv\Scripts\activate
#   macOS / Linux:         source .venv/bin/activate

uv pip install -r requirements.txt        # use requirements-dev.txt if you're deploying Modal
```

## Step 3 — Configure `.env`

```bash
cp .env.example .env      # Windows: copy .env.example .env
```
Fill it in with the values from the backend you chose in Step 1.

## Step 4 — Run it

```bash
python app.py
```
Open the local URL it prints (usually http://127.0.0.1:7860), type a game idea into the
chat, and watch the adventure window build and render your game.

---

## For the team (remotes & deploy)

This repo has two remotes:

- **`origin`** → GitHub (source of truth — commit/push here, GitHub Desktop works on this).
- **`hf`** → the Hugging Face Space. Deploy the app with:
  ```bash
  git push hf main
  ```
- **Modal** hosts the GPU model backend (`modal deploy modal_app.py`), separate from the app.

Secrets live in `.env` locally (gitignored) and in **Space Settings → Secrets** on HF —
never commit them.

### Troubleshooting

- **Modal first call is slow** — that's the one-time cold-start download; later calls are fast.
- **Games come out broken / repetitive** — use a higher-precision backend (the local Nano,
  or a stronger Nemotron); aggressive quantization hurts code quality.
- **History "forgets" on the Space** — Space disk is ephemeral, so `adpd.db` resets on
  restart. Fine locally; for durable Space persistence, move the db to a Volume/Dataset.

---

## Credits & Inspiration

The talking-dentures mascot is a loving **fan tribute to Caine**, the ringmaster from
**[*The Amazing Digital Circus*](https://www.youtube.com/@GlitchProductions)** by **Glitch
Productions**. This is an independent, non-commercial fan project — it is **not** affiliated
with, endorsed by, or sponsored by Glitch Productions or the show's creators, and is **not**
intended to copy, plagiarize, or infringe on their work. All rights to *The Amazing Digital
Circus* and its characters belong to their respective owners. 💛
