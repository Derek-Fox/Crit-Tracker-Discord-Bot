"""Discord bot to allow access to spreadsheet containing crits directly from the server"""
from __future__ import print_function

import os
import os.path
import random
from num2words import num2words

import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
from dotenv import load_dotenv
from google.auth.transport.requests import Request
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SHEET_ID = os.getenv('SHEET_ID')
PAXORIAN_SHEETNAME=os.getenv('PAXORIAN_SHEETNAME') # not sure how important it is to have these as env vars
KRIGGSAN_SHEETNAME=os.getenv('KRIGGSAN_SHEETNAME') # ^

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
    if CREDS and CREDS.expired and CREDS.refresh_token:
        CREDS.refresh(Request())
    else:
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
async def session(ctx, campaign: str = commands.parameter(description='Campaign name, e.g. Paxorian')):
    """Increments the session number by 1"""
    valid = ['Paxorian', 'Kriggsan']
    warningimg = discord.File('res/warning.png')
    
    if campaign.title() not in valid:
        embed = discord.Embed()
        embed.title = '**Error**'
        embed.description = f'Received {campaign}, which is not a valid campaign name. Please try again.'
        embed.set_thumbnail(url='attachment://warning.png')
        embed.color = discord.Color.red()
        await ctx.send(file=warningimg, embed=embed)
        return
    new_session_number = get_and_update('H2', campaign.title())
    await ctx.send(
        embed=discord.Embed(title=f'Session number is now {new_session_number}',
        color=0xA2C4C9)
    )


@bot.command(name='add', help='Adds a crit of the specified type to the specified character.')
async def add(
    ctx,
    crit_type: str = commands.parameter(description='Type of crit, 1 or 20'),
    char_name: str = commands.parameter(description='Name of character, e.g. Morbo')
):
    """Adds a crit of the specified type to the specified character."""
    
    cell = ''
    sheet = ''
    embed = discord.Embed()
    sad_emoji = list('😞😒😟😠🙁😣😖😨😰😧😢😥😭😵‍💫')
    happy_emoji = list('😀😁😃😄😆😉😊😋😎😍🙂🤗🤩😏')
    file = ''
    sound = ''
    warningimg = discord.File('res/warning.png')
    nat20img = discord.File('res/nat20.png')
    nat1img = discord.File('res/nat1.png')
    
    char_name_upper = char_name.upper()
    paxorian_chars = ['ZOHAR', 'MORBO', 'GRUNT', 'CELEMINE', 'ORWYND'] #characters listed in order of appearance on the sheet
    paxorian_chars_colors = [0x8E7CC3, 0x38761D, 0x000000, 0x351C75, 0xEB7AB1] #corresponding colors for paxorian_chars
    kriggsan_chars = ['CIRRUS', 'DAELAN', 'LAVENDER', 'LORELAI', 'TORMYTH']
    kriggsan_chars_colors = [0xd8e5f4,0xcc0000,0xff00ff,0x09438b,0x351c75]
    
    #get the sheet and row for the character
    if char_name_upper in paxorian_chars:
        sheet = PAXORIAN_SHEETNAME
        cell = paxorian_chars.index(char_name_upper) + 2
        embed.color = paxorian_chars_colors[cell - 2]
    elif char_name_upper in kriggsan_chars:
        sheet = KRIGGSAN_SHEETNAME
        cell = kriggsan_chars.index(char_name_upper) + 2
        embed.color = kriggsan_chars_colors[cell - 2]
    elif char_name_upper == 'TEST':
        sheet = PAXORIAN_SHEETNAME
        cell = 50
        embed.color = 0xffffff
    else:
        embed.title = '**Error**'
        embed.description = f'Received {char_name}, which is not a valid character name. Please try again.'
        embed.set_thumbnail(url='attachment://warning.png')
        embed.color = discord.Color.red()
        await ctx.send(file=warningimg, embed=embed)
        return

    #get the column for the crit type
    if crit_type == '20':
        cell = 'B' + str(cell)
        embed.title = f'20 added! {random.choice(happy_emoji)}'
        file = nat20img
        embed.set_thumbnail(url='attachment://nat20.png')
        sound = 'res/success.wav'
    elif crit_type == '1':
        cell = 'C' + str(cell)
        embed.title = f'1 added. {random.choice(sad_emoji)}'
        file = nat1img
        embed.set_thumbnail(url='attachment://nat1.png')
        sound = 'res/fail.mp3'
    else:
        embed.title = '**Error**'
        embed.description = f'Received {crit_type}, which is not a valid crit type. Please try again.'
        embed.set_thumbnail(url='attachment://warning.png')
        embed.color = discord.Color.red()
        await ctx.send(file=warningimg, embed=embed)
        return

    #send crit to sheet and update embed with new number of crits
    num_crits = get_and_update(cell, sheet)
    embed.description = f'{char_name.title()} now has {num2words(num_crits)} {crit_type}s!'

    #send embed to discord
    await ctx.send(file=file, embed=embed)
    
    #play sound if sounds are enabled
    if ctx.voice_client:
        play(ctx, sound)
    
@bot.command(name='sounds', help='Enable sounds for crits for the current channel.')
async def sounds(
    ctx,
    status: str = commands.parameter(description='on or off')
):
    embed = discord.Embed()
    embed.title = f'Sounds {status}!'
    embed.color = discord.Color.green() if status == 'on' else discord.Color.red()
    await ctx.send(embed=embed)
    
    if status == 'on':
        await join(ctx)
    elif status == 'off':
        await leave(ctx)
    
def play(ctx, file):
    voice = ctx.guild.voice_client
    source = FFmpegPCMAudio(file)
    voice.play(source)
    
async def join(ctx):
    warningimg = discord.File('res/warning.png')
    
    if ctx.message.author.voice:
        channel = ctx.message.author.voice.channel
        await channel.connect()
    else:
        embed = discord.Embed()
        embed.title = '**Error**'
        embed.description = "You are not in a voice channel. Please join one and try again."
        embed.set_thumbnail(url='attachment://warning.png')
        embed.color = discord.Color.red()
        await ctx.send(file=warningimg, embed=embed)

async def leave(ctx):
    warningimg = discord.File('res/warning.png')
    
    if ctx.voice_client:
        await ctx.guild.voice_client.disconnect()
    else:
        embed = discord.Embed()
        embed.title = '**Error**'
        embed.description = "I am not in a voice channel."
        embed.set_thumbnail(url='attachment://warning.png')
        embed.color = discord.Color.red()
        await ctx.send(file=warningimg, embed=embed)

bot.run(TOKEN)
