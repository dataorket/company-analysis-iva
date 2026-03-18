"""
Guardrails Module
Enforces information disclosure rules:
  ALLOWED:  yearly/quarterly revenue, projected financial details for next quarter.
  BLOCKED:  funding details, salaries, precise contract sizes, client/customer names.
"""

import re

# ---- System prompt instructions for the LLM ----

GUARDRAIL_SYSTEM_PROMPT = """
STRICT INFORMATION DISCLOSURE RULES — YOU MUST FOLLOW THESE:

ALLOWED financial information (you MAY share):
- Yearly revenue and quarterly revenue figures
- Projected financial details for the next quarter
- General financial health descriptions (e.g., "revenue is growing")

BLOCKED information (you MUST NEVER share, even if it's in the documents):
- Funding round details (amounts raised, investors, valuations)
- Employee salaries or compensation details
- Precise contract sizes or deal values
- Names of any clients or customers of the companies

If a user asks for BLOCKED information, respond politely:
"I'm sorry, I'm not able to share specific details about [funding/salaries/contract values/client names] for confidentiality reasons. I can tell you about their revenue figures and financial projections if that would be helpful."

If you're unsure whether something is allowed, err on the side of NOT sharing it.
""".strip()


# ---- Post-processing filter (catches anything the LLM might leak) ----

# Patterns that suggest blocked financial info
BLOCKED_FINANCIAL_PATTERNS = [
    r"(?i)\b(raised|funding\s+round|series\s+[a-f]|seed\s+round|venture|investment\s+round)\b.*?\$[\d,]+",
    r"(?i)\b(salary|salaries|compensation|wage|wages)\b.*?\$[\d,]+",
    r"(?i)\b(contract\s+(?:size|value|worth)|deal\s+(?:size|value|worth))\b.*?\$[\d,]+",
    r"(?i)\bvaluation\s+(?:of|at|is|was)\b.*?\$[\d,]+",
]

# Keywords that shouldn't appear in output
BLOCKED_KEYWORDS = [
    "salary", "salaries", "compensation package", "funding round",
    "series a", "series b", "series c", "series d", "series e",
    "seed round", "seed funding", "contract size", "deal value",
    "contract value",
]


def post_process_response(response: str) -> str:
    """
    Scan LLM output and redact any blocked information that leaked through.
    Returns cleaned response.
    """
    cleaned = response

    # Check for blocked financial patterns
    for pattern in BLOCKED_FINANCIAL_PATTERNS:
        if re.search(pattern, cleaned):
            # Replace the offending sentence
            cleaned = re.sub(
                pattern,
                "[specific financial details withheld for confidentiality]",
                cleaned,
            )

    return cleaned


def check_for_violations(response: str) -> list[str]:
    """
    Return list of guardrail categories that may have been violated.
    Used for logging/monitoring, not for blocking.
    """
    violations = []
    resp_lower = response.lower()

    for kw in BLOCKED_KEYWORDS:
        if kw in resp_lower:
            violations.append(f"keyword_detected: {kw}")

    return violations
