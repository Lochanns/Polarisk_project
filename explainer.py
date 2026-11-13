"""Non-authoritative narrative generation over already computed evidence."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol

from .models import FindingEvidence

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "openai/gpt-oss-20b"

SYSTEM_PROMPT = """You are an AML analyst writing a concise narrative. The JSON supplied by
the application is authoritative, already computed evidence for an already-flagged
structuring finding. Do not make a detection decision, select transactions, calculate,
recalculate, add, omit, or change any facts. Write exactly one neutral paragraph using
only those facts. Do not introduce motives, risk scores, regulations, or information
not present in the evidence."""


class NarrativeClient(Protocol):
    def create_narrative(self, evidence_payload: dict[str, object]) -> str: ...


class GroqNarrativeClient:
    """Small adapter so tests never need a network client or an API key."""

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or os.environ.get("GROQ_API_KEY") or _api_key_from_dotenv()
        if not key:
            raise RuntimeError("GROQ_API_KEY is required when --explain is used")
        from openai import OpenAI

        self._client = OpenAI(api_key=key, base_url=GROQ_BASE_URL)

    def create_narrative(self, evidence_payload: dict[str, object]) -> str:
        response = self._client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=0,
            max_completion_tokens=1024,
            reasoning_effort="low",
            messages=[
                {
                    "role": "user",
                    "content": (
                        SYSTEM_PROMPT
                        + "\n\nAuthoritative detector evidence:\n"
                        + json.dumps(evidence_payload)
                    ),
                },
            ],
        )
        narrative = response.choices[0].message.content
        if not narrative:
            raise RuntimeError("Groq returned an empty narrative")
        return narrative.strip()


def _api_key_from_dotenv() -> str | None:
    """Read GROQ_API_KEY from an untracked local .env file, when present."""
    dotenv_path = Path.cwd() / ".env"
    try:
        lines = dotenv_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return None

    for line in lines:
        name, separator, value = line.partition("=")
        if separator and name.strip() == "GROQ_API_KEY":
            return value.strip().strip('"').strip("'") or None
    return None


def explain_finding(evidence: FindingEvidence, client: NarrativeClient) -> str:
    """Pass only detector-created evidence to the LLM adapter."""
    return client.create_narrative(evidence.to_llm_payload())
