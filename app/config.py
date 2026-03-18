"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Groq (Free LLM) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

# --- ChromaDB ---
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")
COLLECTION_MENSCH = "mensch_und_maschine"
COLLECTION_TYSON = "tyson_foods"

# --- Document ingestion ---
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CHUNK_SIZE = 500       # tokens (~characters * 0.75)
CHUNK_OVERLAP = 50     # overlap between chunks

# --- Server ---
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# --- Conversation ---
MAX_HISTORY_TURNS = 10  # keep last N turns per session
