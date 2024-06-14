import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

class General(commands.Cog, name="general"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="help", description="List all available commands."
    )
    @app_commands.describe(ephemeral="Whether or not the help message should be ephemeral.")
    async def help(self, context: Context, ephemeral: bool = False) -> None:
        embed = discord.Embed(
            title="Help", description="Use either '/' or 's!':", color=0xFFFFE0
        )
        for i in self.bot.cogs:
            if i == "owner":
                continue

            # Check if the user has one of the specified roles
            user_role_ids = [role.id for role in context.author.roles]
            if i == "message" and not any(role_id in self.bot.config["mod_role_ids"] for role_id in user_role_ids):
                continue

            cog = self.bot.get_cog(i.lower())
            commands = cog.get_commands()
            data = []
            for command in commands:
                description = command.description.partition("\n")[0]
                data.append(f"/{command.name} · {description}")
            help_text = "\n".join(data)
            embed.add_field(
                name=i.capitalize(), value=f"```{help_text}```", inline=False
            )
        await context.send(embed=embed, ephemeral=ephemeral)

    @commands.hybrid_command(
        name="ping",
        description="Check if the bot is alive.",
    )
    async def ping(self, context: Context) -> None:
        """
        Check if the bot is alive.

        :param context: The hybrid command context.
        """
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"{round(self.bot.latency * 1000)}ms.",
            color=0xBEBEFE,
        )
        await context.send(embed=embed, ephemeral=True)

async def setup(bot) -> None:
    await bot.add_cog(General(bot))
