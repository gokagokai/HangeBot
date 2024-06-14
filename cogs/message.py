import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

class Message(commands.Cog, name="message"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="say",
        description="Sends a message as the bot.",
    )
    @app_commands.describe(message="The message that should be repeated by the bot",
                          channel="The channel where the message should be sent")
    async def say(self, context: Context, channel: discord.TextChannel = None, *, message: str) -> None:
        """
        The bot will say anything you want.

        :param context: The hybrid command context.
        :param channel: The channel where the message should be sent (defaults to the channel where the command was invoked).
        :param message: The message that should be repeated by the bot.
        """

        channel = channel or context.channel
        embed = discord.Embed(description="Sent to " + channel.mention, color=0xBEBEFE)
        await context.send(embed=embed, ephemeral=True)
        await channel.send(message)
            
    @commands.hybrid_command(
        name="embed",
        description="Embeds a message as the bot.",
    )
    @app_commands.describe(message="The message that should be repeated by the bot")
    async def embed(self, context: Context, *, channel: discord.TextChannel = None, message: str) -> None:
        """
        The bot will say anything you want, but using embeds.

        :param context: The hybrid command context.
        :param channel: The channel where the message should be sent (defaults to the channel where the command was invoked).
        :param message: The message that should be repeated by the bot.
        """
        channel = channel or context.channel
        context_embed = discord.Embed(description="Sent to " + channel.mention, color=0xBEBEFE)
        message_embed = discord.Embed(description=message, color=0xFFFFE0)
        await context.send(embed=context_embed, ephemeral=True)
        await channel.send(embed=message_embed)
        
async def setup(bot) -> None:
    await bot.add_cog(Message(bot))