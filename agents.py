import os
from pathlib import Path

from instructions.adventure_engineer import adventure_engineer
from agno.agent import Agent
from agno.models.llama_cpp import LlamaCpp
from agno.tools.coding import CodingTools
from agno.db.sqlite import SqliteDb
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.embedder.sentence_transformer import SentenceTransformerEmbedder
from agno.vectordb.lancedb import LanceDb, SearchType
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

ADVENTURES_DIR = str(Path(__file__).resolve().parent / "adventures")
Path(ADVENTURES_DIR).mkdir(exist_ok=True)  # CodingTools base_dir + where the app renders games

# Single gitignored folder for all local databases (session history + vector store).
DB_DIR = Path(__file__).resolve().parent / "db"
DB_DIR.mkdir(exist_ok=True)

# ---- Knowledge base (Traditional RAG) -------------------------------------------------
# The distilled game-dev patterns (knowledge/game-patterns.txt, ~3.7K tokens) live in a
# LanceDB vector store. We use TRADITIONAL RAG (search_knowledge=False +
# add_knowledge_to_context=True on the agent below): the patterns relevant to the user's
# request are searched and injected straight into the prompt, so the small model never has
# to call a search tool to get them. Embedding is local via sentence-transformers (no API key).
KNOWLEDGE_FILE = str(Path(__file__).resolve().parent / "knowledge" / "game-patterns.txt")
LANCEDB_URI = str(DB_DIR / "lancedb")

# Embedder: openbmb/MiniCPM-Embedding-Light (local, no API key). Its custom MiniCPM
# architecture must be loaded with trust_remote_code=True, which Agno's
# SentenceTransformerEmbedder(id=...) path can't pass — so we build the SentenceTransformer
# client ourselves and inject it. Output is 1024-dim (config.json hidden_size); we set
# dimensions to match so LanceDB's vector schema is correct. We leave the query prompt unset:
# Agno applies a single `prompt` to BOTH documents and queries, and the per-query instruction
# gain is negligible for this ~14-chunk corpus. (Switching embedder dims => delete db/lancedb.)
_embedding_client = SentenceTransformer("openbmb/MiniCPM-Embedding-Light", trust_remote_code=True)
game_embedder = SentenceTransformerEmbedder(
    sentence_transformer_client=_embedding_client,
    dimensions=1024,
    normalize_embeddings=True,
)

game_knowledge = Knowledge(
    vector_db=LanceDb(
        uri=LANCEDB_URI,
        table_name="game_patterns",
        search_type=SearchType.vector,
        embedder=game_embedder,
    ),
)
# Embed the patterns once. skip_if_exists avoids re-embedding unchanged content on startup;
# delete the db/lancedb dir to force a rebuild after you edit game-patterns.txt.
game_knowledge.insert(name="Game Patterns", path=KNOWLEDGE_FILE, skip_if_exists=True)

# Local SQLite store for per-user chat history + memories. The app passes a stable
# user_id/session_id (persisted in the browser via gr.BrowserState) into agent.run(),
# so each browser keeps its own continuous history. NOTE: HF Space disk is ephemeral —
# for durable cross-restart persistence on the Space, point this at a Volume/Dataset later.
DB_FILE = str(DB_DIR / "adpd.db")
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

# Single agent: a collaborator that ideates with the user, then BUILDS / EDITS playable
# 2D/3D browser games as single .html files under ADVENTURES_DIR. No team, no planner.
adventure_agent = Agent(
    name="Adventure Engineer",
    role="Brainstorms game ideas with the user, then builds and iteratively edits playable 2D/3D browser games.",
    model=model,
    debug_mode=True,
    debug_level=2,
    tools=[
        # CodingTools sandboxed to adventures/: write_file creates a new game, read_file +
        # edit_file change an existing one in place. No shell (no reliable executor here).
        CodingTools(
            base_dir=ADVENTURES_DIR,
            restrict_to_base_dir=True,
            max_lines=4000,       # read whole games before editing (defaults truncate large ones)
            max_bytes=200_000,
            enable_read_file=True,
            enable_write_file=True,
            enable_edit_file=True,
            enable_run_shell=False,
            enable_ls=True,
        )
    ],
    instructions=[adventure_engineer],
    # Traditional RAG: search the patterns with the user's request and inject the matches
    # into the prompt. search_knowledge=False means the small model does NOT call a search
    # tool — the retrieval happens automatically (see the knowledge-base comment above).
    knowledge=game_knowledge,
    search_knowledge=False,
    add_knowledge_to_context=True,
    # Per-user persistence: store + replay chat history (no LLM-driven memory extraction).
    db=db,
    add_history_to_context=True,
    num_history_runs=5,
    send_media_to_model=False
)

if __name__ == "__main__":
    adventure_agent.cli_app()
