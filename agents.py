import os
from pathlib import Path

from instructions.adventure_engineer import adventure_engineer
from agno.agent import Agent
from agno.models.llama_cpp import LlamaCpp
from agno.tools.file_generation import FileGenerationTools
from agno.skills import Skills, LocalSkills
from agno.db.sqlite import SqliteDb
from dotenv import load_dotenv

load_dotenv()

ADVENTURES_DIR = str(Path(__file__).resolve().parent / "adventures")
# Folder holding Agno skill packages (e.g. skills/game-engine/SKILL.md). Pointing the
# loader at the parent dir lets us add more skills later without touching this file.
SKILLS_DIR = str(Path(__file__).resolve().parent / "skills")

# Local SQLite store for per-user chat history + memories. The app passes a stable
# user_id/session_id (persisted in the browser via gr.BrowserState) into agent.run(),
# so each browser keeps its own continuous history. NOTE: HF Space disk is ephemeral —
# for durable cross-restart persistence on the Space, point this at a Volume/Dataset later.
DB_FILE = str(Path(__file__).resolve().parent / "adpd.db")
db = SqliteDb(db_file=DB_FILE)

# Single llama.cpp backend. If you don't have enough local compute, modal_app.py serves
# Nemotron via llama-server; point this at it with LLAMACPP_BASE_URL / LLAMACPP_API_KEY /
# LLM_MODEL_ID.
mainmodel = LlamaCpp(
    id=os.getenv("LLM_MODEL_ID", "nemotron"),
    base_url=os.getenv("LLAMACPP_BASE_URL", "http://localhost:8080/v1"),
    api_key=os.getenv("LLAMACPP_API_KEY", "sk-no-key"),
    retries=10,
)
model = mainmodel

# Single agent: it ONLY builds fully-playable 3D browser adventures and ships them by
# calling generate_html_file (which writes into ADVENTURES_DIR). No team, no planner.
adventure_agent = Agent(
    name="Adventure Engineer",
    role="Creates fully playable 3D browser adventure games from the user's request.",
    model=model,
    debug_mode=True,
    debug_level=2,
    tools=[
        FileGenerationTools(
            enable_html_generation=True,
            enable_json_generation=False,
            enable_csv_generation=False,
            enable_pdf_generation=False,
            enable_docx_generation=False,
            enable_txt_generation=False,
            save_files=True,
            output_directory=ADVENTURES_DIR
        )
    ],
    instructions=[adventure_engineer],
    # The game-engine skill (vendored from github/awesome-copilot) — lazy-loaded game-dev
    # references/templates the agent can pull on demand. Loader points at the skills/ dir.
    skills=Skills(loaders=[LocalSkills(SKILLS_DIR)]),
    # Per-user persistence: store + replay chat history (no LLM-driven memory extraction).
    db=db,
    add_history_to_context=True,
    num_history_runs=5,
    send_media_to_model=False
)

if __name__ == "__main__":
    adventure_agent.cli_app()
