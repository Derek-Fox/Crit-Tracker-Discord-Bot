from __future__ import print_function

import os
import os.path
import random

import discord
import google.auth
from discord.ext import commands
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def update_values(spreadsheet_id, range_name, value_input_option, _values, creds):
    
    try:

        service = build('sheets', 'v4', credentials=creds)
       
        body = {
            'values': _values
        }
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range=range_name,
            valueInputOption=value_input_option, body=body).execute()
        print(f"{result.get('updatedCells')} cells updated.")
        return result
    except HttpError as error:
        print(f"An error occurred: {error}")
        return error
    
def get_values(spreadsheet_id, range_name, creds):
    
    try:
        service = build('sheets', 'v4', credentials=creds)

        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name).execute()
        rows = result.get('values', [])
        print(f"{len(rows)} rows retrieved")
        return result
    except HttpError as error:
        print(f"An error occurred: {error}")
        return error
    
def get_and_update(cell, creds):
    value = get_values("1FWsrc8M03umsn2uBBERj7my-HyaxXepMsSv25-8kVz8", cell, creds).get('values', [])
    
    update_values("1FWsrc8M03umsn2uBBERj7my-HyaxXepMsSv25-8kVz8", cell, "USER_ENTERED", [[int(value[0][0]) + 1]], creds)

intents = discord.Intents(messages=True, guilds=True)
intents.message_content = True

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='$', intents=intents)

@bot.command(name='add')
async def add(ctx, crit_type, char_name):
    creds = None
   
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                r'C:\Users\Redux\Documents\Coding Stuff\Crit Tracker Discord Bot\credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    
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
        
    if crit_type == '20':
        cell = "B" + cell
        response = '20 added! B)'
    elif crit_type == '1':
        cell = "C" + cell
        response = '1 added :('
    
    get_and_update(cell, creds)
        
    await ctx.send(response)

bot.run(TOKEN)
