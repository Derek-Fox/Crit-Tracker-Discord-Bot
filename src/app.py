"""
Main entry point for the Crit Tracker Discord Bot application.
This file initializes logging, loads configuration, sets up Google Sheets credentials,
initializes the GenAI model, and starts the Discord bot.
"""

import asyncio
import json
import logging
from logging.handlers import RotatingFileHandler
from os import getenv, path
import colorlog
from dotenv import load_dotenv
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from google.auth.external_account_authorized_user import (
    Credentials as ExternalAccountCredentials,
)
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from sheets import SheetsHandler
from bot import init_bot


def init_logs():
    """
    Initializes logging for the application, setting up both file and console handlers
    with appropriate formatting and log levels.
    """
    fmt = "%(asctime)s - %(levelname)s - %(message)s"
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

    discord_logger = logging.getLogger("discord")
    discord_logger.propagate = False


def init_model(tim_config: dict, gemini_key):
    """
    Initializes the GenAI model (Tim) with the provided configuration and API key.

    :param tim_config: Configuration dictionary for the Tim model, including model name, system instruction, and generation parameters.
    :param gemini_key: API key for authenticating with the GenAI service.
    """
    try:
        genai.configure(api_key=gemini_key)
        tim = genai.GenerativeModel(
            model_name=tim_config["model_name"],
            system_instruction=tim_config["instruction"],
            generation_config=genai.GenerationConfig(
                temperature=tim_config["temperature"]
            ),
        )
        tim_chat = tim.start_chat()
        logging.info("Tim genai model initialized successfully.")
        return tim_chat
    except Exception as e:
        logging.error("Failed to initialize Tim model: %s", e)
        raise (e)


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
        raise (e)
    except json.JSONDecodeError as e:
        logging.error("Failed to parse JSON in config file: %s", config_file)
        raise (e)
    except Exception as e:
        logging.error("Unexpected error while loading config: %s", e)
        raise (e)


def load_google_credentials(
    credentials_file: str, token_file: str = "token.json"
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
            creds = flow.run_local_server(host="127.0.0.1", port=8080, redirect_uri_trailing_slash=True, open_browser=True)

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


async def main():
    """
    Main entry point for the application. Initializes logging, loads configuration and credentials,
    sets up the GenAI model, and starts the Discord bot. Handles exceptions gracefully, logging
    critical errors and exiting if initialization fails.
    """
    try:
        init_logs()
        load_dotenv()
        config = load_config("./config.json")

        google_creds = load_google_credentials("./credentials.json")
        sheets = SheetsHandler(getenv("SHEET_ID"), google_creds)

        tim_chat = init_model(config["tim_config"], getenv("GEMINI_KEY"))

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