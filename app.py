from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import gradio as gr


APP_TITLE = "Amazing Digital Pet Dentures"
ADVENTURES_DIR = Path("adventures")


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
      background:
        radial-gradient(circle at 20% 15%, rgba(255,255,255,.95), transparent 18rem),
        linear-gradient(135deg, #ff4f8b 0%, #ffde59 35%, #4bd9ff 70%, #8affb2 100%);
      display: grid;
      place-items: center;
      color: #17324d;
    }
    main {
      width: min(880px, calc(100vw - 32px));
      padding: 28px;
      border: 2px solid rgba(255,255,255,.72);
      border-radius: 8px;
      background: rgba(255,255,255,.42);
      box-shadow: 0 24px 80px rgba(18, 45, 82, .26), inset 0 1px 0 rgba(255,255,255,.75);
      backdrop-filter: blur(18px) saturate(1.5);
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
    <p>The ringmaster dentures demand three tiny wins before noon. Click each act as it leaves the tent.</p>
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


def optional_agent_reply(message: str, history: list[dict[str, str]]) -> str | None:
    try:
        from agents import respond  # type: ignore
    except Exception:
        return None

    reply = respond(message=message, history=history)
    return str(reply) if reply is not None else None


def local_reply(message: str) -> str:
    clean = message.strip()
    if not clean:
        return "Clack once if you need a task turned into an adventure."

    return (
        "I am the temporary front desk for the denture circus. "
        "The real agent team will plug in through `agents.py` later. "
        f"For now, I heard: {clean!r}. Pick a faux adventure from the dropdown and inspect the live HTML stage."
    )


def chat_turn(
    message: str,
    history: list[dict[str, str]] | None,
) -> tuple[str, list[dict[str, str]]]:
    next_history = list(history or [])
    if message.strip():
        next_history.append({"role": "user", "content": message})
    reply = optional_agent_reply(message, next_history) or local_reply(message)
    next_history.append({"role": "assistant", "content": reply})
    return "", next_history


def build_app() -> gr.Blocks:
    ensure_adventures()
    choices = adventure_choices()
    initial_adventure = choices[0] if choices else None

    css = """
    :root {
      --adpd-ink: #14304b;
      --adpd-pink: #ff4f8b;
      --adpd-blue: #4bd9ff;
      --adpd-yellow: #ffde59;
      --adpd-glass: rgba(255, 255, 255, .52);
    }
    .gradio-container {
      min-height: 100vh;
      background:
        radial-gradient(circle at 12% 10%, rgba(255,255,255,.9), transparent 18rem),
        radial-gradient(circle at 78% 8%, rgba(75,217,255,.42), transparent 18rem),
        linear-gradient(135deg, #ffe3ef 0%, #dff7ff 38%, #fff0a8 68%, #e6ffe9 100%);
      color: var(--adpd-ink);
    }
    #adpd-shell {
      max-width: 1440px;
      margin: 0 auto;
    }
    #adpd-title h1 {
      font-size: clamp(2rem, 4vw, 4.4rem);
      line-height: 1;
      margin-bottom: .35rem;
      letter-spacing: 0;
    }
    #adpd-title p {
      font-size: 1.05rem;
      max-width: 820px;
      color: #33516d;
    }
    #mascot-panel, #chat-panel, #adventure-panel {
      border: 1px solid rgba(255, 255, 255, .72);
      border-radius: 8px;
      background: var(--adpd-glass);
      box-shadow: 0 24px 80px rgba(37, 67, 96, .18), inset 0 1px 0 rgba(255,255,255,.76);
      backdrop-filter: blur(18px) saturate(1.45);
    }
    #mascot-panel {
      padding: 18px;
      min-height: 240px;
      display: grid;
      place-items: center;
    }
    #chat-panel, #adventure-panel {
      padding: 14px;
    }
    #adventure-panel {
      min-height: 680px;
    }
    .adventure-frame {
      width: 100%;
      height: 660px;
      border: 0;
      border-radius: 8px;
      background: white;
      box-shadow: inset 0 0 0 1px rgba(20,48,75,.14);
    }
    #denture-svg {
      width: min(100%, 280px);
      height: auto;
      filter: drop-shadow(0 18px 24px rgba(143, 38, 88, .22));
    }
    #chat-panel textarea {
      min-height: 58px !important;
    }
    @media (max-width: 900px) {
      #adventure-panel { min-height: 520px; }
      .adventure-frame { height: 500px; }
    }
    """

    with gr.Blocks(title=APP_TITLE, css=css) as demo:
        with gr.Column(elem_id="adpd-shell"):
            gr.Markdown(
                "# Amazing Digital Pet Dentures\n"
                "Turn chores, goals, and odd little obligations into playable HTML adventures.",
                elem_id="adpd-title",
            )
            with gr.Row(equal_height=False):
                with gr.Column(scale=4):
                    with gr.Group(elem_id="mascot-panel"):
                        gr.HTML(denture_svg())
                    with gr.Group(elem_id="chat-panel"):
                        chatbot = gr.Chatbot(
                            value=[
                                {
                                    "role": "assistant",
                                    "content": "Welcome to the circus desk. The agents arrive later; the adventure window works now.",
                                }
                            ],
                            label="Denture Chat",
                            height=360,
                        )
                        message = gr.Textbox(
                            label="Chat",
                            placeholder="Tell the dentures what quest you need...",
                            lines=2,
                        )
                        message.submit(
                            chat_turn,
                            inputs=[message, chatbot],
                            outputs=[message, chatbot],
                        )
                with gr.Column(scale=8):
                    with gr.Group(elem_id="adventure-panel"):
                        adventure_dropdown = gr.Dropdown(
                            choices=choices,
                            value=initial_adventure,
                            label="Adventure model",
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
    return demo


def denture_svg() -> str:
    return """
<svg id="denture-svg" viewBox="0 0 420 300" role="img" aria-label="Smiling digital dentures mascot" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="gum" x1="0" x2="1">
      <stop offset="0" stop-color="#ff7aad"/>
      <stop offset="0.5" stop-color="#ff4f8b"/>
      <stop offset="1" stop-color="#ff9bc3"/>
    </linearGradient>
    <linearGradient id="tooth" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="#ffffff"/>
      <stop offset="1" stop-color="#dff7ff"/>
    </linearGradient>
  </defs>
  <path d="M64 134 C72 52 344 52 356 134 C365 196 310 250 210 250 C110 250 55 196 64 134Z" fill="url(#gum)" stroke="#8d1443" stroke-width="8"/>
  <path d="M96 142 C112 126 308 126 324 142 C320 205 278 230 210 230 C142 230 100 205 96 142Z" fill="#5e1730" opacity=".92"/>
  <g>
    <rect x="112" y="128" width="42" height="78" rx="12" fill="url(#tooth)" stroke="#b8d7e6" stroke-width="3"/>
    <rect x="156" y="122" width="42" height="90" rx="12" fill="url(#tooth)" stroke="#b8d7e6" stroke-width="3"/>
    <rect x="200" y="120" width="42" height="92" rx="12" fill="url(#tooth)" stroke="#b8d7e6" stroke-width="3"/>
    <rect x="244" y="122" width="42" height="90" rx="12" fill="url(#tooth)" stroke="#b8d7e6" stroke-width="3"/>
  </g>
  <circle cx="165" cy="94" r="24" fill="#fff"/>
  <circle cx="255" cy="94" r="24" fill="#fff"/>
  <circle cx="171" cy="99" r="10" fill="#14304b"/>
  <circle cx="249" cy="99" r="10" fill="#14304b"/>
  <path d="M178 65 C190 48 230 48 242 65" fill="none" stroke="#8d1443" stroke-width="8" stroke-linecap="round"/>
  <path d="M132 252 C172 279 248 279 288 252" fill="none" stroke="#4bd9ff" stroke-width="10" stroke-linecap="round"/>
</svg>
"""


app = build_app()


if __name__ == "__main__":
    app.launch()
