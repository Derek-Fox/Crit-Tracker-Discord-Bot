'''
Handles chat-related commands, such as cowsay and cowchat.
'''

import logging
from discord.ext import commands

from utils.helpers import get_msg_author_name, cow_format, talk_to_tim


class ChatCog(commands.Cog):
    def __init__(self, bot, tim_chat, pwsh_path) -> None:
        self.bot = bot
        self.tim_chat = tim_chat
        self.pwsh_path = pwsh_path

    @commands.command(name="cowsay", help="Get a cow to say something for you.")
    async def cowsay(
        self,
        ctx,
        *,
        message: str = commands.parameter(description="What you want the cow to say.", default=None),
    ):
        logging.info("Received 'cowsay' command from user '%s'.", ctx.author)
        formatted_message = cow_format(message, self.pwsh_path)
        await ctx.send(f"```{formatted_message}```")
        logging.info("Formatted cow message sent to user '%s'.", ctx.author)

    @commands.command(name="cowchat", help="Have a chat with Tim!")
    async def cowchat(
        self,
        ctx,
        *,
        message: str = commands.parameter(description="What you say to the cow.", default=None),
    ):
        logging.info(
            "Received 'cowchat' command from user '%s'. message=%s", ctx.author, message
        )

        if not message:
            logging.info(
                "No message provided for 'cowchat' by user '%s'. Sending default cow response.",
                ctx.author,
            )
            await self.cowsay(ctx)
            return

        name = get_msg_author_name(ctx)
        logging.info("Sending message to Tim the cow from user '%s'.", name)
        response = talk_to_tim(message, name, self.tim_chat)
        logging.info("Received response from Tim the cow.")
        await self.cowsay(ctx, message=response)
