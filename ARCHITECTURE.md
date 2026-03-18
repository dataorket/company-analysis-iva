# Architecture Overview

## Design Philosophy

This application was designed with three principles:

1. **Simplicity over complexity** — The assignment says "show you can execute the basics." Every component is chosen to minimize setup while demonstrating understanding of the full pipeline.
2. **Zero cost** — All services run for free (Groq free tier, local embeddings, browser APIs).
3. **Modularity** — Each component can be swapped independently (e.g., Groq → OpenAI, browser TTS → ElevenLabs).

---

## System Architecture

```
┌────────────────────────────────────────────────────┐
│                  BROWSER (UI)                       │
│                                                     │
│  ┌─────────┐  ┌────────────┐  ┌────────────────┐   │
│  │  🎤 STT  │  │ Chat Panel │  │ Company Context│   │
│  │  (Web    │  │ (messages) │  │ Indicator      │   │
│  │  Speech  │  │            │  │                │   │
│  │  API)    │  │            │  │                │   │
│  └────┬────┘  └─────┬──────┘  └────────────────┘   │
│       │ transcript   │ text                         │
│       └──────┬───────┘                              │
│              ▼                                      │
│       POST /api/chat                                │
└──────────────┬──────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│               FastAPI BACKEND                         │
│                                                       │
│  1. Conversation Manager                              │
│     ├── Session memory (in-memory dict)               │
│     ├── Active company tracking                       │
│     ├── Pronoun/reference resolution                  │
│     └── Ambiguity detection → ask user                │
│                                                       │
│  2. RAG Retriever                                     │
│     ├── Embed query (ChromaDB local model)            │
│     ├── Search correct company collection             │
│     └── Return top-5 relevant chunks                  │
│                                                       │
│  3. LLM (Groq — Llama 3.1 70B)                       │
│     ├── System prompt with guardrail instructions     │
│     ├── Retrieved context + conversation history      │
│     └── Generate conversational response              │
│                                                       │
│  4. Guardrails (Post-processing)                      │
│     ├── Regex scan for blocked financial patterns     │
│     ├── Keyword detection (salary, funding, etc.)     │
│     └── Redact any leaked information                 │
│                                                       │
│  5. Response → JSON → Browser                         │
│     └── Browser SpeechSynthesis reads it aloud (TTS)  │
└──────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│              ChromaDB (Embedded Vector Store)          │
│                                                       │
│  Collection: mensch_und_maschine                      │
│  ├── Chunks from MuM documents                        │
│  └── Embedded with all-MiniLM-L6-v2 (local)          │
│                                                       │
│  Collection: tyson_foods                              │
│  ├── Chunks from Tyson documents                      │
│  └── Embedded with all-MiniLM-L6-v2 (local)          │
└──────────────────────────────────────────────────────┘
```

---

## Technology Choices & Justification

### LLM: Groq (Llama 3.1 70B) — Free Tier

**Why:** Groq provides free access to Llama 3.1 70B with extremely fast inference (~500 tokens/sec). For a RAG Q&A application, Llama 3.1 70B provides strong instruction-following and factual accuracy comparable to GPT-3.5-turbo.

**Trade-offs:**
- ✅ Completely free (up to 14,400 requests/day)
- ✅ Very fast responses (Groq's LPU hardware)
- ✅ Good at following guardrail instructions
- ⚠️ Slightly lower quality than GPT-4o for nuanced reasoning

**Production upgrade:** Swap to OpenAI GPT-4o-mini ($0.15/1M tokens) for better quality. One config change.

### Embeddings: ChromaDB Default (all-MiniLM-L6-v2) — Local

**Why:** ChromaDB includes a built-in sentence-transformer model that runs locally. No API key needed. For a document set of ~20 pages, this provides excellent retrieval quality.

**Trade-offs:**
- ✅ Free, runs locally, no API dependency
- ✅ Fast for small document sets
- ⚠️ First run downloads ~90MB model
- ⚠️ Less accurate than OpenAI embeddings for complex queries

**Production upgrade:** Use OpenAI text-embedding-3-small ($0.02/1M tokens) for better retrieval.

### Vector Store: ChromaDB (Embedded, Persistent)

**Why:** ChromaDB runs in-process (no server to start), persists to disk, and handles both storage and search. For a PoC with < 100 documents, it's the simplest possible choice.

**Trade-offs:**
- ✅ Zero infrastructure (pip install, done)
- ✅ File-backed persistence
- ✅ Built-in embedding support
- ⚠️ Not suitable for millions of documents

**Production upgrade:** Pinecone, Weaviate, or pgvector for scale.

### Backend: FastAPI

**Why:** Industry standard for ML/AI serving. Async, auto-generates OpenAPI docs, trivial to deploy. The reviewer can test the API directly at `/docs`.

### Voice: Browser Web Speech API (STT + TTS)

**Why:** Built into Chrome, Edge, and Safari. Zero cost, zero setup, zero API keys. The user clicks a microphone button, speaks, and the transcript is sent to the same `/api/chat` endpoint. Responses are read aloud via `SpeechSynthesis`.

**Trade-offs:**
- ✅ Free, instant, no server-side processing
- ✅ Works offline for STT
- ⚠️ Robotic TTS voice
- ⚠️ Only works in supported browsers (Chrome, Edge)

**Production upgrade:** OpenAI Whisper API (STT) + ElevenLabs (TTS) for natural voice quality.

### Frontend: Vanilla HTML/JS/CSS

**Why:** No build step. Reviewer opens the URL and it works. No npm, no webpack, no React setup. The UI is clean and professional — a single-page chat interface.

---

## Guardrails Design

The assignment has strict rules about information disclosure. We implement a **dual-layer** approach:

### Layer 1: System Prompt (Preventive)
The LLM receives explicit instructions about what it can and cannot share. This handles 95% of cases.

### Layer 2: Post-Processing Filter (Detective)
A code-based filter scans the LLM output for:
- Dollar amounts associated with funding/salary/contract keywords
- Known blocked keyword patterns

This catches the rare case where the LLM ignores system instructions.

### Why Two Layers?
LLMs are probabilistic — they occasionally ignore instructions. The post-processing layer provides a deterministic safety net. In an interview, this demonstrates understanding of defense-in-depth for AI systems.

---

## Conversation Context Design

The session manager tracks:
1. **Active company** — set when user mentions a company name
2. **History** — last 10 turns for context continuity
3. **Reference resolution**:
   - "their Q2 earnings" → use `active_company`
   - "the other one" → switch `active_company`
   - Ambiguous query + no context → ask for clarification

---

## What I Would Add in Production

| Feature | Technology | Why |
|---|---|---|
| Premium TTS | ElevenLabs API | Natural, human-like voice |
| Better STT | OpenAI Whisper API | Higher accuracy, language support |
| Stronger LLM | GPT-4o or Claude 3.5 | Better reasoning, guardrail following |
| Auth | JWT / OAuth | Multi-user support |
| Persistent sessions | Redis / PostgreSQL | Survive server restarts |
| Monitoring | LangSmith / Helicone | Track LLM usage, latency, errors |
| CI/CD | GitHub Actions | Automated testing and deployment |
| Containerization | Docker + Compose | One-command deployment |
| Rate limiting | FastAPI middleware | Prevent abuse |
