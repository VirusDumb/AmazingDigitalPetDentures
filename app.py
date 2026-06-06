from __future__ import annotations

import html
import uuid
from pathlib import Path

import gradio as gr


APP_TITLE = "Amazing Digital Pet Adventures"
ADVENTURES_DIR = Path("adventures")
APP_CSS = ""


SAMPLE_ADVENTURES: dict[str, str] = {
    "morning-circus-cleanup.html": """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Morning Circus Cleanup</title>
  <style>
    :root { color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
    body {
      margin: 0;
      min-height: 100vh;
      background: #fff4d6;
      display: grid;
      place-items: center;
      color: #17324d;
    }
    main {
      width: min(880px, calc(100vw - 32px));
      padding: 28px;
      border: 4px solid #17324d;
      border-radius: 8px;
      background: #ffffff;
      box-shadow: 10px 10px 0 #ff4f8b;
    }
    h1 { margin: 0 0 8px; font-size: clamp(2rem, 5vw, 4rem); letter-spacing: 0; }
    p { max-width: 62ch; font-size: 1.05rem; line-height: 1.5; }
    .track { display: grid; gap: 12px; margin-top: 22px; }
    label {
      display: flex;
      gap: 12px;
      align-items: center;
      padding: 14px 16px;
      border: 1px solid rgba(23, 50, 77, .18);
      border-radius: 8px;
      background: rgba(255,255,255,.58);
      font-weight: 750;
    }
    input { width: 22px; height: 22px; accent-color: #ff2f73; }
    .banner { margin-top: 20px; font-weight: 850; color: #8d1443; }
  </style>
</head>
<body>
  <main>
    <h1>Morning Circus Cleanup</h1>
    <p>The ringmaster has three tiny wins waiting before noon. Click each act as it leaves the tent.</p>
    <section class="track" aria-label="Adventure checklist">
      <label><input type="checkbox" /> Sweep one visible surface for five minutes</label>
      <label><input type="checkbox" /> Drink water like a professional acrobat</label>
      <label><input type="checkbox" /> Put one wandering item back in its home</label>
    </section>
    <div class="banner">Bonus: say "ta-da" at least once. It counts.</div>
  </main>
</body>
</html>
""",
    "deep-work-tightrope.html": """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Deep Work Tightrope</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, sans-serif; color: #eef8ff; }
    body {
      margin: 0;
      min-height: 100vh;
      background:
        linear-gradient(90deg, rgba(255,255,255,.22) 1px, transparent 1px) 0 0 / 44px 44px,
        linear-gradient(180deg, #15335f 0%, #0b1020 100%);
      display: grid;
      place-items: center;
    }
    main { width: min(900px, calc(100vw - 28px)); }
    h1 { margin: 0 0 14px; font-size: clamp(2.1rem, 6vw, 4.6rem); letter-spacing: 0; }
    .rope {
      height: 12px;
      border-radius: 999px;
      background: linear-gradient(90deg, #ffde59, #ff4f8b, #4bd9ff);
      box-shadow: 0 0 28px rgba(75,217,255,.45);
      margin: 26px 0;
    }
    .acts { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; }
    button {
      border: 1px solid rgba(255,255,255,.25);
      border-radius: 8px;
      padding: 18px;
      min-height: 92px;
      background: rgba(255,255,255,.1);
      color: inherit;
      font: inherit;
      font-weight: 800;
      cursor: pointer;
      backdrop-filter: blur(12px);
    }
    button.done { background: rgba(138,255,178,.22); border-color: rgba(138,255,178,.7); }
    p { color: #c8e2ff; line-height: 1.5; }
  </style>
</head>
<body>
  <main>
    <h1>Deep Work Tightrope</h1>
    <p>Cross the rope in three careful blocks. Tap an act when it is complete.</p>
    <div class="rope" aria-hidden="true"></div>
    <section class="acts">
      <button>25 min focus sprint</button>
      <button>5 min stretch reset</button>
      <button>25 min final pass</button>
    </section>
  </main>
  <script>
    document.querySelectorAll("button").forEach((button) => {
      button.addEventListener("click", () => button.classList.toggle("done"));
    });
  </script>
</body>
</html>
""",
}


