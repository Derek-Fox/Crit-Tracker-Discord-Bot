"""
Local (Ollama) backend for "Tim the Magic Cow".

Wraps the official `ollama` Python client behind a Gemini-like interface:
    chat = OllamaChat(...)
    chat.send_message(text).text  -> str

This lets the Discord bot run Tim locally via Ollama without changing the cogs
or helpers that depend on the Gemini API shape, while removing the Google AI
dependency entirely on this branch.
"""

import logging
import os

import ollama
from ollama import Client, ResponseError, RequestError


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
        host: str | None = None,
    ) -> None:
        self.model = model
        self.host = host or os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434"
        self.client = Client(host=self.host)
        self.messages = [{"role": "system", "content": system_instruction}]
        self.temperature = temperature
        logging.info(
            "Tim Ollama model '%s' initialized (host=%s).", model, self.host
        )

    def send_message(self, message: str) -> _Response:
        self.messages.append({"role": "user", "content": message})
        try:
            response = self.client.chat(
                model=self.model,
                messages=self.messages,
                options={"temperature": self.temperature},
            )
            reply = ""
            try:
                reply = (response.message.content or "").strip()
            except (AttributeError, TypeError):
                reply = ""
        except Exception as e:
            logging.error("Error communicating with Tim (Ollama): %s", e)
            # Roll back the user message so history stays consistent.
            self.messages.pop()
            return _Response("Tim is having trouble responding right now.")

        self.messages.append({"role": "assistant", "content": reply})
        return _Response(reply)
