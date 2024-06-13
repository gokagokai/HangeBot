import asyncio
import string
import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from modules import LoadDistributionManager
from api import AutoWebUi

class Sd(commands.Cog, name="sd"):
    def __init__(self, bot) -> None:
        self.bot = bot
        ips = self.bot.config['webui_ips'].items()
        ips = [ip[1] for ip in ips]
        self.load_distributor = LoadDistributionManager.LoadDist(ips, self.bot.config)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.type.name != 'private':
            if message.author == self.bot.user:
                try:
                    # Check if the message from Hange was actually a generation
                    if message.embeds[0].description == '**Enjoy!**':
                        await message.add_reaction('❌')
                except:
                    pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, ctx):
        if ctx.emoji.name == '❌':
            channel = self.bot.get_channel(ctx.channel_id)
            if not channel:
                return
            message = await channel.fetch_message(ctx.message_id)
            if message.embeds:
                # look at the message footer to see if the generation was by the user who reacted
                if f'{ctx.member.name}' in message.embeds[0].footer.text:
                    await message.delete()

    @commands.hybrid_command(
        name="model", 
        description="Switch model"
    )
    @app_commands.describe(model="Model to switch to")
    async def model(self, ctx: Context, model: str):
        webui = AutoWebUi.WebUi("http://127.0.0.1:7860/")
        print(f'Request -- {ctx.author.name} -- change model to {model}')
        queue_obj = AutoWebUi.QueueObj(
            event_loop=asyncio.get_event_loop(),
            ctx=ctx,
            args={
                'sd_model_checkpoint': model
            }
        )
        response, status_code = webui.switch_model(queue_obj)
        if status_code != 200:
            await ctx.send("shits fucked", ephemeral=True)
        else:
            await ctx.send(f"finished switching to {model}", ephemeral=True)

    @commands.hybrid_command(
        name="generate", 
        description="Generate an image"
    )
    @app_commands.describe(
        prompt="The prompt for generating the image",
        negative_prompt="Negative prompt",
        aspect_ratio="Image Aspect Ratio",
        steps="Sampling Steps",
        seed="Image seed",
        guidance_scale="CFG scale",
        sampler="Sampling method"
    )
    async def generate(
        self, ctx: Context, 
        prompt: str,
        negative_prompt: str = None,
        aspect_ratio: str = None,
        steps: int = None,
        seed: int = None,
        guidance_scale: float = None,
        sampler: str = None
    ):
        negative_prompt = negative_prompt or self.bot.config['command_params']['default_negative']
        aspect_ratio = aspect_ratio or self.bot.config['command_params']['default_ratio']
        steps = steps or self.bot.config['command_params']['default_steps']
        seed = seed or -1
        guidance_scale = guidance_scale or self.bot.config['command_params']['default_cfg']
        sampler = sampler or self.bot.config['command_params']['default_sampler']

        # Check for banned words
        search = prompt if self.bot.config['blacklist']['allow_in_negative'] else ' '.join([prompt, negative_prompt])
        for word in self.bot.config['blacklist']['words']:
            for word2 in search.translate(str.maketrans('', '', string.punctuation)).split():
                if word.lower() == word2.lower():
                    print(f'Denied -- {ctx.author.name} tried to use banned word: {word}')
                    await ctx.send(f'You tried to use a banned word.\n `Word: {word}`', ephemeral=True)
                    return

        # Prevent randomness from going wild when short prompt
        if len(prompt) <= 20:
            if negative_prompt:
                negative_prompt += ', ' + ', '.join(self.bot.config['blacklist']['words'])
            else:
                negative_prompt = ', '.join(self.bot.config['blacklist']['words'])

        # Check for banned nsfw words
        if str(ctx.channel.id) not in self.bot.config['blacklist']['nsfw_channels']:
            for word in self.bot.config['blacklist']['nsfw_words']:
                for word2 in search.translate(str.maketrans('', '', string.punctuation)).split():
                    if word.lower() == word2.lower():
                        print(f'Denied -- {ctx.author.name} tried to use banned nsfw word: {word}')
                        await ctx.send(f'Chill bro keep it Sfw.\n `Word: {word}`', ephemeral=True)
                        return
            
            if len(prompt) <= 20:
                if negative_prompt:
                    negative_prompt += ', ' + ', '.join(self.bot.config['blacklist']['nsfw_words'])
                else:
                    negative_prompt = ', '.join(self.bot.config['blacklist']['nsfw_words'])

        # Process request
        print(f'Request -- {ctx.author.name} -- Prompt: {prompt}')
        width, height = self.bot.config['aspect_ratios'][aspect_ratio]
        queue_obj = AutoWebUi.QueueObj(
            event_loop=asyncio.get_event_loop(),
            ctx=ctx,
            args={
                'prompt': prompt,
                'negative_prompt': negative_prompt,
                'steps': steps,
                'width': width,
                'height': height,
                'seed': seed,
                'cfg_scale': guidance_scale,
                'sampler_index': sampler
            }
        )

        response, info = self.load_distributor.add_to_queue(queue_obj)

        if response == LoadDistributionManager.Status.QUEUED:
            await ctx.send(f'`Queue Position: {info}`')
        elif response == LoadDistributionManager.Status.IN_QUEUE:
            embed = discord.Embed(
                                  description=f'**Chill bro I only have 1 GPU**.\n'
                                              f'`Your Position: {info + 1}`',
                                  color=0xFFD700)
            await ctx.send(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(title='Encountered an error: ',
                                  description=str(response),
                                  color=0xff0000)
            await ctx.send(embed=embed)

async def setup(bot) -> None:
    await bot.add_cog(Sd(bot))
