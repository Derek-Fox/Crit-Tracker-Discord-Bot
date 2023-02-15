import os

import discord
from dotenv import load_dotenv

intents = discord.Intents(messages=True, guilds=True)
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

client = discord.Client(command_prefix='!', intents=intents)

@client.event
async def on_ready():
    guild = discord.utils.get(client.guilds, name=GUILD)
        
    print(
        f'{client.user} has connected to guild: \n'
        f'{guild.name}(id: {guild.id})'
    )
    
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if message.content == 'add 20':
        await message.channel.send('20 added')
        

client.run(TOKEN)



