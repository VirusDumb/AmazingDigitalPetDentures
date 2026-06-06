from __future__ import annotations

import html
import uuid
from pathlib import Path

import gradio as gr


APP_TITLE = "Amazing Digital Pet Adventures"
ADVENTURES_DIR = Path("adventures")
APP_CSS = ""

# Shown when the chat first loads and whenever a new session is started.
WELCOME_MESSAGE = [
    {
        "role": "assistant",
        "content": "Hi! I'm the dentures 🦷 — tell me a vibe or an idea and I'll build you a playable game. Hit 🧹 New session anytime to start fresh.",
    }
]


def ensure_adventures() -> None:
    """Make sure the shared adventures/ folder exists (the agent writes games into it)."""
    ADVENTURES_DIR.mkdir(exist_ok=True)


def adventure_choices() -> list[str]:
    ensure_adventures()
    return sorted(path.name for path in ADVENTURES_DIR.glob("*.html"))


def read_adventure(filename: str | None) -> str:
    choices = adventure_choices()
    selected = filename if filename in choices else choices[0] if choices else None
    if selected is None:
        return empty_adventure_html()

    path = ADVENTURES_DIR / selected
    return path.read_text(encoding="utf-8")


def empty_adventure_html() -> str:
    return """<!doctype html>
<html lang="en">
<head><meta charset="utf-8" /><title>No Adventure</title></head>
<body style="font-family: system-ui; padding: 2rem;">
  <h1>No adventures yet</h1>
  <p>Ask the dentures to build you a game — it'll appear right here.</p>
</body>
</html>
"""


def iframe_for(raw_html: str) -> str:
    srcdoc = html.escape(raw_html, quote=True)
    return (
        '<iframe class="adventure-frame" '
        f'srcdoc="{srcdoc}" '
        'allow="autoplay; fullscreen; clipboard-write; gamepad"></iframe>'
    )


def load_adventure(filename: str | None) -> str:
    return iframe_for(read_adventure(filename))


def reload_adventures() -> tuple[gr.Dropdown, str]:
    choices = adventure_choices()
    selected = choices[0] if choices else None
    return gr.Dropdown(choices=choices, value=selected), load_adventure(selected)


def latest_adventure() -> str | None:
    """Name of the most recently created/modified adventure, or None if there are none."""
    ensure_adventures()
    files = list(ADVENTURES_DIR.glob("*.html"))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime).name


def open_adventure() -> tuple[dict, dict, gr.Dropdown, str]:
    """Open the adventure window on the latest adventure (the 'continue' button)."""
    choices = adventure_choices()
    selected = latest_adventure()
    if selected not in choices:
        selected = choices[0] if choices else None
    return (
        gr.update(visible=True),   # adventure_col
        gr.update(visible=False),  # open_btn
        gr.Dropdown(choices=choices, value=selected),
        load_adventure(selected),  # falls back to empty_adventure_html() when None
    )


def close_adventure() -> tuple[dict, dict]:
    """Close the adventure window and bring back the 'continue' button."""
    return gr.update(visible=False), gr.update(visible=True)


def _response_text(response: object) -> str:
    """Pull the assistant text out of an Agno run response."""
    content = getattr(response, "content", response)
    return str(content) if content is not None else ""


def optional_agent_turn(
    message: str, selected_adventure: str | None, user_id: str, session_id: str
) -> tuple[str, str | None]:
    try:
        from agents import adventure_agent  # type: ignore
    except Exception:
        return local_reply(message), None

    # Snapshot the folder so we can spot an adventure the Adventure Engineer just wrote.
    before = set(ADVENTURES_DIR.glob("*.html"))
    try:
        # Stable per-browser user_id; session_id is resettable via the "New session" button,
        # so each session starts with clean history.
        response = adventure_agent.run(message, user_id=user_id, session_id=session_id)
    except Exception as exc:  # keep the Gradio handler alive; surface the error in chat
        import sys
        import traceback

        traceback.print_exc(file=sys.stderr)
        return f"The dentures hit a snag: {exc}", None

    reply = _response_text(response)
    new_files = sorted(set(ADVENTURES_DIR.glob("*.html")) - before, key=lambda p: p.stat().st_mtime)
    adventure_path = str(new_files[-1]) if new_files else None
    return reply, adventure_path


def local_reply(message: str) -> str:
    """Fallback when the agent can't be imported (e.g. backend/env not configured yet)."""
    if not message.strip():
        return "Tell the dentures what game you'd like them to build."
    return (
        "I couldn't reach the game engine — check that your model backend is configured "
        "(see README: set LLAMACPP_BASE_URL / LLAMACPP_API_KEY in .env)."
    )


def ensure_user_id(user_id: str | None) -> str:
    """A stable id for this browser; generate one on first use (persisted via BrowserState)."""
    return user_id or f"u-{uuid.uuid4().hex[:12]}"


def ensure_session_id(session_id: str | None) -> str:
    """The current chat session; reset by the 'New session' button to clear agent history."""
    return session_id or f"s-{uuid.uuid4().hex[:12]}"


