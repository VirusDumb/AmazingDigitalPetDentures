"""
modal_app.py — serves NVIDIA Nemotron-3-Nano-30B-A3B via llama.cpp's `llama-server`
on a Modal GPU, exposing an OpenAI-compatible endpoint.

This is the FAST dev/demo backend. The Gradio app / agents never import modal — they
point `LLAMACPP_BASE_URL` at the URL this prints and set `LLAMACPP_API_KEY` to the
secret. (Keeps the 🦙 Llama Champion badge — the model runs on the llama.cpp runtime —
but it's a cloud call, so it does NOT count for 🔌 Off-the-Grid. Known tradeoff.)

Built on Modal's official LLM-serving pattern (https://modal.com/docs/examples/llm_inference
and /vllm_inference): the same `@app.function` → `@modal.concurrent` → `@modal.web_server`
stack that works for vLLM works for llama-server (confirmed by the Modal team). We just
launch `llama-server` as the subprocess instead of `vllm serve`.

────────────────────────────────────────────────────────────────────────────────────────
DEPLOY (run these yourself; the venv has modal + you're authenticated as soumyaray532):

  1. Create the API-key secret ONCE (pick any long private value):
       modal secret create adpd-llama LLAMA_API_KEY=sk-pick-something-long

  2. Smoke-test end-to-end on an ephemeral container (cold start downloads ~23 GB once):
       modal run modal_app.py

  3. Deploy the persistent endpoint:
       modal deploy modal_app.py

  4. Modal prints a URL like:  https://<workspace>--adpd-llama-serve.modal.run
     Put these in your local .env (and later in the Space secrets):
       LLAMACPP_BASE_URL = https://<workspace>--adpd-llama-serve.modal.run/v1
       LLAMACPP_API_KEY  = <the LLAMA_API_KEY you chose>
       LLM_MODEL_ID      = unsloth/Nemotron-3-Nano-30B-A3B   # must match --alias below
────────────────────────────────────────────────────────────────────────────────────────
VERIFIED 2026-06-06 (don't trust memory — these were checked against the live repo/docs):
  - GGUF tag `UD-Q4_K_XL` exists as a SINGLE (un-split) file in
    unsloth/Nemotron-3-Nano-30B-A3B-GGUF, size ≈ 22.8 GB. `-hf repo:QUANT` downloads it.
  - Unsloth's recommended llama-server flags: --temp 0.6 --top-p 0.95 --min-p 0.01
    --ctx-size 16384 (https://unsloth.ai/docs/models/nemotron-3).
  - Nemotron 3 is a HYBRID MAMBA-2 model → needs a RECENT llama.cpp build. The rolling
    `:server-cuda` image tag (pulled fresh at Modal image-build time) is current and runs
    it. If you ever hit `mamba-base.cpp ... GGML_ASSERT` (ggml-org/llama.cpp#20570),
    the image is stale — force a rebuild or pin a newer image tag.
  - UPGRADE PATH (parked): bartowski/nvidia_Nemotron-Cascade-2-30B-A3B-GGUF:Q5_K_M
    (≈26.2 GB) is a near drop-in with much stronger codegen (LiveCodeBench 68→87). Swap
    MODEL_REPO/MODEL_QUANT/MODEL_ALIAS + sampling temp=1.0/top_p=0.95 and bump -c to 32768.

GPU SIZING (the bug in the previous version): the quant is 22.8 GB and 4-bit needs
~24 GB, so it does NOT safely fit a 24 GB L4 once you add the KV cache + CUDA compute
buffers → OOM at load. We use an L40S (48 GB) for comfortable headroom and full GPU
offload. The Mamba-2 state is constant-size, so large context stays cheap. To cut cost
you can try gpu="A100-40GB", but do NOT drop back to "L4" with this quant.
"""

import modal

MIN = 60  # seconds

# ---- Config ----
MODEL_REPO = "unsloth/Nemotron-3-Nano-30B-A3B-GGUF"
MODEL_QUANT = "UD-Q4_K_XL"                       # ≈ 22.8 GB, single file. VERIFIED on Files tab.
MODEL_ALIAS = "unsloth/Nemotron-3-Nano-30B-A3B"  # the model id llama-server reports / Agno sends
PORT = 8080
GPU = "L40S"                                      # 48 GB — fits the 22.8 GB quant + buffers

# The official ggml image puts the binary at /app/llama-server; we also check PATH so an
# image layout change won't silently break the launch.
LLAMA_SERVER_CANDIDATES = ("/app/llama-server", "/llama-server", "/usr/bin/llama-server")

app = modal.App("adpd-llama")

