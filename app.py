from __future__ import annotations

import html
import os
import re

# Disable Gradio's Node SSR sidecar BEFORE importing gradio. SSR (a separate Node proxy that
# server-side-renders the page) was interfering with the dynamically-injected iframe preview;
# pure client-side rendering is reliable for live HTML. On the HF Space THIS env var is what
# counts — the SDK launches the `app` object itself, so the launch(ssr_mode=...) at the bottom
# only affects local runs.
os.environ.setdefault("GRADIO_SSR_MODE", "false")

import gradio as gr

from instructions.toy_maker import toy_maker

# Import the model layer EAGERLY at startup. HF ZeroGPU only detects @spaces.GPU functions
# that are registered while the app module is importing — a lazy/in-function import means the
# decorated `generate` is never seen at startup ("No @spaces.GPU function detected"). The
# try/except keeps app.py importable locally (no torch/llama-cpp/spaces installed); on the
# Space the deps exist, the import succeeds, and ZeroGPU registers the GPU function.
try:
    from model import generate as model_generate
except Exception:  # surfaced in logs below
    import sys
    import traceback

    print("[app] model layer not available — using fallback replies. Reason:", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    model_generate = None


APP_TITLE = "Amazing Digital Pet Dentures — HTML Toy Maker"
APP_CSS = ""

# How many recent messages to keep (and send to the model). Bounds both the context window
# and the ~5 MB localStorage cap (each assistant turn carries a full HTML doc).
MAX_MESSAGES = 8

WELCOME_MESSAGE = [
    {
        "role": "assistant",
        "content": "Hi! I'm the dentures 🦷 — describe anything (a game, a widget, a "
                   "visualizer, a clock…) and I'll build it as a live HTML toy. "
                   "Hit 🧹 New session to start over.",
    }
]


# ---- HTML extraction -------------------------------------------------------------------
_THINK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)


def _strip_fences(text: str) -> str:
    """Remove ``` code fences but keep their contents."""
    text = re.sub(r"```[a-zA-Z0-9]*\n?", "", text or "")
    return text.replace("```", "")


def best_html(text: str | None) -> str | None:
    """Slice out the real HTML document: from the LAST <!doctype html> (or <html>) to the
    LAST </html>. The real doc is generated AFTER any reasoning, so taking the last opener
    avoids reasoning that merely *mentions* tags (which produced broken fragments before).
    """
    if not text:
        return None
    low = text.lower()
    start = low.rfind("<!doctype html")
    if start == -1:
        start = low.rfind("<html")
    if start == -1:
        return None
    end = low.rfind("</html>")
    if end == -1 or end <= start:
        return None
    doc = text[start:end + len("</html>")].strip()
    return doc if len(doc) >= 120 else None  # too-short => a mention, not a document


def parse_reply(content: str, reasoning: str) -> tuple[str, str, str | None]:
    """Split a raw model reply into (thinking, prose, html_doc_or_None)."""
    content = _strip_fences(_THINK_RE.sub("", content or "")).strip()
    reasoning = (reasoning or "").strip()
    doc = best_html(content)

    if doc:
        before = content[: content.find(doc)].strip()
        if reasoning:
            # Reasoning came cleanly separated, so `before` is just the friendly sentence.
            thinking, prose = reasoning, (before or "Here's your toy! 🎉")
        else:
            # Reasoning is mixed into content — everything before the doc is thinking.
            thinking, prose = before, "Here's your toy! 🎉"
        return thinking.strip(), (prose.strip() or "Here's your toy! 🎉"), doc

    # No complete document this turn.
    if reasoning:
        return reasoning, (content or "I couldn't finish that — try again?"), None
    return content, "I couldn't produce a complete toy that time — try rephrasing?", None


def answer_markdown(prose: str, doc: str | None) -> str:
    """The assistant chat bubble: the friendly line + the full HTML as a code block."""
    if doc:
        return f"{prose}\n\n```html\n{doc}\n```"
    return prose


def iframe_for(raw_html: str) -> str:
    srcdoc = html.escape(raw_html, quote=True)
    return (
        '<iframe class="adventure-frame" '
        f'srcdoc="{srcdoc}" '
        'allow="autoplay; fullscreen; clipboard-write; gamepad"></iframe>'
    )


def empty_preview_doc() -> str:
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'></head>"
        "<body style='font-family:system-ui;margin:0;display:grid;place-items:center;"
        "height:100vh;color:#171717;background:#fff8df'>"
        "<p style='font-weight:800'>Your toy will appear here. 🎪</p></body></html>"
    )


