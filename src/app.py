import json
import logging
from logging.handlers import RotatingFileHandler
import colorlog
from dotenv import load_dotenv
from os import getenv
import google.generativeai as genai
from sheets import SheetsHandler
from bot import Tim


def config_logging():
    LOG_FILE = "./out.log"
    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
    LOG_LEVEL = logging.DEBUG

    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    console_handler = colorlog.StreamHandler()
    console_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )
    console_handler.setFormatter(console_formatter)

    logging.basicConfig(level=LOG_LEVEL, handlers=[file_handler, console_handler])

    discord_logger = logging.getLogger("discord")
    discord_logger.propagate = False


def load_env() -> dict:
    load_dotenv()
    env = {
        "TOKEN": getenv("DISCORD_TOKEN"),
        "SHEET_ID": getenv("SHEET_ID"),
        "PWSH_PATH": rf"{getenv('PWSH_PATH')}",
        "GEMINI_KEY": getenv("GEMINI_API_KEY"),
        "BASH_PATH": rf"{getenv('BASH_PATH')}"
    }

    for key, value in env.items():
        if not value:
            logging.error(f"Env var '{key}' not found. Exiting...")
            exit(1)

    return env


def init_model(env: dict):
    with open("./src/tim_config.json") as f:
        tim_config = json.load(f)

    try:
        genai.configure(api_key=env["GEMINI_KEY"])
        tim = genai.GenerativeModel(
            model_name=tim_config["model_name"],
            system_instruction=tim_config["instruction"],
            generation_config=genai.GenerationConfig(
                temperature=tim_config["temperature"]
            ),
        )
        tim_chat = tim.start_chat()
        logging.info("Tim genai model initialized successfully")
    except Exception as e:
        logging.error(f"Exiting, failed to initialize tim: {e}")
        exit(1)

    return tim_chat


def main():
    config_logging()

    env = load_env()

    tim_chat = init_model(env)

    sheets = SheetsHandler(env['SHEET_ID'])
    
    bot = Tim(sheets, tim_chat, env)

    bot.run(getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
    main()
