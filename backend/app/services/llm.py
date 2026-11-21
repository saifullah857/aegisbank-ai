"""Groq chat-completions client (OpenAI-compatible HTTP API).

Contract: complete_json() NEVER raises. No API key, a timeout, an HTTP error or malformed output all return
None, and every caller then uses its deterministic result — the app works end-to-end with zero LLM calls.
"""
import json
import logging

import httpx

from app.core.config import get_settings

log = logging.getLogger("aegisbank.llm")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqClient:
    def __init__(self, api_key: str | None, model: str, timeout: float = 20, transport: httpx.BaseTransport | None = None):
        self.api_key, self.model, self.timeout, self.transport = api_key, model, timeout, transport

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def complete_json(self, system: str, user: str) -> dict | None:
        if not self.available:
            return None
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                r = client.post(GROQ_URL, headers={"Authorization": f"Bearer {self.api_key}"}, json={
                    "model": self.model, "temperature": 0.2, "max_tokens": 600, "response_format": {"type": "json_object"},
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
                r.raise_for_status()
                parsed = json.loads(r.json()["choices"][0]["message"]["content"])
                return parsed if isinstance(parsed, dict) else None
        except Exception as exc:  # deliberately broad: any failure means "use the deterministic result"
            log.warning("Groq call failed (%s); falling back to deterministic analysis", type(exc).__name__)
            return None


    def chat(self, messages: list[dict], max_tokens: int = 500) -> str | None:
        """Plain-text completion for the assistant. Never raises: returns None on any failure so the caller can fall back."""
        if not self.available:
            return None
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                r = client.post(GROQ_URL, headers={"Authorization": f"Bearer {self.api_key}"},
                                json={"model": self.model, "temperature": 0.2, "max_tokens": max_tokens, "messages": messages})
                r.raise_for_status()
                text = r.json()["choices"][0]["message"]["content"]
                return text.strip() if isinstance(text, str) and text.strip() else None
        except Exception as exc:
            log.warning("Groq chat failed (%s); using the built-in answer", type(exc).__name__)
            return None


_client: GroqClient | None = None


def get_llm_client() -> GroqClient:
    global _client
    if _client is None:
        s = get_settings()
        _client = GroqClient(s.GROQ_API_KEY, s.GROQ_MODEL, s.LLM_REQUEST_TIMEOUT_SECONDS)
    return _client


def set_llm_client(client: GroqClient | None) -> None:
    global _client
    _client = client
