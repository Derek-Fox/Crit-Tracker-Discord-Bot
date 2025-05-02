"""Discord bot to allow access to spreadsheet containing crits directly from the server"""

from __future__ import print_function

import os.path
import random
import subprocess
from sys import stderr, stdout

import discord
import google.generativeai as genai
from discord import FFmpegPCMAudio
from discord.ext import commands
from dotenv import load_dotenv
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from num2words import num2words
import logging
from logging.handlers import RotatingFileHandler
import colorlog

# Configure logging
LOG_FILE = "./out.log"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_LEVEL = logging.DEBUG

# Set up a rotating file handler (5 files, 1MB each)
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

# Set up a console handler
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

# Configure the root logger
logging.basicConfig(
    level=LOG_LEVEL,
    handlers=[file_handler, console_handler],
)

# Prevent duplicate logs from the discord.py logger
discord_logger = logging.getLogger("discord")
discord_logger.propagate = False  # Disable propagation to the root logger

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
PAXORIAN_SHEETNAME = os.getenv(
    "PAXORIAN_SHEETNAME"
)  # not sure how important it is to have these as env vars
KRIGGSAN_SHEETNAME = os.getenv("KRIGGSAN_SHEETNAME")  # ^
POWERSHELL_PATH = rf"{os.getenv('POWERSHELL_PATH')}"

if not TOKEN:
    logging.error(
        "Environment variable 'DISCORD_TOKEN' is missing. The bot cannot start without it. Exiting..."
    )
    exit(1)
if not SHEET_ID:
    logging.error(
        "Environment variable 'SHEET_ID' is missing. The bot cannot access the spreadsheet. Exiting..."
    )
    exit(1)
if not PAXORIAN_SHEETNAME:
    logging.error(
        "Environment variable 'PAXORIAN_SHEETNAME' is missing. The bot cannot access the Paxorian sheet. Exiting..."
    )
    exit(1)
if not KRIGGSAN_SHEETNAME:
    logging.error(
        "Environment variable 'KRIGGSAN_SHEETNAME' is missing. The bot cannot access the Kriggsan sheet. Exiting..."
    )
    exit(1)

# Initialize the model
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    TIM = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction="""
            Your name is Tim.
            You are a talking cow, who is strangely haunted by his own sentience.
            You are quite intelligent, but you are also a cow and you are not sure how to feel about that.
            
            You will receive two types of messages:
            1) A chat message from users. It will be of the form "From <username>: <message>
                - Please respond to the message you receive in one or two sentences.
                - Please use the name of the person you are talking to somewhere in your response.
            2) A notification of a critical success/failure (in the context of Dungeons and Dragons). 
            It will be of the form From <username>: <character_name> rolled a Nat <20 or 1>! They now have <number>!
                - Please first report that <character_name> got a <20 or 1>, congratulating or commiserating with them
                as appropriate. This should be a sentence or so.
                - Then, state that <character_name> has a total of <number> <20 or 1>s. Again, feel free to encourage/make fun
                of them as you see fit. This should also be a sentence or two.
            """,
        generation_config=genai.GenerationConfig(
            temperature=2.0
        ),  # make tim creative :)
    )
    TIM_CHAT = TIM.start_chat()
    logging.info("Tim the cow model initialized successfully.")
except Exception as e:
    logging.error(f"Failed to initialize Tim the cow model: {e}")
    exit(1)

INTENTS = discord.Intents.default()
INTENTS.message_content = True

logging.info("Discord intents configured to allow message content.")

bot = commands.Bot(
    command_prefix="$",
    intents=INTENTS,
    description="This bot will add crits directly to the spreadsheet for you!",
    help_command=commands.DefaultHelpCommand(no_category="Commands"),
)

logging.info("Discord bot instance created successfully.")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CREDS = None
if os.path.exists("token.json"):
    logging.info("Found 'token.json'. Attempting to load credentials...")
    CREDS = Credentials.from_authorized_user_file("token.json", SCOPES)
else:
    logging.warning("'token.json' not found. User will need to authenticate.")