def ensure_adventures() -> None:
    ADVENTURES_DIR.mkdir(exist_ok=True)
    for filename, contents in SAMPLE_ADVENTURES.items():
        path = ADVENTURES_DIR / filename
        if not path.exists():
            path.write_text(contents, encoding="utf-8")


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
  <p>Generated HTML files will appear here later.</p>
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
    message: str, selected_adventure: str | None, user_id: str
) -> tuple[str, str | None]:
    try:
        from agents import adventure_agent  # type: ignore
    except Exception:
        return local_reply(message), None

    # Snapshot the folder so we can spot an adventure the Adventure Engineer just wrote.
    before = set(ADVENTURES_DIR.glob("*.html"))
    try:
        # Stable per-browser user_id/session_id → continuous history + memory for this user.
        response = adventure_agent.run(message, user_id=user_id, session_id=user_id)
    except Exception as exc:  # keep the Gradio handler alive; surface the error in chat
        import sys
        import traceback

        traceback.print_exc(file=sys.stderr)
        return f"The agent team hit a snag: {exc}", None

    reply = _response_text(response)
    new_files = sorted(set(ADVENTURES_DIR.glob("*.html")) - before, key=lambda p: p.stat().st_mtime)
    adventure_path = str(new_files[-1]) if new_files else None
    return reply, adventure_path


def local_reply(message: str) -> str:
    clean = message.strip()
    if not clean:
        return "Tell the quest booth what you need turned into an adventure."

    return (
        "I am the temporary quest booth for the circus. "
        "The real agent team will plug in through `agents.py` later. "
        f"For now, I heard: {clean!r}. Pick a faux adventure from the dropdown and inspect the live HTML stage."
    )


def ensure_user_id(user_id: str | None) -> str:
    """A stable id for this browser; generate one on first use (persisted via BrowserState)."""
    return user_id or f"u-{uuid.uuid4().hex[:12]}"


def chat_turn(
    message: str,
    history: list[dict[str, str]] | None,
    selected_adventure: str | None,
    user_id: str | None,
) -> tuple[str, list[dict[str, str]], gr.Dropdown, str, dict, dict, str]:
    user_id = ensure_user_id(user_id)
    next_history = list(history or [])
    if message.strip():
        next_history.append({"role": "user", "content": message})
    reply, adventure_path = optional_agent_turn(message, selected_adventure, user_id)
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
                "# Amazing Digital Pet Adventures\n"
                "Turn chores, goals, and odd little obligations into playable HTML adventures.",
                elem_id="adpd-title",
            )
            with gr.Row(equal_height=False):
                # Chat is the persistent primary window. When the adventure column is
                # hidden, this flex-grows to full width on its own (no scale juggling).
                with gr.Column(scale=3, elem_id="chat-col"):
                    with gr.Group(elem_id="booth-panel"):
                        gr.Markdown(
                            "## Quest Booth\n"
                            "Bright circus tasks, big-top energy.",
                            elem_id="booth-title",
                        )
                    with gr.Group(elem_id="chat-panel"):
                        chatbot = gr.Chatbot(
                            value=[
                                {
                                    "role": "assistant",
                                    "content": "Welcome to the quest booth. The agents arrive later; the adventure window works now.",
                                }
                            ],
                            label="Quest Chat",
                            height=520,
                        )
                        with gr.Row(elem_id="chat-input-row"):
                            message = gr.Textbox(
                                placeholder="Tell the booth what quest you need...",
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
            # Persisted in the browser's localStorage → stable per-browser user/session id
            # across reloads, so each visitor keeps their own history + memory.
            user_state = gr.BrowserState("", storage_key="adpd_user_id")

            chat_io = dict(
                fn=chat_turn,
                inputs=[message, chatbot, adventure_dropdown, user_state],
                outputs=[message, chatbot, adventure_dropdown, adventure_view, adventure_col, open_btn, user_state],
            )
            message.submit(**chat_io)
            send_button.click(**chat_io)
    return demo


app = build_app()


if __name__ == "__main__":
    app.launch(css=APP_CSS)
