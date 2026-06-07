from __future__ import annotations

import html
import re

import gradio as gr

from instructions.toy_maker import toy_maker

# Import the model layer EAGERLY at startup. HF ZeroGPU only detects @spaces.GPU functions
# that are registered while the app module is importing — a lazy/in-function import means the
# decorated `generate` is never seen at startup ("No @spaces.GPU function detected"). The
# try/except keeps app.py importable locally (no torch/llama-cpp/spaces installed); on the
# Space the deps exist, the import succeeds, and ZeroGPU registers the GPU function.
try:
    from model import generate as model_generate
except Exception as _model_import_error:  # noqa: F841 — surfaced in logs below
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
                   "visualizer, a to-do list…) and I'll build it as a live HTML toy. "
                   "Hit 🧹 New session to start over.",
    }
]

# ---- HTML extraction -------------------------------------------------------------------
_THINK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_DOCTYPE_RE = re.compile(r"<!doctype html.*?</html>", re.IGNORECASE | re.DOTALL)
_HTML_RE = re.compile(r"<html.*?</html>", re.IGNORECASE | re.DOTALL)


def extract_html(reply: str | None) -> tuple[str, str | None]:
    """Split a model reply into (chat_prose, html_doc_or_None).

    Strips <think> blocks and ``` fences, then slices out <!doctype…>…</html>
    (falls back to <html>…</html>). Whatever text is left becomes the chat message.
    """
    text = _THINK_RE.sub("", reply or "").strip()
    # Drop triple-backtick fences but keep their contents.
    text = re.sub(r"```[a-zA-Z0-9]*\n?", "", text).replace("```", "")
    match = _DOCTYPE_RE.search(text) or _HTML_RE.search(text)
    if not match:
        return (text.strip() or "Hmm, I didn't produce anything that time — try again?"), None
    html_doc = match.group(0).strip()
    prose = (text[: match.start()] + " " + text[match.end():]).strip()
    prose = re.sub(r"\s+", " ", prose).strip()
    return (prose or "Here's your toy! 🎉"), html_doc


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


def run_model(messages: list[dict], user_message: str) -> str:
    if model_generate is None:
        return local_reply(user_message)
    try:
        return model_generate(messages)
    except Exception as exc:  # keep the UI alive; surface the error in chat
        import sys
        import traceback

        traceback.print_exc(file=sys.stderr)
        return f"The toy maker hit a snag: {exc}"


# ---- History helpers (no Agno; convo lives in a BrowserState) ---------------------------
def to_display(convo: list[dict]) -> list[dict]:
    """Render the model-facing convo into chatbot messages (assistant = prose only)."""
    display: list[dict] = []
    for m in convo:
        if m.get("role") == "user":
            display.append({"role": "user", "content": m.get("content", "")})
        else:
            prose, _ = extract_html(m.get("content", ""))
            display.append({"role": "assistant", "content": prose})
    return display or list(WELCOME_MESSAGE)


def latest_html(convo: list[dict]) -> str | None:
    for m in reversed(convo):
        if m.get("role") == "assistant":
            _, doc = extract_html(m.get("content", ""))
            if doc:
                return doc
    return None


# ---- Event handlers --------------------------------------------------------------------
def chat_turn(message: str, convo: list[dict] | None):
    convo = list(convo or [])
    msg = (message or "").strip()
    if not msg:
        return "", to_display(convo), convo, gr.update(), gr.update(), gr.update()

    sent = [{"role": "system", "content": toy_maker}] + convo[-MAX_MESSAGES:]
    sent.append({"role": "user", "content": msg})
    reply = run_model(sent, msg)
    prose, html_doc = extract_html(reply)

    convo = (convo + [
        {"role": "user", "content": msg},
        {"role": "assistant", "content": reply},
    ])[-MAX_MESSAGES:]
    display = to_display(convo)

    if html_doc:
        return ("", display, convo, iframe_for(html_doc),
                gr.update(visible=True), gr.update(visible=False))
    return "", display, convo, gr.update(), gr.update(), gr.update()


