"""
Main entry point for the Crit Tracker Discord Bot application.
This file initializes logging, loads configuration, sets up Google Sheets credentials,
initializes the Ollama model, and starts the Discord bot.
"""

import asyncio
import json
import logging
from logging.handlers import RotatingFileHandler
from os import getenv, path
import colorlog
from dotenv import load_dotenv

from google.oauth2.credentials import Credentials
from google.auth.external_account_authorized_user import (
    Credentials as ExternalAccountCredentials,
)
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from sheets import SheetsHandler
from bot import init_bot
from ollama_chat import OllamaChat


def init_logs():
    """
    Initializes logging for the application, setting up both file and console handlers
    with appropriate formatting and log levels.
    """
    fmt = "%(asctime)s - %(levelname)s - %(message)s - %(name)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    file_handler = RotatingFileHandler("./out.log", maxBytes=1_000_000, backupCount=3)
    file_handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))

    console_handler = colorlog.StreamHandler()
    console_handler.setFormatter(
        colorlog.ColoredFormatter(
            fmt="%(log_color)s" + fmt,
            datefmt=datefmt,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )
    )

    logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console_handler])

    # Prevent discord and google-oauth loggers from spamming the logs with debug info
    logging.getLogger("discord").setLevel(logging.INFO)
    logging.getLogger("requests_oauthlib.oauth2_session").setLevel(logging.INFO)


LOCAL_DEFAULT_HOST = "http://127.0.0.1:11434"
CLOUD_DEFAULT_HOST = "https://ollama.com"
LOCAL_DEFAULT_MODEL = "gemma4:e2b"


def resolve_ollama_config(tim_config: dict) -> dict:
    """Resolve a normalized Ollama configuration from env + config.

    Layered precedence (highest to lowest):
        1. Environment variables
        2. ``tim_config["ollama"]`` block (or legacy flat keys)
        3. Defaults based on backend.

    Returns a dict with keys: backend, model, host, api_key, timeout.
    Raises ValueError on missing/invalid required values.
    """
    block = {}
    if isinstance(tim_config.get("ollama"), dict):
        block = tim_config["ollama"]

    # ---- backend ----
    env_backend = getenv("OLLAMA_BACKEND")
    backend = (env_backend or block.get("backend") or "local").strip().lower()
    if backend not in {"local", "cloud"}:
        backend = "local"

    # ---- host ----
    host = (
        getenv("OLLAMA_HOST")
        or block.get("host")
        or tim_config.get("ollama_host")
        or (CLOUD_DEFAULT_HOST if backend == "cloud" else LOCAL_DEFAULT_HOST)
    )
    host = (host or "").strip().rstrip("/")
    if not host or not host.startswith(("http://", "https://")):
        raise ValueError(f"Invalid Ollama host: {host!r}")

    # ---- api key ----
    api_key = getenv("OLLAMA_API_KEY") or block.get("api_key") or tim_config.get("ollama_api_key")
    key_file = (
        getenv("OLLAMA_API_KEY_FILE")
        or block.get("api_key_file")
        or tim_config.get("ollama_api_key_file")
    )
    if not api_key and key_file and os.path.isfile(key_file):
        with open(key_file, encoding="utf-8") as f:
            api_key = f.read().strip()

    # Promote backend to cloud if the host/key indicate it.
    if backend == "local" and ("ollama.com" in host or (bool(api_key) and not host.startswith("http://127.0.0.1"))):
        backend = "cloud"

    # ---- model ----
    model = (
        getenv("OLLAMA_MODEL")
        or block.get("model")
        or tim_config.get("ollama_model")
        or LOCAL_DEFAULT_MODEL
    )
    model = (model or "").strip()
    if "ollama.com" in host and model.endswith(":cloud"):
        model = model[: -len(":cloud")]
    if not model:
        raise ValueError("Ollama model name is empty.")

    # ---- timeout ----
    raw_timeout = getenv("OLLAMA_TIMEOUT")
    if raw_timeout is None:
        raw_timeout = block.get("timeout")
    try:
        timeout = float(raw_timeout) if raw_timeout is not None else None
    except (TypeError, ValueError):
        raise ValueError(f"Invalid OLLAMA_TIMEOUT: {raw_timeout!r}")

    # ---- validation ----
    if backend == "cloud" or "ollama.com" in host:
        if not api_key:
            raise ValueError(
                "Ollama cloud backend requires an API key. "
                "Set OLLAMA_API_KEY (or OLLAMA_API_KEY_FILE / "
                "tim_config['ollama']['api_key_file'])."
            )

    resolved_backend = "cloud" if "ollama.com" in host else backend
    return {
        "backend": resolved_backend,
        "model": model,
        "host": host,
        "api_key": api_key,
        "timeout": timeout,
    }


