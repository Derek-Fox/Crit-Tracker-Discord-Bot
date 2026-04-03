"""
Handles commands related to tracking critical hits on the spreadsheet,
such as adding crits and incrementing session numbers.
"""

import random
import logging
import discord
from discord import app_commands
from discord.ext import commands
from num2words import num2words

from utils.helpers import (
    send_error_embed,
    play_sound,
    get_msg_author_name,
    talk_to_tim,
    cow_format,
)

happy_emoji = list("😀😁😃😄😆😉😊😋😎😍🙂🤗🤩😏")
sad_emoji = list("😞😒😟😠🙁😣😖😨😰😧😢😥😭😵‍💫")


def build_crit_embed(
    title, crit_type, char_name, num_crits, color, cow_msg
) -> discord.Embed:
    """
    Helper function to build an embed for a crit response.

    :param title: Title of the embed, can include {crit_type} and {emoji} placeholders.
    :param crit_type: Type of crit, e.g. "1" or "20".
    :param char_name: Name of the character who got the crit.
    :param num_crits: Total number of crits the character has after this one.
    :param color: Color of the embed, as a hex integer.
    :param cow_msg: Message from Tim the cow to include in the embed description.
    :return: A discord.Embed object representing the crit response.
    """
    embed = discord.Embed(
        title=title.format(
            crit_type=crit_type,
            emoji=random.choice(happy_emoji if crit_type == "20" else sad_emoji),
        ),
        color=color,
    )
    embed.set_thumbnail(url=f"attachment://nat{crit_type}.png")
    embed.description = f"{char_name.title()} now has {num2words(num_crits)} Nat {crit_type}s!\n{cow_msg}"
    return embed


class CritCog(commands.Cog):
    def __init__(self, bot, sheet_handler, tim_chat, pwsh_path, config) -> None:
        self.bot = bot
        self.sheet_handler = sheet_handler
        self.tim_chat = tim_chat
        self.pwsh_path = pwsh_path
        self.campaigns: list[str] = config["campaigns"]
        self.characters: dict[str, dict] = config["characters"]
        self.crit_types: dict[str, dict] = config["crit_types"]

    dnd_commands = app_commands.Group(name="dnd", description="Commands to manage Dnd stuff (crits, sessions).")

    @dnd_commands.command(name="session", description="Increments the session number by one.")
    @app_commands.choices(campaign=[
        app_commands.Choice(name="Kriggsan", value="KRIGGSAN"),
        app_commands.Choice(name="Paxorian", value="PAXORIAN"),
    ])
    async def session(
        self,
        inter: discord.Interaction,
        campaign: str #= commands.parameter(description="Campaign name, e.g. Paxorian."),
    ):
        """
        Increments the session number for a given campaign by one.
        """

        logging.info(
            "Received 'session' command from user '%s' with campaign='%s'.",
            inter.user.display_name,
            campaign,
        )

        if campaign.upper() not in self.campaigns:
            await send_error_embed(
                inter,
                f"Received invalid campaign {campaign}. Please try again.",
            )
            return

        new_session_number = self.sheet_handler.increment_cell("H2", campaign.title())
        msg = f"Campaign {campaign.title()} incremented to {new_session_number}."
        await inter.response.send_message(embed=discord.Embed(title=msg, color=0xA2C4C9))
        logging.info(msg)

    @commands.command(name="add", help="Adds a crit to the spreadsheet.")
    async def add(
        self,
        ctx,
        crit_type: str = commands.parameter(description="Type of crit, 1 or 20."),
        char_name: str = commands.parameter(description="Name of character, e.g. Morbo."),
    ):
        '''
        Adds a crit to the spreadsheet for a given character and crit type, 
        then responds with an embed showing the updated crit count and a message from Tim the cow.
        
        :param self: The instance of the CritCog class.
        :param ctx: The context of the command invocation.
        :param crit_type: The type of crit to add, either "1" or "20".
        :param char_name: The name of the character to add the crit to.
        '''
        logging.info(
            "Received 'add' command from user '%s' with crit_type='%s' and char_name='%s'.",
            ctx.author,
            crit_type,
            char_name,
        )

        char_info = self.characters.get(char_name.upper())
        if not char_info:
            logging.warning(
                "Invalid character name '%s' provided by user '%s'.",
                char_name,
                ctx.author,
            )
            await send_error_embed(
                ctx,
                f"Received invalid character '{char_name}'. Please try again.",
            )
            return

        crit_info = self.crit_types.get(crit_type)
        if not crit_info:
            logging.warning(
                "Invalid crit type '%s' provided by user '%s'.",
                crit_type,
                ctx.author,
            )
            await send_error_embed(
                ctx,
                f"Received invalid crit type '{crit_type}'. Please try again.",
            )
            return

        cell = crit_info["col"] + char_info["row"]
        logging.info(
            "Updating crit count for character '%s' in cell '%s' on sheet '%s'.",
            char_name,
            cell,
            char_info["sheet"],
        )
        num_crits = self.sheet_handler.increment_cell(cell, char_info["sheet"])

        logging.info(
            "Crit count for '%s' updated successfully. New count: %s.",
            char_name,
            num_crits,
        )

        tim_response = talk_to_tim(
            f"{char_name.title()} rolled a Nat {crit_type}! They now have {num_crits}!",
            get_msg_author_name(ctx),
            self.tim_chat,
        )

        embed = build_crit_embed(
            "Nat {crit_type} added! {emoji}",
            crit_type,
            char_name,
            num_crits,
            char_info["color"],
            f"```{cow_format(tim_response, self.pwsh_path)}```",
        )
        await ctx.send(file=discord.File(crit_info["img"]), embed=embed)
        logging.info("Response sent to user '%s' for 'add' command.", ctx.author)

        play_sound(ctx, crit_info["sound"])