def empty_preview() -> str:
    return iframe_for(empty_preview_doc())


# ---- Model call ------------------------------------------------------------------------
def local_reply(message: str) -> str:
    """Fallback when the model layer can't be imported/run (e.g. no GPU locally)."""
    if not (message or "").strip():
        return "Tell me what to build — e.g. 'a bouncing ball that follows my mouse'."
    return (
        "I couldn't reach the model. This runs in-process on **ZeroGPU** via "
        "llama-cpp-python — check that the Space has ZeroGPU enabled and see the logs."
    )


def run_model(messages: list[dict], user_message: str) -> dict:
    """Always returns {"content", "reasoning"}."""
    if model_generate is None:
        return {"content": local_reply(user_message), "reasoning": ""}
    try:
        result = model_generate(messages)
        if isinstance(result, dict):
            return {"content": result.get("content", ""), "reasoning": result.get("reasoning", "")}
        return {"content": str(result), "reasoning": ""}
    except Exception as exc:  # keep the UI alive; surface the error in chat
        import sys
        import traceback

        traceback.print_exc(file=sys.stderr)
        return {"content": f"The toy maker hit a snag: {exc}", "reasoning": ""}


# ---- History (no Agno; convo lives in a BrowserState) ----------------------------------
def convo_to_history(convo: list[dict]) -> list[dict]:
    """Rebuild the chatbot from the persisted convo on reload (thinking is live-only)."""
    history = [{"role": m["role"], "content": m["content"]} for m in convo if m.get("content")]
    return history or list(WELCOME_MESSAGE)


def latest_html(convo: list[dict]) -> str | None:
    for m in reversed(convo):
        if m.get("role") == "assistant":
            doc = best_html(_strip_fences(m.get("content", "")))
            if doc:
                return doc
    return None


# ---- Event handlers --------------------------------------------------------------------
def chat_turn(message: str, history: list[dict] | None, convo: list[dict] | None):
    history = list(history or [])
    convo = list(convo or [])
    msg = (message or "").strip()
    if not msg:
        return "", history, convo, gr.update()

    history.append({"role": "user", "content": msg})
    sent = [{"role": "system", "content": toy_maker}] + convo[-MAX_MESSAGES:]
    sent.append({"role": "user", "content": msg})

    reply = run_model(sent, msg)
    thinking, prose, doc = parse_reply(reply["content"], reply["reasoning"])

    # Thinking shown as a SEPARATE collapsible bubble (Gradio's metadata accordion).
    if thinking:
        history.append({"role": "assistant", "content": thinking,
                        "metadata": {"title": "🧠 Thinking"}})
    answer = answer_markdown(prose, doc)
    history.append({"role": "assistant", "content": answer})

    # convo (model context + persistence) keeps the answer only — NOT the thinking.
    convo.append({"role": "user", "content": msg})
    convo.append({"role": "assistant", "content": answer})
    convo = convo[-MAX_MESSAGES:]

    # The preview panel is always on; only swap its content when we have a new toy.
    view = iframe_for(doc) if doc else gr.update()
    return "", history, convo, view


def hydrate(convo: list[dict] | None):
    """On page load, restore the chat + last toy from the persisted BrowserState."""
    convo = list(convo or [])
    history = convo_to_history(convo)
    doc = latest_html(convo)
    return history, (iframe_for(doc) if doc else empty_preview())


def new_session():
    """Clear chat + history + preview (panel stays on, showing the empty placeholder)."""
    return list(WELCOME_MESSAGE), "", [], empty_preview()


