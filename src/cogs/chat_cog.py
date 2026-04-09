"""
Handles chat-related commands, such as cowsay and cowchat.
"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import get_msg_author_name, cow_format, talk_to_tim


class ChatCog(commands.Cog):
    def __init__(self, bot, tim_chat, pwsh_path) -> None:
        self.bot = bot
        self.tim_chat = tim_chat
        self.pwsh_path = pwsh_path

    @app_commands.command(name="cowsay", description="Get a cow to say something for you.")
    async def cowsay(
            self,
            inter: discord.Interaction,
            message: str
    ):
        """
        Get a cow to say something for you.

        :param inter: discord.Interaction instance
        :param message: What you want the cow to say.
        """
        logging.info("Received 'cowsay' command from user '%s'.", inter.user.display_name)
        formatted_message = cow_format(message, self.pwsh_path)
        await inter.response.send_message(f"```{formatted_message}```")
        logging.info("Formatted cow message sent to user '%s'.", inter.user.display_name)

    @app_commands.command(name="cowchat", description="Have a chat with Tim the Magic Cow!")
    async def cowchat(
            self,
            inter: discord.Interaction,
            message: str
    ):
        """
        Have a chat with Tim the Magic Cow!

        :param inter: discord.Interaction instance
        :param message: What you want to say to Tim
        """
        await inter.response.defer()  # defer because the model can take longer than 3 second limit

        logging.info(
            "Received 'cowchat' command from user '%s'. message=%s", inter.user.display_name, message
        )

        if not message:
            logging.info(
                "No message provided for 'cowchat' by user '%s'.",
                inter.user.display_name,
            )
            return

        name = get_msg_author_name(inter)
        logging.info("Sending message to Tim the cow from user '%s', display name '%s.", inter.user.display_name, name)
        response = talk_to_tim(message, name, self.tim_chat)
        logging.info("Received response from Tim the cow.")

        formatted_message = cow_format(response, self.pwsh_path)
        await inter.followup.send(f"```{formatted_message}```")
        logging.info("Formatted cow message sent to user '%s'.", inter.user.display_name)
