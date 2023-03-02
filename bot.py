'''Discord bot to allow access to spreadsheet containing crits directly from the server'''
from __future__ import print_function

import os
import os.path
import random
from num2words import num2words

import discord
from discord.ext import commands
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SHEET_ID = os.getenv('SHEET_ID')

INTENTS = discord.Intents(messages=True, guilds=True)
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
    if CREDS and CREDS.expired and CREDS.refresh_token:
        CREDS.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        CREDS = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open('token.json', mode='w', encoding='UTF-8') as token:
        token.write(CREDS.to_json())


def update_values(spreadsheet_id, range_name, value_input_option, _values):
    '''Updates values on the spreadsheet in the given range with given values'''
    try:
        service = build('sheets', 'v4', credentials=CREDS)
        body = {'values': _values}
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


def get_values(spreadsheet_id, range_name):
    '''Returns values from the spreadsheet from the specified range'''
    try:
        service = build('sheets', 'v4', credentials=CREDS)
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


def get_and_update(cell):
    '''Increments the value of the given cell by 1.'''
    value = get_values(SHEET_ID, cell).get('values', [])

    update_values(SHEET_ID, cell, 'USER_ENTERED',
                  [[int(value[0][0]) + 1]])

    print(f'{cell} updated!')

    return int(value[0][0]) + 1


@bot.event
async def on_ready():
    '''Sets up the bot's status'''
    game = discord.Game('$help')
    await bot.change_presence(status=discord.Status.dnd, activity=game)


@bot.command(name='session', help='Increments the session number by one.')
async def session(ctx):
    '''Increments the session number by 1'''
    new_session_number = get_and_update('H2')
    await ctx.send(f'Session number is now {new_session_number}')


@bot.command(name='add', help='Adds a crit of the specified type to the specified character.')
async def add(
    ctx,
    crit_type: str = commands.parameter(description='Type of crit, 1 or 20'),
    char_name: str = commands.parameter(
        description='Name of character, e.g. Morbo')
):
    '''Adds a crit of the specified type to the specified character.'''
    cell = ''
    embed = discord.Embed()
    match char_name.upper():
        case 'ZOHAR':
            cell = '2'
            embed.color = 0x8E7CC3
        case 'MORBO':
            cell = '3'
            embed.color = 0x38761D
        case 'GRUNT':
            cell = '4'
            embed.color = 0x000000
        case 'CELEMINE':
            cell = '5'
            embed.color = 0x351C75
        case 'ORWYND':
            cell = '6'
            embed.color = 0xEB7AB1
        case 'BORMOD':
            cell = '9'
        case 'OATMEAL':
            cell = '10'
        case _:
            embed.title = "**Error** ⚠️"
            embed.description = f"Received {char_name}, which is not a valid character name. Please try again."
            embed.color = discord.Color.red()
            await ctx.send(embed=embed)
            return

    sad_emoji = list('😞😒😟😠🙁😣😖😨😰😧😢😥😭😵‍💫')
    happy_emoji = list('😀😁😃😄😆😉😊😋😎😍🙂🤗🤩😏')
    if crit_type == '20':
        cell = 'B' + cell
        embed.title = f'20 added! {random.choice(happy_emoji)}'
    elif crit_type == '1':
        cell = 'C' + cell
        embed.title = f'1 added {random.choice(sad_emoji)}'
    else:
        embed.title = "**Error** ⚠️"
        embed.description = f"Received {crit_type}, which is not a valid crit type. Please try again."
        embed.color = discord.Color.red()
        await ctx.send(embed=embed)
        return

    num_crits = get_and_update(cell)
    embed.description = f'{char_name} now has {num2words(num_crits)} {crit_type}s!'

    await ctx.send(embed=embed)

bot.run(TOKEN)
