"""
FastAPI Application — Company Analysis Interactive Conversational App
Serves the chat API and the frontend UI.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import os

from app.config import HOST, PORT
from app.conversation import (
    get_or_create_session,
    clear_session,
    resolve_company_context,
    COMPANY_DISPLAY_NAMES,
)
from app.rag import retrieve_chunks, get_collection_stats
from app.llm import generate_response
from app.guardrails import post_process_response, check_for_violations

app = FastAPI(
    title="Company Analysis IVA",
    description="Interactive conversational app for analyzing Mensch und Maschine and Tyson Foods",
    version="1.0.0",
)

# Serve static files (frontend)
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---- Request/Response Models ----

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    active_company: str | None = None
    active_company_display: str | None = None


# ---- Routes ----

@app.get("/")
async def serve_frontend():
    """Serve the chat UI."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint.
    Receives a text message, retrieves relevant docs, generates a response.
    """
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # 1. Get or create session
    session = get_or_create_session(request.session_id)

    # 2. Resolve which company the user is asking about
    company, clarification = resolve_company_context(message, session)

    # If we need clarification, return it directly
    if clarification:
        session.add_turn("user", message)
        session.add_turn("assistant", clarification)
        return ChatResponse(
            response=clarification,
            session_id=session.session_id,
            active_company=session.active_company,
            active_company_display=COMPANY_DISPLAY_NAMES.get(session.active_company) if session.active_company else None,
        )

    # 3. Retrieve relevant document chunks
    chunks = retrieve_chunks(query=message, company=company, top_k=5)

    # 4. Generate LLM response
    llm_response = generate_response(
        user_message=message,
        retrieved_chunks=chunks,
        conversation_history=session.history,
        active_company=session.active_company,
    )

    # 5. Apply post-processing guardrails
    cleaned_response = post_process_response(llm_response)

    # Log violations (for debugging, not shown to user)
    violations = check_for_violations(cleaned_response)
    if violations:
        print(f"⚠️  Guardrail flags: {violations}")

    # 6. Update session history
    session.add_turn("user", message)
    session.add_turn("assistant", cleaned_response)

    return ChatResponse(
        response=cleaned_response,
        session_id=session.session_id,
        active_company=session.active_company,
        active_company_display=COMPANY_DISPLAY_NAMES.get(session.active_company) if session.active_company else None,
    )


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Clear a conversation session."""
    clear_session(session_id)
    return {"status": "ok", "message": "Session cleared"}


@app.get("/health")
async def health():
    """Health check — also shows document counts."""
    stats = get_collection_stats()
    return {
        "status": "healthy",
        "collections": stats,
        "total_chunks": sum(stats.values()),
    }


# ---- Run with: python -m app.main ----

if __name__ == "__main__":
    import uvicorn
    print(f"\n🚀 Starting Company Analysis IVA")
    print(f"   Open: http://localhost:{PORT}")
    print(f"   API docs: http://localhost:{PORT}/docs\n")
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