def init_model(tim_config: dict) -> OllamaChat:
    """
    Initializes Tim via Ollama, supporting both local and cloud backends.

    Resolution is centralized in :func:`resolve_ollama_config`.
    """
    try:
        cfg = resolve_ollama_config(tim_config)
        temperature = tim_config.get("temperature", 1.0)
        tim_chat = OllamaChat(
            model=cfg["model"],
            system_instruction=tim_config["instruction"],
            temperature=temperature,
            host=cfg["host"],
            api_key=cfg["api_key"],
            timeout=cfg["timeout"],
        )
        logging.info(
            "Tim Ollama model initialized: backend=%s model=%s host=%s.",
            cfg["backend"],
            cfg["model"],
            cfg["host"],
        )
        return tim_chat
    except Exception as e:
        logging.error("Failed to initialize Tim model: %s", e)
        raise


def load_config(config_file: str):
    """
    Loads the configuration from a JSON file, logging the number of characters and crit types loaded.

    :param config_file: Path to the JSON configuration file
    :return: Configuration dictionary loaded from the file
    """
    try:
        with open(config_file, encoding="UTF-8") as f:
            config = json.load(f)
        logging.info("Config for %d characters loaded.", len(config["characters"]))
        logging.info("Config for %d crit types loaded.", len(config["crit_types"]))
        return config
    except FileNotFoundError as e:
        logging.error("Config file not found: %s", config_file)
        raise e
    except json.JSONDecodeError as e:
        logging.error("Failed to parse JSON in config file: %s", config_file)
        raise e
    except Exception as e:
        logging.error("Unexpected error while loading config: %s", e)
        raise e


def load_google_credentials(
        credentials_file: str, token_file: str
) -> Credentials | ExternalAccountCredentials:
    """Load Google credentials, refreshing or authenticating as needed.

    Args:
        credentials_file: Path to credentials.json for OAuth flow
        token_file: Path to token.json for storing/loading cached credentials

    Returns:
        Credentials object ready to use with Google APIs

    Raises:
        Exception: If credentials cannot be loaded or created via OAuth
    """
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = None

    # Try to load existing credentials
    if path.exists(token_file):
        try:
            logging.info("Loading credentials from %s...", token_file)
            creds = Credentials.from_authorized_user_file(token_file, scopes)

            # Refresh if expired
            if creds and creds.expired and creds.refresh_token:
                logging.info("Credentials expired. Refreshing...")
                creds.refresh(Request())
        except Exception as e:
            logging.warning("Failed to load credentials from %s: %s", token_file, e)
            creds = None

    # If no valid credentials, start OAuth flow
    if not creds or not creds.valid:
        logging.info("Starting OAuth flow using %s...", credentials_file)
        try:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, scopes)
            creds = flow.run_local_server(
                host="127.0.0.1", port=8080, redirect_uri_trailing_slash=True, open_browser=True
            )

            # Save credentials for future use
            with open(token_file, "w", encoding="UTF-8") as f:
                f.write(creds.to_json())
            logging.info("Credentials saved to %s", token_file)
        except Exception as e:
            logging.error("Failed to complete OAuth flow: %s", e)
            raise e

    if not creds:
        raise Exception("Failed to obtain valid Google credentials")

    logging.info("Google credentials initialized successfully.")

    return creds


async def main() -> None:
    """
    Main entry point for the application. Initializes logging, loads configuration and credentials,
    sets up the GenAI model, and starts the Discord bot. Handles exceptions gracefully, logging
    critical errors and exiting if initialization fails.
    """
    try:
        init_logs()
        load_dotenv()
        config = load_config("./config.json")

        google_creds = load_google_credentials("./credentials.json", "./token.json")
        sheets = SheetsHandler(getenv("SHEET_ID"), google_creds)

        tim_chat = init_model(config["tim_config"])

        bot = await init_bot(sheets, tim_chat, getenv("PWSH_PATH"), config)

        if discord_token := getenv("DISCORD_TOKEN"):
            await bot.start(discord_token)
        else:
            raise Exception("DISCORD_TOKEN not found")
    except Exception as e:
        logging.critical("Critical error in main execution: %s", e, exc_info=True)
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
