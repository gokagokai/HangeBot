import toml
import logging
import os
import platform
import random
import sys

import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context
from dotenv import load_dotenv

if not os.path.isfile(f"{os.path.realpath(os.path.dirname(__file__))}/config.toml"):
    sys.exit("'config.toml' not found! Please add it and try again.")
else:
    with open(f"{os.path.realpath(os.path.dirname(__file__))}/config.toml") as file:
        config = toml.load(file)

intents = discord.Intents.default()
intents.bans = True
intents.dm_messages = True
intents.dm_reactions = True
intents.dm_typing = True
intents.emojis = True
intents.emojis_and_stickers = True
intents.guild_messages = True
intents.guild_reactions = True
intents.guild_scheduled_events = True
intents.guild_typing = True
intents.guilds = True
intents.integrations = True
intents.invites = True
intents.messages = True
intents.reactions = True
intents.typing = True
intents.voice_states = True
intents.webhooks = True

intents.members = True
intents.message_content = True
intents.presences = True

class LoggingFormatter(logging.Formatter):
    # Colors
    black = "\x1b[30m"
    red = "\x1b[31m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    blue = "\x1b[34m"
    gray = "\x1b[38m"
    # Styles
    reset = "\x1b[0m"
    bold = "\x1b[1m"

    COLORS = {
        logging.DEBUG: gray + bold,
        logging.INFO: blue + bold,
        logging.WARNING: yellow + bold,
        logging.ERROR: red,
        logging.CRITICAL: red + bold,
    }

    def format(self, record):
        log_color = self.COLORS[record.levelno]
        format = "(black){asctime}(reset) (levelcolor){levelname:<8}(reset) (green){name}(reset) {message}"
        format = format.replace("(black)", self.black + self.bold)
        format = format.replace("(reset)", self.reset)
        format = format.replace("(levelcolor)", log_color)
        format = format.replace("(green)", self.green + self.bold)
        formatter = logging.Formatter(format, "%Y-%m-%d %H:%M:%S", style="{")
        return formatter.format(record)


logger = logging.getLogger("discord_bot")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(LoggingFormatter())
# File handler
file_handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
file_handler_formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{"
)
file_handler.setFormatter(file_handler_formatter)

# Add the handlers
logger.addHandler(console_handler)
logger.addHandler(file_handler)


class DiscordBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned_or(config["prefix"]),
            intents=intents,
            help_command=None,
        )
        """
        This creates custom bot variables so that we can access these variables in cogs more easily.

        For example, The config is available using the following code:
        - self.config # In this class
        - bot.config # In this file
        - self.bot.config # In cogs
        """
        self.logger = logger
        self.config = config
        self.owner_id = config["owner_id"]

    async def load_cogs(self) -> None:
        """
        The code in this function is executed whenever the bot will start.
        """
        cog_order = ['general', 'message', 'owner', 'sd']

        for cog in cog_order:
            try:
                await self.load_extension(f"cogs.{cog}")
                self.logger.info(f"Loaded extension '{cog}'")
            except Exception as e:
                exception = f"{type(e).__name__}: {e}"
                self.logger.error(
                    f"Failed to load extension {cog}\n{exception}"
                )
        
    @tasks.loop(minutes=1.0)
    async def status_task(self) -> None:
        """
        Setup the game status task of the bot.
        """
        statuses = ["wonderful arts!"]
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=random.choice(statuses)))

    @status_task.before_loop
    async def before_status_task(self) -> None:
        """
        Before starting the status changing task, we make sure the bot is ready
        """
        await self.wait_until_ready()

    async def setup_hook(self) -> None:
        """
        This will just be executed when the bot starts the first time.
        """
        self.logger.info(f"Logged in as {self.user.name}")
        self.logger.info(f"discord.py API version: {discord.__version__}")
        self.logger.info(f"Python version: {platform.python_version()}")
        self.logger.info(
            f"Running on: {platform.system()} {platform.release()} ({os.name})"
        )
        self.logger.info("-------------------")
        await self.load_cogs()
        self.status_task.start()
    
    async def on_message(self, message: discord.Message) -> None:
        """
        The code in this event is executed every time someone sends a message, with or without the prefix

        :param message: The message that was sent.
        """
        if message.author == self.user or message.author.bot:
            return
        
        # DM Logs
        if not message.guild:
            owner = self.get_user(self.owner_id)
            if owner:
                embed = discord.Embed(
                    title=f"DM from {message.author}",
                    description=message.content,
                    color=discord.Color(0xadd8e6)
                )
                embed.set_thumbnail(url=message.author.avatar)
                
                await owner.send(embed=embed)

                for attachment in message.attachments:
                    await owner.send(file=await attachment.to_file())

        await self.process_commands(message)

    async def on_reaction_add(self, reaction, user):
        """
        This event is called every time someone reacts to a message.

        :param reaction: The reaction that was added.
        :param user: The user that added the reaction.
        """
        # DM Reaction Logs
        if reaction.message.guild is None:
            owner = self.get_user(self.owner_id)
            if owner:
                embed = discord.Embed(
                    title=f"Reaction {reaction.emoji} added by {user}",
                    description=f"{reaction.message.content}",
                    color=discord.Color(0xadd8e6)
                )
                embed.set_thumbnail(url=user.avatar)

                await owner.send(embed=embed)

    async def on_reaction_remove(self, reaction, user):
        """
        This event is called every time someone removes a reaction from a message.

        :param reaction: The reaction that was removed.
        :param user: The user that removed the reaction.
        """
        # DM Reaction Logs
        if reaction.message.guild is None:
            owner = self.get_user(self.owner_id)
            if owner:
                embed = discord.Embed(
                    title=f"Reaction {reaction.emoji} removed by {user}",
                    description=f"{reaction.message.content}",
                    color=discord.Color(0xadd8e6)
                )
                embed.set_thumbnail(url=user.avatar)

                await owner.send(embed=embed)

    async def on_command_completion(self, context: Context) -> None:
        """
        The code in this event is executed every time a normal command has been *successfully* executed.

        :param context: The context of the command that has been executed.
        """
        full_command_name = context.command.qualified_name
        split = full_command_name.split(" ")
        executed_command = str(split[0])
        if context.guild is not None:
            self.logger.info(
                f"Executed {executed_command} command in {context.guild.name} (ID: {context.guild.id}) by {context.author} (ID: {context.author.id})"
            )
        else:
            self.logger.info(
                f"Executed {executed_command} command by {context.author} (ID: {context.author.id}) in DMs"
            )

    async def on_command_error(self, context: Context, error) -> None:
        """
        The code in this event is executed every time a normal valid command catches an error.

        :param context: The context of the normal command that failed executing.
        :param error: The error that has been faced.
        """
        if isinstance(error, commands.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            hours, minutes = divmod(minutes, 60)
            hours = hours % 24
            embed = discord.Embed(
                description=f"**Please slow down** - You can use this command again in {f'{round(hours)} hours' if round(hours) > 0 else ''} {f'{round(minutes)} minutes' if round(minutes) > 0 else ''} {f'{round(seconds)} seconds' if round(seconds) > 0 else ''}.",
                color=0xE02B2B,
            )
            await context.send(embed=embed, ephemeral=True)
        elif isinstance(error, commands.NotOwner):
            embed = discord.Embed(
                description="You are not the owner of the bot!", color=0xE02B2B
            )
            await context.send(embed=embed)
            if context.guild:
                self.logger.warning(
                    f"{context.author} (ID: {context.author.id}) tried to execute an owner only command in the guild {context.guild.name} (ID: {context.guild.id}), but the user is not an owner of the bot."
                )
            else:
                self.logger.warning(
                    f"{context.author} (ID: {context.author.id}) tried to execute an owner only command in the bot's DMs, but the user is not an owner of the bot."
                )
        elif isinstance(error, commands.MissingPermissions):
            await context.send('https://tenor.com/view/lotr-lord-of-the-rings-theoden-king-of-rohan-you-have-no-power-here-gif-4952489', ephemeral=True)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                description="I am missing the permission(s) `"
                + ", ".join(error.missing_permissions)
                + "` to fully perform this command!",
                color=0xE02B2B,
            )
            await context.send(embed=embed, ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="Error!",
                # We need to capitalize because the command arguments have no capital letter in the code and they are the first word in the error message.
                description=str(error).capitalize(),
                color=0xE02B2B,
            )
            await context.send(embed=embed, ephemeral=True)
        elif isinstance(error, commands.MissingAnyRole):
            await context.send('https://tenor.com/view/lotr-lord-of-the-rings-theoden-king-of-rohan-you-have-no-power-here-gif-4952489', ephemeral=True)
        else:
            raise error


load_dotenv()

bot = DiscordBot()
bot.run(os.getenv("TOKEN"))