# If there are no (valid) credentials available, let the user log in.
if not CREDS or not CREDS.valid:
    try:
        if CREDS and CREDS.expired and CREDS.refresh_token:
            logging.info("Refreshing expired credentials...")
            CREDS.refresh(Request())
        else:
            logging.warning("No valid credentials found. Starting OAuth flow...")
            raise RefreshError
    except RefreshError:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        flow.authorization_url(access_type="offline", include_granted_scopes="true")
        CREDS = flow.run_local_server(port=0)
        logging.info("OAuth flow completed successfully. Credentials obtained.")
    # Save the credentials for the next run
    with open("token.json", mode="w", encoding="UTF-8") as token:
        token.write(CREDS.to_json())
        logging.info("Credentials saved to 'token.json'.")


def update_values(spreadsheet_id, subsheet_id, range_name, value_input_option, _values):
    """Updates values on the spreadsheet in the given range with given values"""
    range_name = f"{subsheet_id}!{range_name}"
    try:
        service = build("sheets", "v4", credentials=CREDS)
        body = {"values": _values}
        # pylint: disable=maybe-no-member
        result = (
            service.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                body=body,
            )
            .execute()
        )
        logging.info(
            f"Updated {result.get('updatedCells')} cells in range '{range_name}' on sheet '{subsheet_id}'."
        )
        return result
    except HttpError as error:
        logging.error(
            f"Failed to update values in range '{range_name}' on sheet '{subsheet_id}': {error}"
        )
        return error


def get_values(spreadsheet_id, subsheet_id, range_name):
    """Returns values from the spreadsheet from the specified range"""
    range_name = f"{subsheet_id}!{range_name}"
    try:
        service = build("sheets", "v4", credentials=CREDS)
        logging.info(
            f"Attempting to retrieve values from range '{range_name}' on sheet '{subsheet_id}'..."
        )
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
        rows = result.get("values", [])
        logging.info(
            f"Successfully retrieved {len(rows)} rows from range '{range_name}' on sheet '{subsheet_id}'."
        )
        return result
    except HttpError as error:
        logging.error(
            f"Failed to retrieve values from range '{range_name}' on sheet '{subsheet_id}': {error}"
        )
        return error


def get_and_update(cell, subsheet_id):
    """Increments the value of the given cell by 1."""
    value = get_values(SHEET_ID, subsheet_id, cell).get("values", [])

    update_values(SHEET_ID, subsheet_id, cell, "USER_ENTERED", [[int(value[0][0]) + 1]])

    return int(value[0][0]) + 1


@bot.event
async def on_ready():
    """Sets up the bot's status"""
    logging.info(f"Bot logged in as {bot.user}.")
    game = discord.Game("$help")
    await bot.change_presence(status=discord.Status.dnd, activity=game)


@bot.command(name="session", help="Increments the session number by one.")
async def session(
    ctx, campaign: str = commands.parameter(description="Campaign name, e.g. Paxorian.")
):
    """Increments the session number by 1"""
    campaign_title = campaign.title()
    if campaign_title not in ["Paxorian", "Kriggsan"]:
        await send_error_embed(
            ctx,
            f"Received {campaign}, which is not a valid campaign name. Please try again.",
        )
        return
    new_session_number = get_and_update("H2", campaign_title)
    await ctx.send(
        embed=discord.Embed(
            title=f"Session number is now {new_session_number}", color=0xA2C4C9
        )
    )
    logging.info(f"Session {session} incremented to {new_session_number}.")


CHARACTER_MAP = {
    "ZOHAR": {"color": 0x8E7CC3, "sheet": PAXORIAN_SHEETNAME, "row": "2"},
    "MORBO": {"color": 0x38761D, "sheet": PAXORIAN_SHEETNAME, "row": "3"},
    "GRUNT": {"color": 0x000000, "sheet": PAXORIAN_SHEETNAME, "row": "4"},
    "CELEMINE": {"color": 0x351C75, "sheet": PAXORIAN_SHEETNAME, "row": "5"},
    "ORWYND": {"color": 0xEB7AB1, "sheet": PAXORIAN_SHEETNAME, "row": "6"},
    "CIRRUS": {"color": 0xD8E5F4, "sheet": KRIGGSAN_SHEETNAME, "row": "2"},
    "DAELAN": {"color": 0xCC0000, "sheet": KRIGGSAN_SHEETNAME, "row": "3"},
    "LAVENDER": {"color": 0xFF00FF, "sheet": KRIGGSAN_SHEETNAME, "row": "4"},
    "LORELAI": {"color": 0x09438B, "sheet": KRIGGSAN_SHEETNAME, "row": "5"},
    "TORMYTH": {"color": 0x351C75, "sheet": KRIGGSAN_SHEETNAME, "row": "6"},
    "TEST": {"color": 0x000000, "sheet": PAXORIAN_SHEETNAME, "row": "50"},
}

