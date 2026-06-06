"""
test_endpoint.py — quick check of the deployed Modal llama-server OpenAI endpoint.

Usage (PowerShell):
    $env:LLAMACPP_BASE_URL = "https://soumyaray532--adpd-llama-serve.modal.run/v1"
    $env:LLAMACPP_API_KEY  = "sk-the-value-you-gave-the-adpd-llama-secret"
    python scripts/test_endpoint.py

First call cold-starts the GPU and (on the very first run ever) downloads ~23 GB, so
it can take up to ~20 min before you see a reply. Later calls are fast.
"""
import os
import sys

from openai import OpenAI

BASE_URL = os.environ.get(
    "LLAMACPP_BASE_URL", "https://soumyaray532--adpd-llama-serve.modal.run/v1"
)
API_KEY = os.environ.get("LLAMACPP_API_KEY")
MODEL_ID = os.environ.get("LLM_MODEL_ID", "unsloth/Nemotron-3-Nano-30B-A3B")

if not API_KEY:
    sys.exit(
        "Set LLAMACPP_API_KEY first (the same value you gave the `adpd-llama` Modal "
        "secret). In PowerShell:  $env:LLAMACPP_API_KEY = \"sk-...\""
    )

client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=20 * 60)

print(f"→ {BASE_URL}  (model: {MODEL_ID})")
print("waiting for first response (cold start can take a while) ...\n")

resp = client.chat.completions.create(
    model=MODEL_ID,
    messages=[{"role": "user", "content": "Say hello in exactly three words."}],
    temperature=0.6,
)
print("reply:\n" + resp.choices[0].message.content)