def hydrate(convo: list[dict] | None):
    """On page load, restore the chat + last toy from the persisted BrowserState."""
    convo = list(convo or [])
    display = to_display(convo)
    doc = latest_html(convo)
    if doc:
        return display, iframe_for(doc), gr.update(visible=True), gr.update(visible=False)
    return display, empty_preview(), gr.update(visible=False), gr.update(visible=True)


def new_session():
    """Clear chat + history + preview and mint a blank session."""
    return (list(WELCOME_MESSAGE), "", [], empty_preview(),
            gr.update(visible=False), gr.update(visible=True))


def open_preview():
    return gr.update(visible=True), gr.update(visible=False)


def close_preview():
    return gr.update(visible=False), gr.update(visible=True)


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
    .gradio-container {
      min-height: 100vh;
      background:
        linear-gradient(45deg, rgba(23,23,23,.06) 25%, transparent 25%) 0 0 / 28px 28px,
        linear-gradient(-45deg, rgba(23,23,23,.06) 25%, transparent 25%) 0 0 / 28px 28px,
        var(--adpd-paper);
      color: var(--adpd-ink);
    }
    #adpd-shell {
      max-width: 1440px;
      margin: 0 auto;
      padding: 18px;
    }
    #adpd-title {
      border: 4px solid var(--adpd-ink);
      border-radius: 8px;
      background: var(--adpd-yellow);
      box-shadow: 8px 8px 0 var(--adpd-ink);
      padding: 18px 20px;
      margin-bottom: 18px;
    }
    #adpd-title h1, #booth-title h2 {
      font-size: clamp(2.2rem, 5vw, 5.2rem);
      line-height: 1;
      margin-bottom: .35rem;
      letter-spacing: 0;
      color: var(--adpd-ink);
    }
    #adpd-title p {
      font-size: 1.1rem;
      max-width: 820px;
      color: var(--adpd-ink);
      font-weight: 700;
    }
    #booth-panel, #chat-panel, #adventure-panel {
      border: 4px solid var(--adpd-ink);
      border-radius: 8px;
      background: white;
      box-shadow: 8px 8px 0 var(--adpd-ink);
    }
    #booth-panel {
      padding: 18px 18px 14px;
      min-height: 150px;
      background:
        linear-gradient(90deg, var(--adpd-red) 0 16.66%, white 16.66% 33.33%, var(--adpd-blue) 33.33% 50%, white 50% 66.66%, var(--adpd-red) 66.66% 83.33%, white 83.33% 100%);
      color: var(--adpd-ink);
      display: flex;
      align-items: end;
    }
    #chat-panel, #adventure-panel {
      padding: 14px;
    }
    #chat-panel {
      background: #fefefe;
      margin-top: 18px;
    }
    #adventure-panel {
      min-height: 680px;
      background: var(--adpd-blue);
    }
    .adventure-frame {
      width: 100%;
      height: 660px;
      border: 4px solid var(--adpd-ink);
      border-radius: 8px;
      background: white;
      box-shadow: 6px 6px 0 rgba(23,23,23,.35);
    }
    #booth-title {
      width: 100%;
      background: var(--adpd-yellow);
      border: 4px solid var(--adpd-ink);
      border-radius: 8px;
      padding: 12px;
      box-shadow: 6px 6px 0 var(--adpd-ink);
    }
    #booth-title h2 {
      font-size: clamp(1.5rem, 3vw, 2.8rem);
      margin: 0;
    }
    #booth-title p {
      margin: 8px 0 0;
      font-weight: 800;
      line-height: 1.35;
    }
    #chat-panel textarea {
      min-height: 58px !important;
    }
    button, select, input, textarea {
      border-radius: 8px !important;
    }
    button {
      border: 3px solid var(--adpd-ink) !important;
      box-shadow: 4px 4px 0 var(--adpd-ink) !important;
      font-weight: 900 !important;
    }
    #open-adventure-btn {
      width: 100%;
      margin-top: 16px;
      min-height: 70px;
      font-size: clamp(1.1rem, 2vw, 1.5rem) !important;
      background: var(--adpd-green) !important;
      box-shadow: 6px 6px 0 var(--adpd-ink) !important;
    }
    #adventure-toolbar {
      align-items: end;
      gap: 10px;
    }
    #close-adventure-btn {
      background: var(--adpd-red) !important;
      color: white !important;
    }
    @media (max-width: 900px) {
      #adventure-panel { min-height: 520px; }
      .adventure-frame { height: 500px; }
    }
    """

    with gr.Blocks(title=APP_TITLE) as demo:
        with gr.Column(elem_id="adpd-shell"):
            gr.Markdown(
                "# Amazing Digital Pet Dentures\n"
                "Describe anything — the dentures build it as a live HTML toy.",
                elem_id="adpd-title",
            )
            with gr.Row(equal_height=False):
                with gr.Column(scale=3, elem_id="chat-col"):
                    with gr.Group(elem_id="booth-panel"):
                        gr.Markdown(
                            "## Chat with the Dentures\n"
                            "Tell them what to make — they'll build it in HTML, live.",
                            elem_id="booth-title",
                        )
                    with gr.Group(elem_id="chat-panel"):
                        with gr.Row(elem_id="chat-toolbar"):
                            new_session_btn = gr.Button(
                                "🧹 New session", elem_id="new-session-btn",
                                scale=0, min_width=150,
                            )
                        chatbot = gr.Chatbot(
                            value=list(WELCOME_MESSAGE),
                            label="Chat with the Dentures",
                            height=520,
                        )
                        with gr.Row(elem_id="chat-input-row"):
                            message = gr.Textbox(
                                placeholder="Describe a toy to build...",
                                lines=1,
                                max_lines=6,
                                autofocus=True,
                                show_label=False,
                                container=False,
                                scale=8,
                            )
                            send_button = gr.Button(
                                "Send", variant="primary", scale=1, min_width=110
                            )
                    open_btn = gr.Button(
                        "👉 Click here to open your last toy",
                        elem_id="open-adventure-btn",
                        variant="primary",
                    )
                with gr.Column(scale=7, visible=False, elem_id="adventure-col") as adventure_col:
                    with gr.Group(elem_id="adventure-panel"):
                        with gr.Row(elem_id="adventure-toolbar"):
                            gr.Markdown("### 🎪 Your toy", elem_id="adventure-label")
                            close_btn = gr.Button(
                                "✕ Close",
                                elem_id="close-adventure-btn",
                                scale=0,
                                min_width=140,
                            )
                        adventure_view = gr.HTML(empty_preview())

            # Persisted in the browser's localStorage: the model-facing conversation
            # (user turns + assistant turns incl. the full HTML). Survives reloads;
            # more durable than the old ephemeral-disk SQLite. Cleared by "New session".
            convo = gr.BrowserState([], storage_key="adpd_convo")

            open_btn.click(open_preview, inputs=None, outputs=[adventure_col, open_btn])
            close_btn.click(close_preview, inputs=None, outputs=[adventure_col, open_btn])
            new_session_btn.click(
                new_session,
                inputs=None,
                outputs=[chatbot, message, convo, adventure_view, adventure_col, open_btn],
            )

            chat_io = dict(
                fn=chat_turn,
                inputs=[message, convo],
                outputs=[message, chatbot, convo, adventure_view, adventure_col, open_btn],
            )
            message.submit(**chat_io)
            send_button.click(**chat_io)

            # On page load, restore chat + last toy from the persisted convo.
            demo.load(
                hydrate,
                inputs=[convo],
                outputs=[chatbot, adventure_view, adventure_col, open_btn],
            )
    return demo


app = build_app()


if __name__ == "__main__":
    app.launch(css=APP_CSS)