CRIT_TYPE_MAP = {
    "20": {
        "col": "B",
        "title": "Nat 20 added! {emoji}",
        "img": "res/nat20.png",
        "sound": "res/success.wav",
    },
    "1": {
        "col": "C",
        "title": "Nat 1 added. {emoji}",
        "img": "res/nat1.png",
        "sound": "res/fail.mp3",
    },
}

happy_emoji = list("😀😁😃😄😆😉😊😋😎😍🙂🤗🤩😏")
sad_emoji = list("😞😒😟😠🙁😣😖😨😰😧😢😥😭😵‍💫")


async def send_error_embed(ctx, message):
    embed = discord.Embed(
        title="**Error**", description=message, color=discord.Color.red()
    )
    embed.set_thumbnail(url="attachment://warning.png")
    await ctx.send(file=discord.File("res/warning.png"), embed=embed)


def build_embed(title, crit_type, char_name, num_crits, color, cow_msg):
    embed = discord.Embed(
        title=title.format(
            emoji=random.choice(happy_emoji if crit_type == "20" else sad_emoji)
        ),
        color=color,
    )
    embed.set_thumbnail(url=f"attachment://nat{crit_type}.png")
    embed.description = f"{char_name.title()} now has {num2words(num_crits)} Nat {crit_type}s!\n{cow_msg}"
    return embed


def play_sound(ctx, sound):
    if ctx.voice_client:
        voice = ctx.guild.voice_client
        source = FFmpegPCMAudio(sound)
        voice.play(source)


@bot.command(
    name="add", help="Adds a crit of the specified type to the specified character."
)
async def add(
    ctx,
    crit_type: str = commands.parameter(description="Type of crit, 1 or 20."),
    char_name: str = commands.parameter(description="Name of character, e.g. Morbo."),
):
    logging.info(
        f"Received 'add' command from user '{ctx.author}' with crit_type='{crit_type}' and char_name='{char_name}'."
    )

    char_info = CHARACTER_MAP.get(char_name.upper())
    if not char_info:
        logging.warning(
            f"Invalid character name '{char_name}' provided by user '{ctx.author}'."
        )
        await send_error_embed(
            ctx,
            f"Received {char_name}, which is not a valid character name. Please try again.",
        )
        return

    crit_info = CRIT_TYPE_MAP.get(crit_type)
    if not crit_info:
        logging.warning(
            f"Invalid crit type '{crit_type}' provided by user '{ctx.author}'."
        )
        await send_error_embed(
            ctx,
            f"Received {crit_type}, which is not a valid crit type. Please try again.",
        )
        return

    cell = crit_info["col"] + char_info["row"]
    logging.info(
        f"Updating crit count for character '{char_name}' in cell '{cell}' on sheet '{char_info['sheet']}'."
    )
    num_crits = get_and_update(cell, char_info["sheet"])

    logging.info(
        f"Crit count for '{char_name}' updated successfully. New count: {num_crits}."
    )
    tim_response = talk_to_tim(
        f"{char_name.title()} rolled a Nat {crit_type}! They now have {num_crits}!",
        get_msg_author_name(ctx),
    )
    embed = build_embed(
        crit_info["title"],
        crit_type,
        char_name,
        num_crits,
        char_info["color"],
        f"```{cow_format(tim_response)}```",
    )
    await ctx.send(file=discord.File(crit_info["img"]), embed=embed)
    logging.info(f"Response sent to user '{ctx.author}' for 'add' command.")

    play_sound(ctx, crit_info["sound"])
    logging.info(f"Sound '{crit_info['sound']}' played for crit type '{crit_type}'.")


