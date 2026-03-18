"""
Conversation Manager
Tracks session state: active company, conversation history,
context resolution (pronouns, "the other one", ambiguity).
"""

import uuid
from dataclasses import dataclass, field
from app.config import MAX_HISTORY_TURNS

# Company name aliases for detection
COMPANY_ALIASES = {
    "mensch_und_maschine": [
        "mensch und maschine", "mensch", "mum", "m+m", "m&m",
        "mensch und maschine se", "cad/pdm", "cad pdm",
    ],
    "tyson_foods": [
        "tyson foods", "tyson", "tyson food",
    ],
}

# Reverse map: alias → collection name
ALIAS_TO_COMPANY = {}
for company, aliases in COMPANY_ALIASES.items():
    for alias in aliases:
        ALIAS_TO_COMPANY[alias.lower()] = company


@dataclass
class Session:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    active_company: str | None = None  # "mensch_und_maschine" or "tyson_foods"
    history: list[dict] = field(default_factory=list)  # [{role, content}, ...]

    def add_turn(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        # Keep only last N turns
        if len(self.history) > MAX_HISTORY_TURNS * 2:
            self.history = self.history[-(MAX_HISTORY_TURNS * 2):]

    def get_other_company(self) -> str | None:
        """Return the company that is NOT currently active."""
        if self.active_company == "mensch_und_maschine":
            return "tyson_foods"
        elif self.active_company == "tyson_foods":
            return "mensch_und_maschine"
        return None


# In-memory session store
_sessions: dict[str, Session] = {}


def get_or_create_session(session_id: str | None = None) -> Session:
    """Get existing session or create a new one."""
    if session_id and session_id in _sessions:
        return _sessions[session_id]
    session = Session(session_id=session_id or str(uuid.uuid4()))
    _sessions[session.session_id] = session
    return session


def clear_session(session_id: str):
    """Remove a session."""
    _sessions.pop(session_id, None)


def detect_company(message: str) -> str | None:
    """
    Detect which company the user is asking about from the message text.
    Returns collection name or None.
    """
    msg_lower = message.lower()

    # Direct mention
    for alias, company in sorted(ALIAS_TO_COMPANY.items(), key=lambda x: -len(x[0])):
        if alias in msg_lower:
            return company

    return None


def resolve_company_context(message: str, session: Session) -> tuple[str | None, str | None]:
    """
    Resolve which company the user is asking about.
    Returns: (company_name | None, clarification_message | None)

    Logic:
    1. Explicit mention → use that company, update active
    2. "the other one/company" → switch to the other company
    3. Pronoun/implicit ("their", "they", "the company", "it") → use active
    4. No company context at all → ask for clarification
    """
    msg_lower = message.lower()

    # 1. Explicit company mention
    detected = detect_company(message)
    if detected:
        session.active_company = detected
        return detected, None

    # 2. "The other one" / "the other company" / switching language
    switch_phrases = ["the other one", "the other company", "other firm", "the second one", "other one", "switch"]
    for phrase in switch_phrases:
        if phrase in msg_lower:
            other = session.get_other_company()
            if other:
                session.active_company = other
                return other, None
            else:
                return None, "I'm not sure which company you'd like to switch to. Could you specify — **Mensch und Maschine** or **Tyson Foods**?"

    # 3. Implicit reference (pronouns, follow-up) → use active company
    if session.active_company:
        return session.active_company, None

    # 4. No context — check if the question is general or needs a company
    general_keywords = ["hello", "hi", "hey", "help", "what can you", "who are you", "how do"]
    if any(kw in msg_lower for kw in general_keywords):
        return None, None  # General question, no company needed

    # Ambiguous — ask
    return None, "I can help with information about two companies. Could you please specify which one you're asking about — **Mensch und Maschine** (a German CAD/PDM provider) or **Tyson Foods** (a US food manufacturer)?"


COMPANY_DISPLAY_NAMES = {
    "mensch_und_maschine": "Mensch und Maschine",
    "tyson_foods": "Tyson Foods",
}
