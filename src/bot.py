"""
Initializes the Discord bot, loads cogs, and sets up the
necessary configurations for the bot to run.
"""

import logging
import discord
from discord.ext import commands

from cogs.core_cog import CoreCog
from cogs.crit_cog import CritCog
from cogs.chat_cog import ChatCog
from cogs.voice_cog import VoiceCog


async def init_bot(sheet_handler, tim_chat, pwsh_path, config):
    """
    Initializes the Discord bot with the specified cogs and configurations.

    :param sheet_handler: SheetsHandler instance for interacting with Google Sheets
    :param tim_chat: Tim chat instance for GenAI interactions
    :param pwsh_path: Path to PowerShell executable
    :param config: Configuration dictionary for the bot
    """
    # Set up intents for the bot to allow message content, which is required for command processing and responding to user messages.
    intents = discord.Intents.default()
    intents.message_content = True
    logging.info("Discord intents configured to allow message content.")

    # Initialize the bot
    bot = commands.Bot(
        command_prefix="$",
        intents=intents,
        description="This bot will add crits directly to the spreadsheet for you!",
        help_command=commands.DefaultHelpCommand(no_category="Commands"),
    )
    logging.info("Discord bot instance created successfully.")

    # Load cogs for functionality
    await bot.add_cog(CoreCog(bot))
    await bot.add_cog(CritCog(bot, sheet_handler, tim_chat, pwsh_path, config))
    await bot.add_cog(ChatCog(bot, tim_chat, pwsh_path))
    await bot.add_cog(VoiceCog(bot))
    logging.info("Cogs loaded successfully.")

    return bot
