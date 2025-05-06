"""Discord bot to allow access to spreadsheet containing crits directly from the server"""

import random
import subprocess

import discord
from discord import FFmpegPCMAudio
from discord.ext import commands
from num2words import num2words
import logging


def init_bot(sheet_handler, tim_chat, pwsh_path, char_config):
    character_map = char_config["character_map"]
    crit_type_map = char_config["crit_type_map"]

    happy_emoji = list("😀😁😃😄😆😉😊😋😎😍🙂🤗🤩😏")
    sad_emoji = list("😞😒😟😠🙁😣😖😨😰😧😢😥😭😵‍💫")

    INTENTS = discord.Intents.default()
    INTENTS.message_content = True
    logging.info("Discord intents configured to allow message content.")

    bot = commands.Bot(
        command_prefix="$",
        intents=INTENTS,
        description="This bot will add crits directly to the spreadsheet for you!",
        help_command=commands.DefaultHelpCommand(no_category="Commands"),
    )

    logging.info("Discord bot instance created successfully.")

    @bot.event
    async def on_ready():
        """Sets up the bot's status"""
        logging.info(f"Bot logged in as {bot.user}.")
        game = discord.Game("$help")
        await bot.change_presence(status=discord.Status.dnd, activity=game)

    @bot.command(name="session", help="Increments the session number by one.")
    async def session(
        ctx,
        campaign: str = commands.parameter(description="Campaign name, e.g. Paxorian."),
    ):
        campaign_title = campaign.title()
        if campaign_title not in ["Paxorian", "Kriggsan"]:
            await send_error_embed(
                ctx,
                f"Received {campaign}, which is not a valid campaign name. Please try again.",
            )
            return
        new_session_number = sheet_handler.increment_cell("H2", campaign_title)
        await ctx.send(
            embed=discord.Embed(
                title=f"Session number is now {new_session_number}", color=0xA2C4C9
            )
        )
        logging.info(f"Campaign {campaign_title} incremented to {new_session_number}.")

    async def send_error_embed(ctx, message):
        embed = discord.Embed(
            title="**Error**", description=message, color=discord.Color.red()
        )
        embed.set_thumbnail(url="attachment://warning.png")
        await ctx.send(file=discord.File("res/warning.png"), embed=embed)

    def build_crit_embed(title, crit_type, char_name, num_crits, color, cow_msg):
        embed = discord.Embed(
            title=title.format(
                emoji=random.choice(happy_emoji if crit_type == "20" else sad_emoji)
            ),
            color=color,
        )
        embed.set_thumbnail(url=f"attachment://nat{crit_type}.png")
        embed.description = f"{char_name.title()} now has {num2words(num_crits)} Nat {crit_type}s!\n{cow_msg}"
        return embed

    def play_sound(ctx, sound):
        if ctx.voice_client:
            voice = ctx.guild.voice_client
            source = FFmpegPCMAudio(sound)
            voice.play(source)
            logging.info(f"Sound '{sound}' played in channel '{voice.channel}'.")

    @bot.command(name="add", help="Adds a crit to the spreadsheet.")
    async def add(
        ctx,
        crit_type: str = commands.parameter(description="Type of crit, 1 or 20."),
        char_name: str = commands.parameter(
            description="Name of character, e.g. Morbo."
        ),
    ):
        logging.info(
            f"Received 'add' command from user '{ctx.author}' with crit_type='{crit_type}' and char_name='{char_name}'."
        )

        char_info = character_map.get(char_name.upper())
        if not char_info:
            logging.warning(
                f"Invalid character name '{char_name}' provided by user '{ctx.author}'."
            )
            await send_error_embed(
                ctx,
                f"Received {char_name}, which is not a valid character name. Please try again.",
            )
            return

        crit_info = crit_type_map.get(crit_type)
        if not crit_info:
            logging.warning(
                f"Invalid crit type '{crit_type}' provided by user '{ctx.author}'."
            )
            await send_error_embed(
                ctx,
                f"Received {crit_type}, which is not a valid crit type. Please try again.",
            )
            return

        cell = crit_info["col"] + char_info["row"]
        logging.info(
            f"Updating crit count for character '{char_name}' in cell '{cell}' on sheet '{char_info['sheet']}'."
        )
        num_crits = sheet_handler.increment_cell(cell, char_info["sheet"])

        logging.info(
            f"Crit count for '{char_name}' updated successfully. New count: {num_crits}."
        )
        tim_response = talk_to_tim(
            f"{char_name.title()} rolled a Nat {crit_type}! They now have {num_crits}!",
            get_msg_author_name(ctx),
        )
        embed = build_crit_embed(
            crit_info["title"],
            crit_type,
            char_name,
            num_crits,
            char_info["color"],
            f"```{cow_format(tim_response)}```",
        )
        await ctx.send(file=discord.File(crit_info["img"]), embed=embed)
        logging.info(f"Response sent to user '{ctx.author}' for 'add' command.")

        play_sound(ctx, crit_info["sound"])

    @bot.command(name="sounds", help="Enables/disables sounds for the bot.")
    async def sounds(ctx, status: str = commands.parameter(description="On or off.")):
        logging.info(
            f"Received 'sounds' command from user '{ctx.author}' with status='{status}'."
        )

        if status not in ["on", "off"]:
            logging.warning(
                f"Invalid status '{status}' provided by user '{ctx.author}'."
            )
            await send_error_embed(
                ctx,
                f"Received {status}, which is not a valid status. Please try again.",
            )
            return

        embed = discord.Embed(
            title=f"Sounds {status}!",
            color=discord.Color.green() if status == "on" else discord.Color.red(),
        )
        await ctx.send(embed=embed)

        if status == "on":
            await join(ctx)
        elif status == "off":
            await leave(ctx)

    @bot.command(name="cowsay", help="Get a cow to say something for you.")
    async def cowsay(
        ctx,
        *,
        message: str = commands.parameter(
            description="What you want the cow to say.", default=None
        ),
    ):
        logging.info(f"Received 'cowsay' command from user '{ctx.author}'.")
        formatted_message = cow_format(message)
        await ctx.send(f"```{formatted_message}```")
        logging.info(f"Formatted cow message sent to user '{ctx.author}'.")

    @bot.command(name="cowchat", help="Have a chat with Tim!")
    async def cowchat(
        ctx,
        *,
        message: str = commands.parameter(
            description="What you say to the cow.", default=None
        ),
    ):
        logging.info(f"Received 'cowchat' command from user '{ctx.author}'. {message=}")

        if not message:
            logging.info(
                f"No message provided for 'cowchat' by user '{ctx.author}'. Sending default cow response."
            )
            await cowsay(ctx, message=None)
            return

        name = get_msg_author_name(ctx)
        logging.info(f"Sending message to Tim the cow from user '{name}'.")
        response = talk_to_tim(message, name)
        logging.info(f"Received response from Tim the cow.")
        await cowsay(ctx, message=response)

    def get_msg_author_name(ctx):
        return ctx.message.author.display_name.partition("(")[
            0
        ]  # names in this server are formatted as "name (nickname)"

    def cow_format(message: str | None) -> str:
        """
        Formats a message as a cow saying it using the cowsay subprocess.
        :param message: The message to format.
        :return: The formatted message.
        """
        if not message:
            logging.info("No message provided for cow_format.")
            message = "* The cow stares at you blankly *"

        logging.info(f"Running cowsay command with {message=}.")

        import platform

        if platform.system() == "Windows":
            args = [pwsh_path, "-Command", f"cowsay {message}"]
        else:
            args = ["cowsay", message]

        result = subprocess.run(
            args=args,
            capture_output=True,
            text=True,
            check=True,
        )
        logging.info("Cowsay command executed successfully.")
        return result.stdout

    def talk_to_tim(message: str, name: str) -> str:
        """
        Sends a message to Tim and returns his response.
        :param message: The message to send to Tim.
        :param name: The name of the person sending the message.
        :return: Tim's response text with newline stripped.
        """
        logging.info(f"Sending message to Tim.")
        message = f"From {name}: {message}"
        response = tim_chat.send_message(message).text.strip()
        logging.info(f"Received response from Tim.")
        return response

    async def join(ctx):
        if ctx.message.author.voice:
            channel = ctx.message.author.voice.channel
            await channel.connect()
            logging.info(
                f"Successfully joined voice channel '{channel}' for user '{ctx.author}'."
            )
        else:
            logging.warning(
                f"User '{ctx.author}' attempted to use 'join' command but is not in a voice channel."
            )
            await send_error_embed(ctx, "You are not in a voice channel.")

    async def leave(ctx):
        if ctx.voice_client:
            await ctx.guild.voice_client.disconnect()
            logging.info(
                f"Successfully left voice channel '{ctx.author.voice.channel}' for user '{ctx.author}'."
            )
        else:
            logging.warning(
                f"User '{ctx.author}' attempted to use 'leave' command but bot is not in a voice channel."
            )
            await send_error_embed(ctx, "I am not in a voice channel.")

    return bot
