"""
Ollama backend (local and cloud) for "Tim the Magic Cow".

Wraps the official `ollama` Python client behind a Gemini-like interface:
    chat = OllamaChat(...)
    chat.send_message(text).text  -> str
"""

import logging
import os
import threading
from typing import Optional

import httpx
from ollama import Client, ResponseError


# Defaults for Ollama configuration resolution.
LOCAL_DEFAULT_HOST = "http://127.0.0.1:11434"
CLOUD_DEFAULT_HOST = "https://ollama.com"
LOCAL_DEFAULT_MODEL = "gemma4:e2b"


def _ollama_block(tim_config: dict) -> dict:
    """Return the ``ollama`` sub-block of *tim_config* if it is a dict."""
    if not isinstance(tim_config, dict):
        return {}
    block = tim_config.get("ollama")
    return block if isinstance(block, dict) else {}


def _resolve_backend(block: dict) -> str:
    """Resolve the requested backend name (``local`` or ``cloud``)."""
    env_backend = os.getenv("OLLAMA_BACKEND")
    backend = (
        env_backend
        or block.get("backend")
        or "local"
    )
    backend = str(backend).strip().lower()
    return backend if backend in {"local", "cloud"} else "local"


def _resolve_host(block: dict, tim_config: dict, backend: str) -> str:
    """Resolve and normalize the Ollama host URL."""
    host = (
        os.getenv("OLLAMA_HOST")
        or block.get("host")
        or tim_config.get("ollama_host")
        or (CLOUD_DEFAULT_HOST if backend == "cloud" else LOCAL_DEFAULT_HOST)
    )
    return (host or "").strip().rstrip("/")


def _validate_host(host: str) -> None:
    if not host or not host.startswith(("http://", "https://")):
        raise ValueError(f"Invalid Ollama host: {host!r}")


def _resolve_api_key(block: dict, tim_config: dict):
    """Resolve the API key, optionally loading it from a key file."""
    api_key = (
        os.getenv("OLLAMA_API_KEY")
        or block.get("api_key")
        or tim_config.get("ollama_api_key")
    )
    key_file = (
        os.getenv("OLLAMA_API_KEY_FILE")
        or block.get("api_key_file")
        or tim_config.get("ollama_api_key_file")
    )
    if not api_key and key_file and os.path.isfile(key_file):
        with open(key_file, encoding="utf-8") as f:
            api_key = f.read().strip()
    return api_key


def _promote_backend(backend: str, host: str, api_key) -> str:
    """Promote a ``local`` backend to ``cloud`` when host/key indicate it."""
    if backend == "local" and (
        "ollama.com" in host
        or (bool(api_key) and not host.startswith("http://127.0.0.1"))
    ):
        return "cloud"
    return backend


def _resolve_model(block: dict, tim_config: dict, host: str) -> str:
    """Resolve and normalize the model name."""
    model = (
        os.getenv("OLLAMA_MODEL")
        or block.get("model")
        or tim_config.get("ollama_model")
        or LOCAL_DEFAULT_MODEL
    )
    model = (model or "").strip()
    if "ollama.com" in host and model.endswith(":cloud"):
        model = model[: -len(":cloud")]
    if not model:
        raise ValueError("Ollama model name is empty.")
    return model


def _resolve_timeout(block: dict):
    """Resolve the request timeout, if any."""
    raw_timeout = os.getenv("OLLAMA_TIMEOUT")
    if raw_timeout is None:
        raw_timeout = block.get("timeout")
    try:
        return float(raw_timeout) if raw_timeout is not None else None
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid OLLAMA_TIMEOUT: {raw_timeout!r}") from exc


def _require_cloud_api_key(backend: str, host: str, api_key) -> None:
    if backend == "cloud" or "ollama.com" in host:
        if not api_key:
            raise ValueError(
                "Ollama cloud backend requires an API key. "
                "Set OLLAMA_API_KEY (or OLLAMA_API_KEY_FILE / "
                "tim_config['ollama']['api_key_file'])."
            )


def resolve_ollama_config(tim_config: dict) -> dict:
    """Resolve a normalized Ollama configuration from env + config.

    Layered precedence (highest to lowest):
        1. Environment variables
        2. ``tim_config["ollama"]`` block (or legacy flat keys)
        3. Defaults based on backend.

    Returns a dict with keys: backend, model, host, api_key, timeout.
    Raises ValueError on missing/invalid required values.
    """
    if not isinstance(tim_config, dict):
        tim_config = {}

    block = _ollama_block(tim_config)

    backend = _resolve_backend(block)
    host = _resolve_host(block, tim_config, backend)
    _validate_host(host)

    api_key = _resolve_api_key(block, tim_config)
    backend = _promote_backend(backend, host, api_key)

    model = _resolve_model(block, tim_config, host)
    timeout = _resolve_timeout(block)

    _require_cloud_api_key(backend, host, api_key)

    resolved_backend = "cloud" if "ollama.com" in host else backend
    return {
        "backend": resolved_backend,
        "model": model,
        "host": host,
        "api_key": api_key,
        "timeout": timeout,
    }


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
        max_history_turns: int = 10,
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
        if headers:
            kwargs["headers"] = headers
        self.client = Client(host=self.host, **kwargs)
        self.max_history_turns = max(0, int(max_history_turns))

        self.messages = [{"role": "system", "content": system_instruction}]
        # Serialize access to messages/history across discord event-loop threads.
        self._lock = threading.Lock()

        backend = "cloud" if "ollama.com" in self.host else "local"
        logging.info(
            "Tim Ollama model '%s' initialized (backend=%s, host=%s).",
            model,
            backend,
            self.host,
        )

    def _trim_history(self) -> None:
        # Keep system prompt plus the last N (user/assistant) turns.
        if self.max_history_turns == 0:
            self.messages = [self.messages[0]]
            return
        non_system = self.messages[1:]
        keep = self.max_history_turns * 2
        if len(non_system) > keep:
            self.messages = [self.messages[0]] + non_system[-keep:]

    def send_message(self, message: str) -> _Response:
        with self._lock:
            self.messages.append({"role": "user", "content": message})
            self._trim_history()
            try:
                response = self.client.chat(
                    model=self.model,
                    messages=self.messages,
                    options={"temperature": self.temperature},
                )
            except (ResponseError, httpx.HTTPError, TimeoutError, ConnectionError) as e:
                logging.error(
                    "Error communicating with Tim (Ollama): %s", e, exc_info=True
                )
                # Remove the unanswered user message so history stays clean.
                if self.messages and self.messages[-1].get("role") == "user":
                    self.messages.pop()
                return _Response("Tim is having trouble responding right now.")

            reply = ""
            try:
                reply = (response.message.content or "")
            except (AttributeError, TypeError):
                reply = ""
            reply = reply.strip()

            self.messages.append({"role": "assistant", "content": reply})
            self._trim_history()
            return _Response(reply)
