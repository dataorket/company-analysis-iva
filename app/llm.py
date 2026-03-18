"""
LLM Module
Calls Groq (free Llama 3.3 70B) with system prompt, retrieved context, and conversation history.
"""

from groq import Groq
from app.config import GROQ_API_KEY, LLM_MODEL
from app.guardrails import GUARDRAIL_SYSTEM_PROMPT
from app.conversation import COMPANY_DISPLAY_NAMES

# Lazy-initialized client
_groq_client: Groq | None = None


def _get_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        if not GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY not set. Get a free key at https://console.groq.com/keys "
                "and add it to your .env file."
            )
        _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client


SYSTEM_PROMPT = f"""You are a helpful, conversational AI assistant that answers questions about two companies:
- **Mensch und Maschine** (MuM): A German CAD/PDM software provider
- **Tyson Foods**: A US food manufacturing company

You answer questions ONLY based on the provided document context. If the answer is not found in the provided documents, say so clearly — NEVER guess or make up information. Do not use any prior knowledge about these companies.

Be conversational, professional, and concise. Use natural language, not bullet points (unless the user asks for a list).

{GUARDRAIL_SYSTEM_PROMPT}

IMPORTANT CONTEXT RULES:
- If the user mentions a specific company, answer about that company.
- If the user uses pronouns like "they", "their", "it", "the company" — refer to the currently active company indicated in the system context.
- If it's ambiguous which company they mean, ask for clarification.
- If the user says "the other one" or "the other company", switch to the other company.
"""


def generate_response(
    user_message: str,
    retrieved_chunks: list[dict],
    conversation_history: list[dict],
    active_company: str | None = None,
) -> str:
    """
    Generate a response using Groq (Llama 3.1).

    Args:
        user_message:         The user's current question.
        retrieved_chunks:     Relevant document chunks from RAG.
        conversation_history: Previous turns [{role, content}, ...].
        active_company:       Currently active company collection name.

    Returns:
        The assistant's response text.
    """
    client = _get_client()

    # Build context from retrieved chunks
    if retrieved_chunks:
        context_parts = []
        for chunk in retrieved_chunks:
            company_name = COMPANY_DISPLAY_NAMES.get(chunk["company"], chunk["company"])
            context_parts.append(
                f"[Source: {chunk['source']} | Company: {company_name}]\n{chunk['text']}"
            )
        context_block = "\n\n---\n\n".join(context_parts)
    else:
        context_block = "No relevant documents found."

    # Active company context for the LLM
    company_context = ""
    if active_company:
        display = COMPANY_DISPLAY_NAMES.get(active_company, active_company)
        company_context = f"\n\n[SYSTEM NOTE: The user is currently discussing {display}. Pronouns like 'they', 'their', 'it' refer to {display}.]"

    # Build messages
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT + company_context,
        }
    ]

    # Add conversation history (last few turns for context)
    for turn in conversation_history[-8:]:  # Last 8 messages (4 turns)
        messages.append({
            "role": turn["role"],
            "content": turn["content"],
        })

    # Add the current user message with retrieved context
    user_with_context = f"""Based on the following document excerpts, answer the user's question.

DOCUMENT CONTEXT:
{context_block}

USER QUESTION: {user_message}"""

    messages.append({
        "role": "user",
        "content": user_with_context,
    })

    # Call Groq
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=0.3,  # Low temp for factual accuracy
            max_tokens=1024,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"I'm sorry, I encountered an error generating a response. Please try again. (Error: {str(e)})"