def build_app() -> gr.Blocks:
    global APP_CSS

    APP_CSS = """
    :root {
      --adpd-ink: #171717;
      --adpd-paper: #fff8df;
      --adpd-red: #ff4b4b;
      --adpd-blue: #42b7ff;
      --adpd-yellow: #ffd84d;
      --adpd-green: #70e06a;
      --adpd-purple: #bd7bff;
    }
    html, body { margin: 0; }
    .gradio-container {
      min-height: 100vh;
      max-width: 100% !important;
      padding: 0 !important;
      background:
        linear-gradient(45deg, rgba(23,23,23,.06) 25%, transparent 25%) 0 0 / 28px 28px,
        linear-gradient(-45deg, rgba(23,23,23,.06) 25%, transparent 25%) 0 0 / 28px 28px,
        var(--adpd-paper);
      color: var(--adpd-ink);
    }
    #adpd-shell {
      max-width: 100%;
      margin: 0;
      padding: 6px;
      gap: 6px;
    }
    #adpd-shell .gap { gap: 6px !important; }
    #adpd-title {
      border: 2px solid var(--adpd-ink);
      border-radius: 6px;
      background: var(--adpd-yellow);
      box-shadow: 4px 4px 0 var(--adpd-ink);
      padding: 6px 14px;
      margin-bottom: 8px;
    }
    #adpd-title h1 {
      font-size: clamp(1.1rem, 2vw, 1.7rem);
      line-height: 1.1;
      margin: 0;
      color: var(--adpd-ink);
    }
    #adpd-title p {
      font-size: .9rem;
      margin: 2px 0 0;
      color: var(--adpd-ink);
      font-weight: 700;
    }
    #chat-panel, #adventure-panel {
      border: 2px solid var(--adpd-ink);
      border-radius: 6px;
      background: white;
      box-shadow: 4px 4px 0 var(--adpd-ink);
      padding: 8px;
    }
    #adventure-panel {
      background: var(--adpd-blue);
    }
    /* Bounded viewport heights — fit one screen, never grow infinitely. */
    #toy-chat { height: 70vh !important; }
    .adventure-frame {
      width: 100%;
      height: 80vh;
      display: block;
      border: 2px solid var(--adpd-ink);
      border-radius: 6px;
      background: white;
    }
    #chat-panel textarea {
      min-height: 46px !important;
    }
    button, select, input, textarea {
      border-radius: 6px !important;
    }
    button {
      border: 2px solid var(--adpd-ink) !important;
      box-shadow: 3px 3px 0 var(--adpd-ink) !important;
      font-weight: 800 !important;
    }
    #adventure-toolbar {
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;
    }
    #adventure-label h3 { margin: 0; }
    @media (max-width: 900px) {
      #toy-chat { height: 50vh !important; }
      .adventure-frame { height: 60vh; }
    }
    """

    with gr.Blocks(title=APP_TITLE, fill_width=True) as demo:
        with gr.Column(elem_id="adpd-shell"):
            gr.Markdown(
                "# Amazing Digital Pet Dentures\n"
                "Describe anything — the dentures build it as a live HTML toy.",
                elem_id="adpd-title",
            )
            with gr.Row(equal_height=False, elem_id="main-row"):
                with gr.Column(scale=4, elem_id="chat-col"):
                    with gr.Group(elem_id="chat-panel"):
                        with gr.Row(elem_id="chat-toolbar"):
                            new_session_btn = gr.Button(
                                "🧹 New session", elem_id="new-session-btn",
                                scale=0, min_width=150,
                            )
                        chatbot = gr.Chatbot(
                            value=list(WELCOME_MESSAGE),
                            show_label=False,
                            elem_id="toy-chat",
                            height="70vh",
                        )
                        with gr.Row(elem_id="chat-input-row"):
                            message = gr.Textbox(
                                placeholder="Describe a toy to build...",
                                lines=1,
                                max_lines=6,
                                # no autofocus: it scroll-jumps to the input on load, pushing
                                # the title off the top now that the preview makes the page tall.
                                show_label=False,
                                container=False,
                                scale=8,
                            )
                            send_button = gr.Button(
                                "Send", variant="primary", scale=1, min_width=110
                            )
                # The preview panel is always on (no open/close) — it just shows the latest toy.
                with gr.Column(scale=7, elem_id="adventure-col"):
                    with gr.Group(elem_id="adventure-panel"):
                        with gr.Row(elem_id="adventure-toolbar"):
                            gr.Markdown("### 🎪 Your toy", elem_id="adventure-label")
                        adventure_view = gr.HTML(empty_preview(), elem_id="toy-view")

            # Persisted in the browser's localStorage: the model-facing conversation (user
            # turns + assistant answers incl. the HTML, NOT the thinking). Survives reloads;
            # more durable than the old ephemeral-disk SQLite. Cleared by "New session".
            convo = gr.BrowserState([], storage_key="adpd_convo")

            new_session_btn.click(
                new_session,
                inputs=None,
                outputs=[chatbot, message, convo, adventure_view],
            )

            chat_io = dict(
                fn=chat_turn,
                inputs=[message, chatbot, convo],
                outputs=[message, chatbot, convo, adventure_view],
            )
            message.submit(**chat_io)
            send_button.click(**chat_io)

            # On page load, restore chat + last toy from the persisted convo.
            demo.load(hydrate, inputs=[convo], outputs=[chatbot, adventure_view])
    return demo


app = build_app()


if __name__ == "__main__":
    app.launch(css=APP_CSS, ssr_mode=False)
