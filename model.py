"""In-process model layer for the HTML Toy Maker — runs Nemotron on HF ZeroGPU.

The Gradio app calls `generate(messages)`; that function is wrapped in `@spaces.GPU`,
so the GPU is only attached while it runs (ZeroGPU). The big GGUF DOWNLOAD does not need
the GPU, so we kick it off in a background thread at import time (overlapping Space boot).
The model is then constructed INSIDE the GPU function the first time and cached in a module
global — so the first request only pays for model load + generation, not the download.

Constraints: NVIDIA Nemotron (RTX 5080 prize) on the llama.cpp runtime (Llama Champion),
Q8_0 quant, n_ctx = 65536. Set a HF_TOKEN Space secret for faster, rate-limited-free pulls.

⚠️ If `Llama(...)` raises an "unknown architecture" / GGML assert on load, the prebuilt
llama-cpp-python wheel is older than Nemotron-3-Nano's hybrid Mamba-2 support — bump the
wheel in requirements.txt or build from source.
"""

import os

# Must be set BEFORE huggingface_hub is imported, so the fast Rust downloader is used.
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

import glob
import threading

import spaces
from llama_cpp import Llama

# Nemotron-3-Nano-30B-A3B, Q8_0 (~33.6 GB). Q8_0 may be sharded into *-00001-of-0000N.gguf;
# we download all matching shards and point llama.cpp at the first (it auto-loads the rest).
MODEL_REPO = "unsloth/Nemotron-3-Nano-30B-A3B-GGUF"
QUANT_GLOB = "*Q8_0*.gguf"
# Full trained context (n_ctx_train = 1,048,576). Nemotron-3-Nano is hybrid Mamba-2: only its
# few attention layers grow KV with context (Mamba layers are constant-size), so long context
# is cheap here. Q8_0 (~34 GB) leaves ~36 GB free on ZeroGPU's ~70 GB H200 for the KV cache.
# (llama.cpp allocates KV up front from this — if it ever OOMs at load, dial this back.)
N_CTX = 1048576

# Unsloth's recommended Nemotron sampling.
DEFAULTS = dict(temperature=0.6, top_p=0.95, min_p=0.01)

_llm: Llama | None = None
_model_path: str | None = None
_download_error: Exception | None = None


def _download() -> None:
    """Fetch the GGUF shards (CPU only). Runs in a background thread started at import."""
    global _model_path, _download_error
    try:
        from huggingface_hub import snapshot_download

        local_dir = snapshot_download(MODEL_REPO, allow_patterns=[QUANT_GLOB])
        shards = sorted(glob.glob(os.path.join(local_dir, "**", QUANT_GLOB), recursive=True))
        if not shards:
            raise RuntimeError(f"No {QUANT_GLOB} files found in {MODEL_REPO}")
        _model_path = shards[0]  # first shard; llama.cpp loads the rest of a split GGUF itself
    except Exception as exc:  # surfaced when _load() is first called
        _download_error = exc


# Start downloading immediately at import (overlaps Space startup; does NOT block it, so the
# port binds fast and ZeroGPU registers the GPU function right away).
_download_thread = threading.Thread(target=_download, name="gguf-download", daemon=True)
_download_thread.start()


def _load() -> Llama:
    """Construct the llama.cpp model (GPU attached), cached for reuse across requests."""
    global _llm
    if _llm is not None:
        return _llm

    _download_thread.join()  # wait for the background download (instant if already done)
    if _model_path is None:
        raise RuntimeError(f"GGUF download failed: {_download_error}")

    _llm = Llama(
        model_path=_model_path,
        n_gpu_layers=-1,        # offload everything to the GPU
        n_ctx=N_CTX,
        flash_attn=True,
        verbose=False,
    )
    return _llm


@spaces.GPU(duration=300)
def generate(messages: list[dict], max_tokens: int = 8192, **sampling) -> dict:
    """Run one chat completion. Returns {"content", "reasoning"}.

    Nemotron emits its chain-of-thought via <think>/</think> SPECIAL tokens (ids 12/13),
    which are dropped on detokenize — so reasoning usually arrives mixed into `content`.
    Newer llama.cpp may surface it separately as `reasoning_content`; we pass both back and
    let app.py split them for display.
    """
    llm = _load()
    params = {**DEFAULTS, **sampling}
    out = llm.create_chat_completion(messages=messages, max_tokens=max_tokens, **params)
    msg = out["choices"][0]["message"]
    return {
        "content": (msg.get("content") or "").strip(),
        "reasoning": (msg.get("reasoning_content") or "").strip(),
    }
