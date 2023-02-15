# bot.py
import os
import random

import discord
from discord.ext import commands
from dotenv import load_dotenv

intents = discord.Intents(messages=True, guilds=True)
intents.message_content = True

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command(name='add')
async def add(ctx, crit_type):

    if crit_type == '20':
        response = '20 added'
    elif crit_type == '1':
        response = '1 added'
        
    await ctx.send(response)

bot.run(TOKEN)
