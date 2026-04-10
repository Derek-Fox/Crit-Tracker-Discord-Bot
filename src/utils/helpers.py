"""
Contains helper functions for the bot, such as formatting messages and sending error embeds.
"""

import logging
import os
import subprocess
import platform
import discord
from discord import Interaction
from discord import FFmpegPCMAudio


def cow_format(message: str, pwsh_path: str, eyes: str | None = None) -> str:
    """
    Formats a message as a cow saying it using the cowsay subprocess.
    :param message: The message to format.
    :param pwsh_path: The path to the pwsh executable.
    :param eyes: Optional eye string to use. Must be length 2 exactly.
    :return: The formatted message.
    """
    if eyes and len(eyes) != 2:
        raise Exception("Invalid eye string. Needs to be length 2 exactly.")

    if platform.system() == "Windows":
        logging.info(
            "Windows platform detected, using Powershell at path %s.", pwsh_path
        )
        command = f"cowsay -f ./wizard.cow {message}" if not eyes else rf"cowsay -f ./wizard.cow -e{eyes} {message}"
        args = [pwsh_path, "-Command", command]
    else:
        args = ["cowsay", r"-f./wizard.cow", message]
        if eyes: args.insert(2, rf"-e{eyes}")

    logging.info(f"Running command {" ".join(args)}")
    result = subprocess.run(
        args=args,
        capture_output=True,
        text=True,
        check=True,
    )
    logging.info("Cowsay command executed successfully.")  # TODO: actually handle errors from command
    return result.stdout


def talk_to_tim(message: str, name: str, tim_chat) -> str:
    """
    Sends a message to Tim and returns his response.
    :param message: The message to send to Tim.
    :param name: The name of the person sending the message.
    :param tim_chat: The Tim chat object.
    :return: Tim's response text with newline stripped.

    Note: If the environment variable "NO_TIM" is set (to any value) then the A.I.
    model will not be run and a stock response will be returned.
    """
    if os.getenv("NO_TIM"): return "Tim is disabled right now. Unset NO_TIM to get him back."

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
    if inter.guild and inter.guild.voice_client:
        source = FFmpegPCMAudio(sound)
        inter.guild.voice_client.play(source)
        logging.info("Sound '%s' played in channel '%s'.", sound, inter.guild.voice_client.channel)


def get_msg_author_name(inter):
    """
    Returns the display name of the author of a message in a given context.

    :param inter: The interaction from which to extract the author's name.
    """
    return inter.user.display_name.partition("(")[
        0
    ].strip()  # names in this server are formatted as "name (nickname)"
