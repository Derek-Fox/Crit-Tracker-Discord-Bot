"""
Handles core bot events and functionality, such as setting the bot's status on startup.
"""
import logging
import discord
from discord.ext import commands


class CoreCog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """Sets up the bot's status"""
        logging.info("Bot logged in as %s.", self.bot.user)
        game = discord.Game("$help")
        await self.bot.change_presence(status=discord.Status.dnd, activity=game)

    @commands.command()
    @commands.is_owner()
    @commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
    @commands.dm_only()
    async def sync(self, ctx: commands.Context) -> None:
        """Sync slash commands to discord"""
        synced = await ctx.bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} commands globally")

    @sync.error
    async def sync_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Handle errors in sync command"""
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Sync is on cooldown for {error.retry_after:.1f} seconds", ephemeral=True)
        elif isinstance(error, commands.NotOwner):
            await ctx.send("You are not the owner of this bot.", ephemeral=True)
        elif isinstance(error, commands.PrivateMessageOnly):
            await ctx.send("You can only use this command in private messages.", ephemeral=True)
        else:
            await ctx.send(f"Unknown error: {error}", ephemeral=True)