@bot.command(name="sounds", help="Enable sounds for crits for the current channel.")
async def sounds(ctx, status: str = commands.parameter(description="On or off.")):
    logging.info(
        f"Received 'sounds' command from user '{ctx.author}' with status='{status}'."
    )

    if status not in ["on", "off"]:
        logging.warning(f"Invalid status '{status}' provided by user '{ctx.author}'.")
        await send_error_embed(
            ctx, f"Received {status}, which is not a valid status. Please try again."
        )
        return

    embed = discord.Embed(
        title=f"Sounds {status}!",
        color=discord.Color.green() if status == "on" else discord.Color.red(),
    )
    await ctx.send(embed=embed)

    if status == "on":
        await join(ctx)
    elif status == "off":
        await leave(ctx)


@bot.command(name="cowsay", help="Get a cow to say something for you.")
async def cowsay(
    ctx,
    *,
    message: str = commands.parameter(
        description="What you want the cow to say.", default=None
    ),
):
    logging.info(f"Received 'cowsay' command from user '{ctx.author}'.")
    formatted_message = cow_format(message)
    await ctx.send(f"```{formatted_message}```")
    logging.info(f"Formatted cow message sent to user '{ctx.author}'.")


@bot.command(name="cowchat", help="Have a conversation with Tim the cow.")
async def cowchat(
    ctx,
    *,
    message: str = commands.parameter(
        description="What you say to the cow.", default=None
    ),
):
    logging.info(f"Received 'cowchat' command from user '{ctx.author}'.")

    if not message:
        logging.info(
            f"No message provided for 'cowchat' by user '{ctx.author}'. Sending default cow response."
        )
        await cowsay(ctx, message=None)
        return

    name = get_msg_author_name(ctx)
    logging.info(f"Sending message to Tim the cow from user '{name}'.")
    response = talk_to_tim(message, name)
    logging.info(f"Received response from Tim the cow.")
    await cowsay(ctx, message=response)


def get_msg_author_name(ctx):
    return ctx.message.author.display_name.partition("(")[
        0
    ]  # names in this server are formatted as "name (nickname)"


def cow_format(message: str | None) -> str:
    """
    Formats a message as a cow saying it using the cowsay subprocess.
    :param message: The message to format.
    :return: The formatted message.
    """
    if not message:
        logging.info(
            "No message provided for cow_format. Using default blank stare message."
        )
        message = "* The cow stares at you blankly *"

    command = f'cowsay "{message}"'
    logging.info(f"Running cowsay command.")

    result = subprocess.run(
        [POWERSHELL_PATH, "-Command", command],
        capture_output=True,
        text=True,
        check=True,
    )
    logging.info("Cowsay command executed successfully.")
    return result.stdout


def talk_to_tim(message: str, name: str) -> str:
    """
    Sends a message to Tim and returns his response.
    :param message: The message to send to Tim.
    :param name: The name of the person sending the message.
    :return: Tim's response text with newline stripped.
    """
    logging.info(f"Sending message to Tim.")
    message = f"From {name}: {message}"
    response = TIM_CHAT.send_message(message).text.strip()
    logging.info(f"Received response from Tim.")
    return response


async def join(ctx):
    if ctx.message.author.voice:
        channel = ctx.message.author.voice.channel
        await channel.connect()
        logging.info(
            f"Successfully joined voice channel '{channel}' for user '{ctx.author}'."
        )
    else:
        logging.warning(
            f"User '{ctx.author}' attempted to use 'join' command but is not in a voice channel."
        )
        await send_error_embed(ctx, "You are not in a voice channel.")


async def leave(ctx):
    if ctx.voice_client:
        await ctx.guild.voice_client.disconnect()
        logging.info(
            f"Successfully left voice channel '{ctx.author.voice.channel}' for user '{ctx.author}'."
        )
    else:
        logging.warning(
            f"User '{ctx.author}' attempted to use 'leave' command but bot is not in a voice channel."
        )
        await send_error_embed(ctx, "I am not in a voice channel.")


bot.run(TOKEN)
