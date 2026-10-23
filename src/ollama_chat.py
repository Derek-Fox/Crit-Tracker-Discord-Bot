"""
Ollama backend (local and cloud) for "Tim the Magic Cow".

Wraps the official `ollama` Python client behind a Gemini-like interface:
    chat = OllamaChat(...)
    chat.send_message(text).text  -> str
"""

import logging
import os
from typing import Optional

from ollama import Client


class _Response:
    """Small container that exposes a `.text` attribute, like a Gemini response."""

    def __init__(self, text: str):
        self.text = text


class OllamaChat:
    def __init__(
        self,
        model: str,
        system_instruction: str,
        temperature: float = 1.0,
        host: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self.model = model
        self.host = (
            host or os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434"
        ).rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("OLLAMA_API_KEY")
        self.temperature = temperature
        self.timeout = timeout

        headers = (
            {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None
        )
        kwargs = {}
        if timeout is not None:
            kwargs["timeout"] = timeout
        self.client = Client(host=self.host, **kwargs)
        if headers:
            self.client._client.headers.update(headers)

        self.messages = [{"role": "system", "content": system_instruction}]

        backend = "cloud" if "ollama.com" in self.host else "local"
        logging.info(
            "Tim Ollama model '%s' initialized (backend=%s, host=%s).",
            model,
            backend,
            self.host,
        )

    def send_message(self, message: str) -> _Response:
        self.messages.append({"role": "user", "content": message})
        try:
            response = self.client.chat(
                model=self.model,
                messages=self.messages,
                options={"temperature": self.temperature},
            )
        except Exception as e:  # Defensive: never propagate transport/API errors.
            logging.error("Error communicating with Tim (Ollama): %s", e, exc_info=True)
            self.messages.pop()
            return _Response("Tim is having trouble responding right now.")

        reply = ""
        try:
            reply = (response.message.content or "")
        except (AttributeError, TypeError):
            reply = ""
        reply = reply.strip()

        self.messages.append({"role": "assistant", "content": reply})
        return _Response(reply)
