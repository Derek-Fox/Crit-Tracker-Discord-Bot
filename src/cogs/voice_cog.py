"""
Handles voice-related commands, such as joining/leaving voice channels and enabling/disabling sounds.
"""

import discord
from discord.ext import commands
import logging

from utils.helpers import send_error_embed


class VoiceCog(commands.Cog):
    """Cog that handles voice-related functionality for the Discord bot.

    This cog manages voice channel operations including joining/leaving channels
    and controlling sound effects playback.
    """

    def __init__(self, bot) -> None:
        """Initialize the VoiceCog with a bot instance.

        Args:
            bot: The Discord bot instance to associate with this cog.
        """
        self.bot = bot

    async def join(self, ctx) -> bool:
        """Join the voice channel of the user who invoked the command.

        Connects the bot to the same voice channel as the invoking user. If the user
        is not in a voice channel, sends an error message.

        Args:
            ctx (discord.ext.commands.Context): The command context containing information
                about the user and guild.

        Note:
            This is an internal method typically called by other commands like 'sounds on'.
        """
        if ctx.message.author.voice:
            channel = ctx.message.author.voice.channel
            try:
                await channel.connect()
                logging.info(
                    "Successfully joined voice channel '%s' for user '%s'.",
                    channel,
                    ctx.author,
                )
                return True
            except discord.ClientException as e:
                logging.warning("Bot failed to join voice channel '%s': %s", channel, e)
                return False
        else:
            logging.warning(
                "User '%s' attempted to use 'join' command but is not in a voice channel.",
                ctx.author,
            )
            await send_error_embed(ctx, "You are not in a voice channel.")
            return False

    async def leave(self, ctx) -> bool:
        """Leave the current voice channel.

        Disconnects the bot from the voice channel it is currently connected to.
        If the bot is not in any voice channel, sends an error message.

        Args:
            ctx (discord.ext.commands.Context): The command context containing information
                about the guild and voice client.

        Note:
            This is an internal method typically called by other commands like 'sounds off'.
        """
        if ctx.voice_client:
            await ctx.guild.voice_client.disconnect(force=True)
            logging.info(
                "Successfully left voice channel '%s' for user '%s'.",
                ctx.author.voice.channel,
                ctx.author,
            )
            return True
        else:
            logging.warning(
                "User '%s' attempted to use 'leave' command but bot is not in a voice channel.",
                ctx.author,
            )
            await send_error_embed(ctx, "I am not in a voice channel.")
            return False

    @commands.command(name="sounds", help="Enables/disables sounds for the bot.")
    async def sounds(
        self, ctx, status: str = commands.parameter(description="On or off.")
    ):
        """Enable or disable sound effects for the bot.

        This command controls whether the bot plays sounds when events occur. Setting
        status to 'on' will join the user's voice channel, and 'off' will disconnect
        the bot from the current voice channel.

        Args:
            ctx (discord.ext.commands.Context): The command context.
            status (str): Either 'on' to enable sounds or 'off' to disable sounds.
                Must be one of these two values.

        Raises:
            Sends an error embed if an invalid status is provided.

        Example:
            !sounds on     # Enable sounds and join user's voice channel
            !sounds off    # Disable sounds and leave voice channel
        """
        logging.info(
            "Received 'sounds' command from user '%s' with status='%s'.",
            ctx.author,
            status,
        )

        if status not in ["on", "off"]:
            logging.warning(
                "Invalid status '%s' provided by user '%s'.", status, ctx.author
            )
            await send_error_embed(
                ctx,
                f"Received invalid status {status}. Please try again.",
            )
            return

        success = False
        if status == "on":
            success = await self.join(ctx)
        elif status == "off":
            success = await self.leave(ctx)

        if success:
            embed = discord.Embed(
                title=f"Sounds {status}!",
                color=discord.Color.green() if status == "on" else discord.Color.red(),
            )
            await ctx.send(embed=embed)
