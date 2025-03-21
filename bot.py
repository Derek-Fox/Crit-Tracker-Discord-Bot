"""Discord bot to allow access to spreadsheet containing crits directly from the server"""
from __future__ import print_function

import os.path
import random
import subprocess

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

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SHEET_ID = os.getenv('SHEET_ID')
PAXORIAN_SHEETNAME = os.getenv('PAXORIAN_SHEETNAME')  # not sure how important it is to have these as env vars
KRIGGSAN_SHEETNAME = os.getenv('KRIGGSAN_SHEETNAME')  # ^
POWERSHELL_PATH = rf"{os.getenv('POWERSHELL_PATH')}"

# Initialize the model
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
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
    generation_config=genai.GenerationConfig(temperature=2.0)  # make tim creative :)
)
TIM_CHAT = TIM.start_chat()

if not TOKEN:
    print('No token found. Exiting...')
    exit(1)
if not SHEET_ID:
    print('No SHEET_ID found. Exiting...')
    exit(1)
if not PAXORIAN_SHEETNAME:
    print('No PAXORIAN_SHEETNAME found. Exiting...')
    exit(1)
if not KRIGGSAN_SHEETNAME:
    print('No KRIGGSAN_SHEETNAME found. Exiting...')
    exit(1)

INTENTS = discord.Intents.default()
INTENTS.message_content = True

bot = commands.Bot(
    command_prefix='$',
    intents=INTENTS,
    description='This bot will add crits directly to the spreadsheet for you!',
    help_command=commands.DefaultHelpCommand(no_category='Commands')
)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
CREDS = None
if os.path.exists('token.json'):
    CREDS = Credentials.from_authorized_user_file('token.json', SCOPES)
# If there are no (valid) credentials available, let the user log in.
if not CREDS or not CREDS.valid:
    try:
        if CREDS and CREDS.expired and CREDS.refresh_token:
            CREDS.refresh(Request())
        else:
            raise RefreshError
    except RefreshError:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        flow.authorization_url(access_type='offline', include_granted_scopes='true')
        CREDS = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open('token.json', mode='w', encoding='UTF-8') as token:
        token.write(CREDS.to_json())


def update_values(spreadsheet_id, subsheet_id, range_name, value_input_option, _values):
    """Updates values on the spreadsheet in the given range with given values"""
    range_name = f'{subsheet_id}!{range_name}'
    try:
        service = build('sheets', 'v4', credentials=CREDS)
        body = {'values': _values}
        # pylint: disable=maybe-no-member
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption=value_input_option,
            body=body
        ).execute()
        print(f'{result.get("updatedCells")} cells updated.')
        return result
    except HttpError as error:
        print(f'An error occurred: {error}')
        return error


def get_values(spreadsheet_id, subsheet_id, range_name):
    """Returns values from the spreadsheet from the specified range"""
    range_name = f'{subsheet_id}!{range_name}'
    try:
        service = build('sheets', 'v4', credentials=CREDS)
        # pylint: disable=maybe-no-member
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        rows = result.get('values', [])
        print(f'{len(rows)} rows retrieved')
        return result
    except HttpError as error:
        print(f'An error occurred: {error}')
        return error


def get_and_update(cell, subsheet_id):
    """Increments the value of the given cell by 1."""
    value = get_values(SHEET_ID, subsheet_id, cell).get('values', [])

    update_values(SHEET_ID, subsheet_id, cell, 'USER_ENTERED',
                  [[int(value[0][0]) + 1]])

    print(f'{subsheet_id}:{cell} updated!')

    return int(value[0][0]) + 1


@bot.event
async def on_ready():
    """Sets up the bot's status"""
    game = discord.Game('$help')
    await bot.change_presence(status=discord.Status.dnd, activity=game)


@bot.command(name='session', help='Increments the session number by one.')
async def session(ctx, campaign: str = commands.parameter(description='Campaign name, e.g. Paxorian.')):
    """Increments the session number by 1"""
    campaign_title = campaign.title()
    if campaign_title not in ['Paxorian', 'Kriggsan']:
        await send_error_embed(ctx, f'Received {campaign}, which is not a valid campaign name. Please try again.')
        return
    new_session_number = get_and_update('H2', campaign_title)
    await ctx.send(embed=discord.Embed(title=f'Session number is now {new_session_number}', color=0xA2C4C9))


CHARACTER_MAP = {
    'ZOHAR': {'color': 0x8E7CC3, 'sheet': PAXORIAN_SHEETNAME, 'row': '2'},
    'MORBO': {'color': 0x38761D, 'sheet': PAXORIAN_SHEETNAME, 'row': '3'},
    'GRUNT': {'color': 0x000000, 'sheet': PAXORIAN_SHEETNAME, 'row': '4'},
    'CELEMINE': {'color': 0x351C75, 'sheet': PAXORIAN_SHEETNAME, 'row': '5'},
    'ORWYND': {'color': 0xEB7AB1, 'sheet': PAXORIAN_SHEETNAME, 'row': '6'},
    'CIRRUS': {'color': 0xd8e5f4, 'sheet': KRIGGSAN_SHEETNAME, 'row': '2'},
    'DAELAN': {'color': 0xcc0000, 'sheet': KRIGGSAN_SHEETNAME, 'row': '3'},
    'LAVENDER': {'color': 0xff00ff, 'sheet': KRIGGSAN_SHEETNAME, 'row': '4'},
    'LORELAI': {'color': 0x09438b, 'sheet': KRIGGSAN_SHEETNAME, 'row': '5'},
    'TORMYTH': {'color': 0x351c75, 'sheet': KRIGGSAN_SHEETNAME, 'row': '6'},
    'TEST': {'color': 0x000000, 'sheet': PAXORIAN_SHEETNAME, 'row': '50'}
}

