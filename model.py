"""In-process model layer for the HTML Toy Maker — runs Nemotron on HF ZeroGPU.

The Gradio app calls `generate(messages)`; that function is wrapped in `@spaces.GPU`,
so the GPU is only attached while it runs (ZeroGPU). We therefore build the llama.cpp
model INSIDE the function the first time and cache it in a module global. The first call
downloads the GGUF (~33 GB, cached afterward) and loads the model — expect ~1-2 min once,
then it's fast.

Constraints: NVIDIA Nemotron (RTX 5080 prize) on the llama.cpp runtime (Llama Champion),
Q8_0 quant, n_ctx = 65536.

⚠️ If `Llama(...)` raises an "unknown architecture" / GGML assert on load, the prebuilt
llama-cpp-python wheel is older than Nemotron-3-Nano's hybrid Mamba-2 support — bump the
wheel in requirements.txt or build from source.
"""

import os

# Must be set BEFORE huggingface_hub is imported, so the fast Rust downloader is used.
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

import glob

import spaces
from llama_cpp import Llama

# Nemotron-3-Nano-30B-A3B, Q8_0 (~33.6 GB). Q8_0 may be sharded into *-00001-of-0000N.gguf;
# we download all matching shards and point llama.cpp at the first (it auto-loads the rest).
MODEL_REPO = "unsloth/Nemotron-3-Nano-30B-A3B-GGUF"
QUANT_GLOB = "*Q8_0*.gguf"
N_CTX = 65536

# Unsloth's recommended Nemotron sampling.
DEFAULTS = dict(temperature=0.6, top_p=0.95, min_p=0.01)

_llm: Llama | None = None


def _load() -> Llama:
    """Download (once) + construct the llama.cpp model, cached for reuse. GPU must be attached."""
    global _llm
    if _llm is not None:
        return _llm

    from huggingface_hub import snapshot_download

    local_dir = snapshot_download(MODEL_REPO, allow_patterns=[QUANT_GLOB])
    shards = sorted(glob.glob(os.path.join(local_dir, "**", QUANT_GLOB), recursive=True))
    if not shards:
        raise RuntimeError(f"No {QUANT_GLOB} files found in {MODEL_REPO}")

    _llm = Llama(
        model_path=shards[0],   # first shard; llama.cpp loads the rest of a split GGUF itself
        n_gpu_layers=-1,        # offload everything to the GPU
        n_ctx=N_CTX,
        flash_attn=True,
        verbose=False,
    )
    return _llm


@spaces.GPU(duration=300)
def generate(messages: list[dict], max_tokens: int = 8192, **sampling) -> str:
    """Run one chat completion and return the assistant text. `messages` is OpenAI-style."""
    llm = _load()
    params = {**DEFAULTS, **sampling}
    out = llm.create_chat_completion(messages=messages, max_tokens=max_tokens, **params)
    return (out["choices"][0]["message"].get("content") or "").strip()
