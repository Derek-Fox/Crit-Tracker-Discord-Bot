"""
Contains helper functions for the bot, such as formatting messages and sending error embeds.
"""

import logging
import subprocess
import platform
import discord
from discord import Interaction
from discord import FFmpegPCMAudio


def cow_format(message: str | None, pwsh_path: str) -> str:
    """
    Formats a message as a cow saying it using the cowsay subprocess.
    :param message: The message to format.
    :param pwsh_path: The path to the pwsh executable.
    :return: The formatted message.
    """
    if not message:
        logging.info("No message provided for cow_format.")
        message = "* The cow stares at you blankly *"

    logging.info("Running cowsay command with message=%s.", message)

    if platform.system() == "Windows":
        logging.info(
            "Windows platform detected, using Powershell at path %s.", pwsh_path
        )
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


def talk_to_tim(message: str, name: str, tim_chat) -> str:
    """
    Sends a message to Tim and returns his response.
    :param message: The message to send to Tim.
    :param name: The name of the person sending the message.
    :tim_chat: The Tim chat object.
    :return: Tim's response text with newline stripped.
    """
    logging.info("Sending message to Tim: '%s' from user '%s'.", message, name)
    try:
        message = f'From {name}: {message}'
        response = tim_chat.send_message(message).text.strip()
        logging.info("Received response from Tim: %s", response)
        return response
    except (AttributeError, ValueError) as e:
        logging.error("Error communicating with Tim: %s", e)
        return "Tim is having trouble responding right now."


async def send_error_embed(inter: discord.Interaction, message):
    """
    Sends an error embed to the given context with the given message.

    :param inter: The interaction in which the error occurred.
    :param message: The error message to display.
    """
    embed = discord.Embed(
        title="**Error**", description=message, color=discord.Color.red()
    )
    embed.set_thumbnail(url="attachment://warning.png")
    try:
        await inter.response.send_message(file=discord.File("res/warning.png"), embed=embed)
    except discord.InteractionResponded:
        await inter.followup.send(file=discord.File("res/warning.png"), embed=embed)


def play_sound(inter: discord.Interaction, sound):
    """
    Plays a sound in the given context's voice channel.

    :param inter: The interaction which asked to play the sound.
    :param sound: The path to the sound file to play.
    """
    if inter.user.voice:
        source = FFmpegPCMAudio(sound)
        inter.guild.voice_client.play(source)
        logging.info("Sound '%s' played in channel '%s'.", sound, voice.channel)


def get_msg_author_name(inter):
    """
    Returns the display name of the author of a message in a given context.

    :param inter: The interaction from which to extract the author's name.
    """
    return inter.user.display_name.partition("(")[
        0
    ].strip()  # names in this server are formatted as "name (nickname)"