CRIT_TYPE_MAP = {
    '20': {
        'col': 'B',
        'title': 'Nat 20 added! {emoji}',
        'img': 'res/nat20.png',
        'sound': 'res/success.wav'
    },
    '1': {
        'col': 'C',
        'title': 'Nat 1 added. {emoji}',
        'img': 'res/nat1.png',
        'sound': 'res/fail.mp3'
    }
}

happy_emoji = list('😀😁😃😄😆😉😊😋😎😍🙂🤗🤩😏')
sad_emoji = list('😞😒😟😠🙁😣😖😨😰😧😢😥😭😵‍💫')


async def send_error_embed(ctx, message):
    embed = discord.Embed(title='**Error**', description=message, color=discord.Color.red())
    embed.set_thumbnail(url='attachment://warning.png')
    await ctx.send(file=discord.File('res/warning.png'), embed=embed)


def build_embed(title, crit_type, char_name, num_crits, color, cow_msg):
    embed = discord.Embed(title=title.format(emoji=random.choice(happy_emoji if crit_type == '20' else sad_emoji)),
                          color=color)
    embed.set_thumbnail(url=f'attachment://nat{crit_type}.png')
    embed.description = f'{char_name.title()} now has {num2words(num_crits)} Nat {crit_type}s!\n{cow_msg}'
    return embed


def play_sound(ctx, sound):
    if ctx.voice_client:
        voice = ctx.guild.voice_client
        source = FFmpegPCMAudio(sound)
        voice.play(source)


@bot.command(name='add', help='Adds a crit of the specified type to the specified character.')
async def add(
        ctx,
        crit_type: str = commands.parameter(description='Type of crit, 1 or 20.'),
        char_name: str = commands.parameter(description='Name of character, e.g. Morbo.')
):
    char_info = CHARACTER_MAP.get(char_name.upper())
    if not char_info:
        await send_error_embed(ctx, f'Received {char_name}, which is not a valid character name. Please try again.')
        return

    crit_info = CRIT_TYPE_MAP.get(crit_type)
    if not crit_info:
        await send_error_embed(ctx, f'Received {crit_type}, which is not a valid crit type. Please try again.')
        return

    cell = crit_info['col'] + char_info['row']
    num_crits = get_and_update(cell, char_info['sheet'])

    tim_response = talk_to_tim(f"{char_name.title()} rolled a Nat {crit_type}! They now have {num_crits}!", get_msg_author_name(ctx))
    embed = build_embed(crit_info['title'], crit_type, char_name, num_crits, char_info['color'], f'```{cow_format(tim_response)}```')
    await ctx.send(file=discord.File(crit_info['img']), embed=embed)

    play_sound(ctx, crit_info['sound'])


@bot.command(name='sounds', help='Enable sounds for crits for the current channel.')
async def sounds(
        ctx,
        status: str = commands.parameter(description='On or off.')
):
    if status not in ['on', 'off']:
        await send_error_embed(ctx, f'Received {status}, which is not a valid status. Please try again.')
        return

    embed = discord.Embed(title=f'Sounds {status}!',
                          color=discord.Color.green() if status == 'on' else discord.Color.red())
    await ctx.send(embed=embed)

    if status == 'on':
        await join(ctx)
    elif status == 'off':
        await leave(ctx)


@bot.command(name='cowsay', help='Get a cow to say something for you.')
async def cowsay(
        ctx,
        *, message: str = commands.parameter(description='What you want the cow to say.', default=None)
):
    await ctx.send(f'```{cow_format(message)}```')


@bot.command(name='cowchat', help='Have a conversation with Tim the cow.')
async def cowchat(
        ctx,
        *, message: str = commands.parameter(description='What you say to the cow.', default=None)
):
    if not message:
        await cowsay(ctx, message=None)
        return

    name = get_msg_author_name(ctx)

    response = talk_to_tim(message, name)
    await cowsay(ctx, message=response)


def get_msg_author_name(ctx):
    return ctx.message.author.display_name.partition('(')[0]  # names in this server are formatted as "name (nickname)"


def cow_format(message: str | None) -> str:
    """
    Formats a message as a cow saying it using the cowsay subprocess.
    :param message: The message to format.
    :return: The formatted message.
    """
    if not message: message = '* The cow stares at you blankly *'

    command = f'cowsay "{message}"'

    result = subprocess.run(
        [POWERSHELL_PATH, "-Command", command],
        capture_output=True,
        text=True,
        check=True
    )

    return result.stdout


def talk_to_tim(message: str, name: str) -> str:
    """
    Sends a message to Tim and returns his response.
    :param message: The message to send to Tim.
    :param name: The name of the person sending the message.
    :return: Tim's response text with newline stripped.
    """
    message = f"From {name}: {message}"
    return TIM_CHAT.send_message(message).text.strip()


async def join(ctx):
    if ctx.message.author.voice:
        channel = ctx.message.author.voice.channel
        await channel.connect()
    else:
        await send_error_embed(ctx, 'You are not in a voice channel.')


async def leave(ctx):
    if ctx.voice_client:
        await ctx.guild.voice_client.disconnect()
    else:
        await send_error_embed(ctx, 'I am not in a voice channel.')


bot.run(TOKEN)
