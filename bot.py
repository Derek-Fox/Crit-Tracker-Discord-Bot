"""Discord bot to allow access to spreadsheet containing crits directly from the server"""
from __future__ import print_function

import os
import os.path

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
    description="This bot will add crits directly to the spreadsheet for you!",
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
    """Updates values on the spreadsheet in the given range with given values"""
    try:
        service = build('sheets', 'v4', credentials=CREDS)
        body = {'values': _values}
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption=value_input_option,
            body=body
        ).execute()
        print(f"{result.get('updatedCells')} cells updated.")
        return result
    except HttpError as error:
        print(f"An error occurred: {error}")
        return error


def get_values(spreadsheet_id, range_name):
    """Returns values from the spreadsheet from the specified range"""
    try:
        service = build('sheets', 'v4', credentials=CREDS)
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        rows = result.get('values', [])
        print(f"{len(rows)} rows retrieved")
        return result
    except HttpError as error:
        print(f"An error occurred: {error}")
        return error


def get_and_update(cell):
    """Increments the value of the given cell by 1."""
    value = get_values(SHEET_ID, cell).get('values', [])

    update_values(SHEET_ID, cell, "USER_ENTERED",
                  [[int(value[0][0]) + 1]])

    print(f"{cell} updated!")

    return int(value[0][0]) + 1


@bot.command(name='session', help="Increments the session number by one.")
async def session(ctx):
    """Increments the session number by 1"""
    new_session_number = get_and_update("H2")
    await ctx.send(f"Session number is now {new_session_number}")


@bot.command(name='add', help="Adds a crit of the specified type to the specified character.")
async def add(
    ctx,
    crit_type: str = commands.parameter(description="Type of crit, 1 or 20"),
    char_name: str = commands.parameter(
        description="Name of character, e.g. Morbo")
):
    """Adds a crit of the specified type to the specified character."""
    cell = ""
    match char_name.upper():
        case "ZOHAR":
            cell = "2"
        case "MORBO":
            cell = "3"
        case "GRUNT":
            cell = "4"
        case "CELEMINE":
            cell = "5"
        case "ORWYND":
            cell = "6"
        case "BORMOD":
            cell = "9"
        case "OATMEAL":
            cell = "10"
        case _:
            await ctx.send("Please enter a valid character name!")
            return

    if crit_type == '20':
        cell = "B" + cell
        response = '20 added! B)'
    elif crit_type == '1':
        cell = "C" + cell
        response = '1 added :('
    else:
        await ctx.send("Please enter a valid crit type!")
        return

    num_crits = get_and_update(cell)
    response = f"{response}\n{char_name} now has {num_crits} {crit_type}s!"

    await ctx.send(response)

bot.run(TOKEN)