def new_session() -> tuple[list[dict[str, str]], str, str]:
    """Start a fresh session: clear the chat to the welcome and mint a new session_id so the
    agent's history (keyed by session_id) starts empty. Shared adventures are untouched."""
    return list(WELCOME_MESSAGE), "", f"s-{uuid.uuid4().hex[:12]}"


def chat_turn(
    message: str,
    history: list[dict[str, str]] | None,
    selected_adventure: str | None,
    user_id: str | None,
    session_id: str | None,
) -> tuple[str, list[dict[str, str]], gr.Dropdown, str, dict, dict, str, str]:
    user_id = ensure_user_id(user_id)
    session_id = ensure_session_id(session_id)
    next_history = list(history or [])
    if message.strip():
        next_history.append({"role": "user", "content": message})
    reply, adventure_path = optional_agent_turn(message, selected_adventure, user_id, session_id)
    next_history.append({"role": "assistant", "content": reply})

    choices = adventure_choices()
    next_selection = selected_adventure
    if adventure_path:
        next_selection = Path(adventure_path).name
        if next_selection not in choices:
            choices = adventure_choices()

    if next_selection not in choices:
        next_selection = choices[0] if choices else None

    # Auto-open the adventure window only when a NEW adventure was just generated;
    # otherwise leave the open/closed state exactly as the user left it.
    if adventure_path:
        col_update = gr.update(visible=True)
        open_btn_update = gr.update(visible=False)
    else:
        col_update = gr.update()
        open_btn_update = gr.update()

    return (
        "",
        next_history,
        gr.Dropdown(choices=choices, value=next_selection),
        load_adventure(next_selection),
        col_update,
        open_btn_update,
        user_id,
        session_id,
    )


def build_app() -> gr.Blocks:
    global APP_CSS

    ensure_adventures()
    choices = adventure_choices()
    initial_adventure = choices[0] if choices else None

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
    /* Big glossy "continue your last adventure" call-to-action under the chat. */
    #open-adventure-btn {
      width: 100%;
      margin-top: 16px;
      min-height: 70px;
      font-size: clamp(1.1rem, 2vw, 1.5rem) !important;
      background: var(--adpd-green) !important;
      box-shadow: 6px 6px 0 var(--adpd-ink) !important;
    }
    /* Adventure toolbar: dropdown + a compact close control. */
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
                "Creates playable HTML adventures.",
                elem_id="adpd-title",
            )
            with gr.Row(equal_height=False):
                # Chat is the persistent primary window. When the adventure column is
                # hidden, this flex-grows to full width on its own (no scale juggling).
                with gr.Column(scale=3, elem_id="chat-col"):
                    with gr.Group(elem_id="booth-panel"):
                        gr.Markdown(
                            "## Chat with the Dentures\n"
                            "Tell them a vibe — they'll build you a playable game.",
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
                                placeholder="Chat with the dentures...",
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
                        "👉 Click here to continue your last adventure",
                        elem_id="open-adventure-btn",
                        variant="primary",
                    )
                # The adventure window: hidden by default, opens side-by-side.
                with gr.Column(scale=7, visible=False, elem_id="adventure-col") as adventure_col:
                    with gr.Group(elem_id="adventure-panel"):
                        with gr.Row(elem_id="adventure-toolbar"):
                            adventure_dropdown = gr.Dropdown(
                                choices=choices,
                                value=initial_adventure,
                                label="Adventure model",
                                scale=8,
                            )
                            close_btn = gr.Button(
                                "✕ Close adventure",
                                elem_id="close-adventure-btn",
                                scale=1,
                                min_width=140,
                            )
                        refresh_button = gr.Button("Refresh adventures")
                        adventure_view = gr.HTML(load_adventure(initial_adventure))

            adventure_dropdown.change(
                load_adventure,
                inputs=adventure_dropdown,
                outputs=adventure_view,
            )
            refresh_button.click(
                reload_adventures,
                inputs=None,
                outputs=[adventure_dropdown, adventure_view],
            )
            open_btn.click(
                open_adventure,
                inputs=None,
                outputs=[adventure_col, open_btn, adventure_dropdown, adventure_view],
            )
            close_btn.click(
                close_adventure,
                inputs=None,
                outputs=[adventure_col, open_btn],
            )
            # Persisted in the browser's localStorage across reloads:
            #  - user_id: stable per browser (forward-compatible with future accounts).
            #  - session_id: the current chat; reset by "New session" to clear agent history.
            user_state = gr.BrowserState("", storage_key="adpd_user_id")
            session_state = gr.BrowserState("", storage_key="adpd_session_id")

            new_session_btn.click(
                new_session,
                inputs=None,
                outputs=[chatbot, message, session_state],
            )

            chat_io = dict(
                fn=chat_turn,
                inputs=[message, chatbot, adventure_dropdown, user_state, session_state],
                outputs=[message, chatbot, adventure_dropdown, adventure_view, adventure_col,
                         open_btn, user_state, session_state],
            )
            message.submit(**chat_io)
            send_button.click(**chat_io)
    return demo


app = build_app()


if __name__ == "__main__":
    app.launch(css=APP_CSS)
