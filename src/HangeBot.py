import asyncio
from abc import ABC
from typing import Optional
import string

import toml
import discord
from discord import option

from src import AutoWebUi
from src.LoadDistributionManager import Status


class Config:
    def __init__(self, config_path):
        self.config = toml.load(config_path)


class Bot:
    def __init__(self, token, config, load_distributor, **options):
        super().__init__(**options)
        self.load_distributor = load_distributor
        instance = Hange()

        # @instance.event
        # async def on_connect():
        #     if instance.auto_sync_commands:
        #         await instance.sync_commands(commands=[],guild_ids=[1174155318029209680])
        #     print(f"{instance.user.name} connected.")

        # @instance.event
        # async def on_ready():
        #     print(f'{instance.user} online')

        params = config.config['command_params']
        aspect_ratios = config.config['aspect_ratios']

        def stringify(queue_obj):
            maps = {
                'prompt': ('prompt', None),
                'negative_prompt': ('negative_prompt', params['default_negative']),
                'steps': ('steps', params['default_steps']),
                'aspect_ratio': ('aspect_ratio', params['default_ratio']),
                'seed': ('seed', -1),
                'cfg_scale': ('guidance_scale', params['default_cfg']),
                'sampler_index': ('sampler', params['default_sampler'])
            }
            cmd_parts = ['/generate']
            for item in queue_obj.args.items():
                if item[0] in maps:
                    # don't append if value is default
                    if item[1] != maps[item[0]][1]:
                        cmd_parts.append(f'{maps[item[0]][0]}: {item[1]}')
            return ' '.join(cmd_parts)
        
        @instance.slash_command(name="model", description="switch model")
        @option('model', str, description='model to switch to', required=True, choices=params['models'])
        async def model(ctx, *, model: str):
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
                await ctx.respond("shits fucked")
            else:
                await ctx.respond("finished switching to "+model)

        @instance.slash_command(name="generate", description="Generate an image", guild_ids=[1174155318029209680])
        @option('prompt', str, description='The prompt for generating the image', required=True)
        @option('negative_prompt', str, description='', required=False)
        @option('aspect_ratio', str, description='Image Aspect Ratio', required=False,
                choices=list(aspect_ratios.keys()))
        @option('steps', int, description='Sampling Steps', required=False,
                min_value=params['min_steps'], max_value=params['max_steps'])
        @option('seed', int, description='Image seed', required=False)
        @option('guidance_scale', float, description='CFG scale', required=False)
        @option('sampler', str, description='Sampling method', required=False, choices=params['samplers'])
        async def generate(ctx, *, prompt: str,
                           negative_prompt: Optional[str] = params['default_negative'],
                           aspect_ratio: Optional[str] = params['default_ratio'],
                           steps: Optional[int] = params['default_steps'],
                           seed: Optional[int] = -1,
                           guidance_scale: Optional[float] = params['default_cfg'],
                           sampler: Optional[str] = params['default_sampler']):
            
            # Check for banned words
            search = prompt if config.config['blacklist']['allow_in_negative'] else ' '.join([prompt, negative_prompt])
            for word in config.config['blacklist']['words']:
                # remove punctuation from the prompt before searching
                for word2 in search.translate(str.maketrans('', '', string.punctuation)).split():
                    if word.lower() == word2.lower():
                        print(f'Denied -- {ctx.author.name} tried to use banned word: {word}')
                        await ctx.respond(f'You tried to use a banned word.\n `Word: {word}`', ephemeral=True)
                        return

            # Prevent randomness from going wild when short prompt
            if len(prompt) <= 20:
                if negative_prompt:
                    negative_prompt += ', ' + ', '.join(config.config['blacklist']['words'])
                else:
                    negative_prompt = ', '.join(config.config['blacklist']['words'])

            # Check for banned nsfw words
            if str(ctx.channel.id) not in config.config['blacklist']['nsfw_channels']:
                for word in config.config['blacklist']['nsfw_words']:
                    # remove punctuation from the prompt before searching
                    for word2 in search.translate(str.maketrans('', '', string.punctuation)).split():
                        if word.lower() == word2.lower():
                            print(f'Denied -- {ctx.author.name} tried to use banned nsfw word: {word}')
                            await ctx.respond(f'Chill bro keep it Sfw.\n `Word: {word}`', ephemeral=True)
                            return
                
                # Prevent randomness from going wild when short prompt
                if len(prompt) <= 20:
                    if negative_prompt:
                        negative_prompt += ', ' + ', '.join(config.config['blacklist']['nsfw_words'])
                    else:
                        negative_prompt = ', '.join(config.config['blacklist']['nsfw_words'])

            # Process request
            print(f'Request -- {ctx.author.name} -- Prompt: {prompt}')
            width, height = aspect_ratios[aspect_ratio]
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

            if response == Status.QUEUED:
                await ctx.respond(
                    f'`Queue Position: {info}`')
            elif response == Status.IN_QUEUE:
                embed = discord.Embed(
                                      description=f'**Chill bro I only have 1 GPU**.\n'
                                                  f'`Your Position: {info + 1}`',
                                      color=0xFFD700)
                await ctx.respond(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(title='Encountered an error: ',
                                      description=str(response),
                                      color=0xff0000)
                await ctx.respond(embed=embed)

        instance.run(token)


class Hange(discord.Bot, ABC):
    def __init__(self, *args, **options):
        super().__init__(*args, **options)

    async def on_message(self, message):
        if message.channel.type.name != 'private':
            if message.author == self.user:
                try:
                    # Check if the message from Hange was actually a generation
                    if message.embeds[0].description == '**Enjoy!**':
                        await message.add_reaction('❌')
                except:
                    pass

    async def on_raw_reaction_add(self, ctx):
        if ctx.emoji.name == '❌':
            message = self.get_channel(ctx.channel_id)
            if not message:
                return
            message = await message.fetch_message(ctx.message_id)
            if message.embeds:
                # look at the message footer to see if the generation was by the user who reacted
                if f'{ctx.member.name}' in message.embeds[0].footer.text:
                    await message.delete()
