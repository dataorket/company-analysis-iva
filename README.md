# Company Analysis — Interactive Conversational App (IVA)

An interactive voice application that lets users ask questions about **Mensch und Maschine** (German CAD/PDM provider) and **Tyson Foods** (US food manufacturer) using provided document summaries as the sole information source.

## 🌐 Live Demo

**� [https://company-analysis-iva.onrender.com](https://company-analysis-iva.onrender.com)**

> **Note:** The free Render instance spins down after inactivity. The first request may take ~30 seconds to cold-start.

## �🚀 Quick Start (Local Development)

```bash
# 1. Install dependencies (in your venv)
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY (free: https://console.groq.com/keys)

# 3. Add company documents to data/ folders
# Place files in: data/mensch_und_maschine/ and data/tyson_foods/

# 4. Ingest documents into vector store
python ingest.py

# 5. Run the application
python -m app.main

# 6. Open in browser
# → http://localhost:8000
```

## 🏗️ Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design decisions and justifications.

**High-level flow:**
```
User (text or voice) → FastAPI backend → Conversation Manager → RAG Retrieval (ChromaDB) → LLM (Groq/Llama 3.3 70B) → Guardrails Filter → Response (text + TTS)
```

## ✨ Features

- **Natural language Q&A** about two companies from provided documents
- **Conversation memory** — maintains context across follow-up questions
- **Company context tracking** — understands pronouns ("their", "they") and "the other one"
- **Information guardrails** — blocks restricted financial data and client names
- **Voice input/output** — browser-based STT and TTS (Phase 2)
- **Clean web UI** — responsive chat interface

## 🔒 Guardrails

| Allowed | Blocked |
|---|---|
| ✅ Yearly/quarterly revenue | ❌ Funding details |
| ✅ Projected financials | ❌ Salaries/compensation |
| ✅ General financial health | ❌ Contract sizes |
| | ❌ Client/customer names |

## 🛠️ Tech Stack

| Component | Technology | Cost |
|---|---|---|
| LLM | Groq (Llama 3.3 70B) | Free |
| Embeddings | ChromaDB built-in (all-MiniLM-L6-v2) | Free (local) |
| Vector Store | ChromaDB (embedded) | Free |
| Backend | FastAPI + uvicorn | Free |
| Voice STT | Web Speech API (browser) | Free |
| Voice TTS | SpeechSynthesis API (browser) | Free |

**💰 Total cost: $0**

> **Production upgrade path:** For better quality, swap in OpenAI GPT-4o-mini ($0.15/1M tokens), OpenAI embeddings ($0.02/1M tokens), and ElevenLabs TTS for natural voice. The architecture is modular — these are config changes, not rewrites.

## 📁 Project Structure

```
├── README.md                 # This file
├── ARCHITECTURE.md           # Detailed architecture & justifications
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
├── .env                      # Your API keys (gitignored)
├── ingest.py                 # Document ingestion script
├── app/
│   ├── main.py               # FastAPI app & routes
│   ├── config.py             # Configuration
│   ├── conversation.py       # Session & context management
│   ├── rag.py                # Document retrieval
│   ├── llm.py                # LLM integration (Groq)
│   └── guardrails.py         # Information filtering
├── static/
│   ├── index.html            # Chat UI
│   ├── style.css             # Styling
│   └── app.js                # Frontend logic + voice
├── data/
│   ├── mensch_und_maschine/  # Company documents
│   └── tyson_foods/          # Company documents
└── chroma_db/                # Vector store (auto-generated)
```

## 🧪 Example Interactions

| User Query | Expected Response |
|---|---|
| "What does Mensch und Maschine do?" | Summary of MuM's core business |
| "What about their 2024 Q2 earnings?" | Q2 revenue (context: still MuM) |
| "Tell me about the other company" | Switches to Tyson Foods |
| "Who are the founders?" | Answers about Tyson (current context) |
| "What's their funding history?" | Politely declines (blocked info) |

## 📝 License

Built for Merantix technical assessment — March 2026.
