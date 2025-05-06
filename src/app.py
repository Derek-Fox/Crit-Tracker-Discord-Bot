import json
import logging
from logging.handlers import RotatingFileHandler
import colorlog
from dotenv import load_dotenv
from os import getenv
import google.generativeai as genai
from sheets import SheetsHandler
from bot import init_bot


def config_logging():
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


def init_model(config_file: str, gemini_key):
    try:
        with open(config_file) as f:
            tim_config = json.load(f)

        genai.configure(api_key=gemini_key)
        tim = genai.GenerativeModel(
            model_name=tim_config["model_name"],
            system_instruction=tim_config["instruction"],
            generation_config=genai.GenerationConfig(
                temperature=tim_config["temperature"]
            ),
        )
        tim_chat = tim.start_chat()
        logging.info("Tim genai model initialized successfully")
        return tim_chat
    except FileNotFoundError as e:
        logging.error(f"Config file not found: {config_file}")
        raise (e)
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON in config file: {config_file}")
        raise (e)
    except Exception as e:
        logging.error(f"Failed to initialize Tim model: {e}")
        raise (e)


def load_chars(config_file: str):
    try:
        with open(config_file) as f:
            char_config = json.load(f)
        logging.info("Character configuration loaded successfully")
        return char_config
    except FileNotFoundError as e:
        logging.error(f"Character config file not found: {config_file}")
        raise (e)
    except json.JSONDecodeError:
        logging.error(f"Failed to parse JSON in character config file: {config_file}")
        raise (e)
    except Exception as e:
        logging.error(f"Unexpected error while loading character config: {e}")
        raise (e)


def main():
    try:
        config_logging()
        load_dotenv()

        tim_chat = init_model(getenv("TIM_CONFIG"), getenv("GEMINI_KEY"))

        sheets = SheetsHandler(getenv("SHEET_ID"))

        chars = load_chars(getenv("CHAR_CONFIG"))

        bot = init_bot(sheets, tim_chat, getenv("PWSH_PATH"), chars)

        bot.run(getenv("DISCORD_TOKEN"))
    except Exception as e:
        logging.critical(f"Critical error in main execution: {e}", exc_info=True)
        exit(1)


if __name__ == "__main__":
    main()