# Prebuilt llama.cpp CUDA server image (rolling latest → recent enough for Nemotron 3's
# hybrid Mamba arch) + Python so Modal can run the wrapping function.
llama_image = (
    modal.Image.from_registry(
        "ghcr.io/ggml-org/llama.cpp:server-cuda", add_python="3.12"
    )
    .entrypoint([])                  # clear the image's llama-server entrypoint; we launch it
    .env({"LLAMA_CACHE": "/cache"})  # llama.cpp downloads GGUFs here → persisted by the volume
)

# Persist the ~23 GB GGUF across cold starts (downloaded once, reused after).
cache_vol = modal.Volume.from_name("adpd-llama-cache", create_if_missing=True)


@app.function(
    image=llama_image,
    gpu=GPU,
    volumes={"/cache": cache_vol},
    secrets=[modal.Secret.from_name("adpd-llama")],  # provides LLAMA_API_KEY
    timeout=15 * MIN,            # max duration of a single request
    scaledown_window=5 * MIN,    # COST KNOB: idle this long after last call, then scale to $0
    max_containers=1,            # COST GUARDRAIL: never run more than ONE GPU (no parallel spend)
    # min_containers left at 0 → scales fully to zero when idle (no idle GPU billing)
)
@modal.concurrent(max_inputs=10)  # Modal-level concurrency; llama-server batches/queues internally
@modal.web_server(port=PORT, startup_timeout=20 * MIN)  # 1st cold start downloads ~23 GB
def serve():
    import os
    import shutil
    import subprocess

    bin_path = next(
        (p for p in (*LLAMA_SERVER_CANDIDATES, shutil.which("llama-server"))
         if p and os.path.exists(p)),
        None,
    )
    if not bin_path:
        raise RuntimeError("llama-server binary not found (checked /app, /, /usr/bin, PATH)")

    api_key = os.environ["LLAMA_API_KEY"]
    cmd = [
        bin_path,
        "-hf", f"{MODEL_REPO}:{MODEL_QUANT}",  # auto-download from HF into LLAMA_CACHE
        "--alias", MODEL_ALIAS,                # stable model id for OpenAI clients / Agno
        "--host", "0.0.0.0",                   # MUST bind 0.0.0.0 for Modal web_server
        "--port", str(PORT),
        "--api-key", api_key,
        "--jinja",                             # chat template + tool-calling support
        "-ngl", "99",                          # offload all layers to the GPU
        "-c", "16384",                         # context (Mamba state is constant-size → cheap)
        # Unsloth-recommended sampling (Agno can still override per request):
        "--temp", "0.6",
        "--top-p", "0.95",
        "--min-p", "0.01",
    ]
    printable = " ".join("***" if a == api_key else a for a in cmd)
    print("launching llama-server:", printable)
    subprocess.Popen(cmd)  # no shell=True needed — we pass an arg list


@app.local_entrypoint()
def test():
    """`modal run modal_app.py` → cold-start the server and hit the OpenAI endpoint once.

    Reads the API key from LLAMACPP_API_KEY (or LLAMA_API_KEY) in your local env/.env so
    it can authenticate against the running server. Polls /v1/models until the (possibly
    ~20 min first-time) download+load finishes, then sends one chat completion.
    """
    import json
    import os
    import time
    import urllib.error
    import urllib.request

    base = serve.get_web_url()  # URL of the (ephemeral) running web server
    api_key = os.environ.get("LLAMACPP_API_KEY") or os.environ.get("LLAMA_API_KEY")
    if not api_key:
        print("⚠️  No LLAMACPP_API_KEY / LLAMA_API_KEY in your local env — the server "
              "requires --api-key, so requests will 401. Set it (same value you gave the "
              "`adpd-llama` secret) and re-run.")
    headers = {"Authorization": f"Bearer {api_key or ''}", "Content-Type": "application/json"}

    def get(path):
        req = urllib.request.Request(base + path, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()

    # Poll until the model is loaded (first run downloads ~23 GB → be patient).
    print(f"waiting for server at {base} (first cold start can take ~20 min) ...")
    deadline = 22 * MIN
    waited = 0
    while True:
        try:
            status, _ = get("/v1/models")
            if status == 200:
                break
        except urllib.error.HTTPError as e:
            if e.code == 401:
                print("server is up but rejected the key (401). Fix the API key and re-run.")
                return
        except Exception:
            pass
        if waited >= deadline:
            print("timed out waiting for the server to become ready.")
            return
        time.sleep(15)
        waited += 15

    print("server ready — sending a test chat completion ...")
    payload = json.dumps({
        "model": MODEL_ALIAS,
        "messages": [{"role": "user", "content": "Say hello in exactly three words."}],
        "temperature": 0.6,
        "max_tokens": 256,
    }).encode()
    req = urllib.request.Request(base + "/v1/chat/completions", data=payload,
                                 headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        body = json.loads(r.read())
    print("reply:", body["choices"][0]["message"]["content"])
