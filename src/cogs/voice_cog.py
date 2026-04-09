"""
Handles voice-related commands, such as joining/leaving voice channels and enabling/disabling sounds.
"""
import asyncio
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands
import logging

from utils.helpers import send_error_embed


class VoiceCog(commands.Cog):
    """Cog that handles voice-related functionality for the Discord bot.

    This cog manages voice channel operations including joining/leaving channels
    and controlling sound effects playback.
    """

    def __init__(self, bot) -> None:
        """Initialize the VoiceCog with a bot instance."""
        self.bot = bot

    @staticmethod
    async def join(inter: discord.Interaction) -> bool:
        """Join the voice channel of the user who invoked the command."""
        if not inter.user.voice:
            logging.warning(
                "User '%s' attempted to use 'join' command but is not in a voice channel.",
                inter.user.display_name,
            )
            await send_error_embed(inter, "You are not in a voice channel.")
            return False

        channel = inter.user.voice.channel
        try:
            await channel.connect()
            logging.info(
                "Successfully joined voice channel '%s' for user '%s'.",
                channel,
                inter.user.display_name,
            )
            return True
        except discord.ClientException | asyncio.TimeoutError as e:
            logging.warning("Bot failed to join voice channel '%s': %s", channel, e)
            return False

    @staticmethod
    async def leave(inter) -> bool:
        """Leave the current voice channel."""
        if not inter.guild.voice_client:
            logging.warning(
                "User '%s' attempted to use 'leave' command but bot is not in a voice channel.",
                inter.user.display_name,
            )
            await send_error_embed(inter, "I am not in a voice channel.")
            return False

        await inter.guild.voice_client.disconnect(force=True)
        logging.info(
            "Successfully left voice channel for user '%s'.",
            inter.user.display_name,
        )
        return True

    @app_commands.command(name="sounds", description="Enables/disables sounds for the bot.")
    async def sounds(
            self,
            inter: discord.Interaction,
            status: Literal["on", "off"]
    ):
        """Enable or disable sound effects for the bot.

        :param self: The instance of the VoiceCog class
        :param inter: The discord.Interaction instance
        :param status: The desired status of sounds
        """
        logging.info(
            "Received 'sounds' command from user '%s' with status='%s'.",
            inter.user.display_name,
            status,
        )

        if status not in ["on", "off"]:
            logging.warning("Invalid status '%s' provided by user '%s'.", status, inter.user.display_name)
            await send_error_embed(inter, f"Received invalid status {status}. Please try again.")
            return

        if await self.join(inter) if status == "on" else await self.leave(inter):
            embed = discord.Embed(
                title=f"Sounds {status}!",
                color=discord.Color.green() if status == "on" else discord.Color.red(),
            )
            await inter.response.send_message(embed=embed)
        else:
            await send_error_embed(inter, "Something went wrong. Please try again.")
