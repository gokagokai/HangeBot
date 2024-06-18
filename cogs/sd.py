import asyncio
import base64
import re
import string
import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
import aiohttp

import toml
from modules import LoadDistributionManager
from api import AutoWebUi

with open(f"config.toml") as file:
    config = toml.load(file)

class Sd(commands.Cog, name="sd"):
    def __init__(self, bot) -> None:
        self.bot = bot
        ips = config['webui_ips'].items()
        self.ips = [ip[1] for ip in ips]
        self.load_distributor = LoadDistributionManager.LoadDist(self.ips, config)
        self.session = aiohttp.ClientSession()

    async def cleanup(self):
        await self.session.close()

    def cog_unload(self):
        asyncio.create_task(self.cleanup())

    async def cog_reload(self):
        await self.cleanup()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.type.name != 'private':
            # Delete image with reaction
            if message.author == self.bot.user:
                try:
                    # Check if the message from Hange was actually a generation
                    if message.embeds[0].description == '**Enjoy!**':
                        await message.add_reaction('❌')
                except:
                    pass
            
            # Reply with @Hange to get metadata
            if message.reference and str(self.bot.user.id) in message.content:
                original_message = await message.channel.fetch_message(message.reference.message_id)
                if original_message.attachments:
                    for attachment in original_message.attachments:
                        if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                            base64_string = await self._download_and_encode_image(attachment.url)
                            webui = AutoWebUi.WebUi(self.ips[0])
                            response, _ = webui.get_png_info(base64_string)
                            await self._send_embed_response(message, response, attachment)

            # Copy Message Link to get metadada
            if "https://discord.com/channels/" in message.content and not message.author.bot:
                link_parts = message.content.split("/")
                if len(link_parts) == 7:
                    try:
                        channel_id = int(link_parts[5])
                        message_id = int(link_parts[6])
                        print(channel_id, message_id)
                        channel = self.bot.get_channel(channel_id)
                        if channel:
                            original_message = await channel.fetch_message(message_id)
                            if original_message.attachments:
                                for attachment in original_message.attachments:
                                    print(attachment)
                                    if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                                        base64_string = await self._download_and_encode_image(attachment.url)
                                        webui = AutoWebUi.WebUi(self.ips[0])
                                        response, _ = webui.get_png_info(base64_string)
                                        await message.channel.send(message.content)
                                        await self._send_embed_response(message, response, attachment)
                                        await message.delete()
                    except Exception as e:
                        print(f"Error processing message link: {e}")

    async def _send_embed_response(self, message, response, attachment):
        embed = discord.Embed(color=0xFFFFE0)
        params = response.get('parameters', {})
        
        if 'Prompt' in params:
            embed.add_field(name='Prompt', value=params['Prompt'])
        if 'Negative prompt' in params:
            embed.add_field(name='Negative Prompt', value=params['Negative prompt'])
        if 'Size-1' in params:
            embed.add_field(name='Size', value=f"{params['Size-1']}x{params['Size-2']}")
        if 'Sampler' in params:
            embed.add_field(name='Sampler', value=params['Sampler'])
        if 'Schedule type' in params:
            embed.add_field(name='Schedule type', value=params['Schedule type'])
        if 'Steps' in params:
            embed.add_field(name='Steps', value=params['Steps'])
        if 'CFG scale' in params:
            embed.add_field(name='CFG Scale', value=params['CFG scale'])
        if 'Clip skip' in params:
            embed.add_field(name='Clip skip', value=params['Clip skip'])
        if 'Seed' in params:
            embed.add_field(name='Seed', value=params['Seed'])
        if 'Model' in params:
            embed.add_field(name='Model', value=params['Model'])

        # Add user footer
        if message.author.avatar is None:
            embed.set_footer(text=f'{message.author.name}')
        else:
            embed.set_footer(
                text=f'{message.author.name}',
                icon_url=message.author.avatar.url
            )

        await message.channel.send(attachment.url)
        await message.channel.send(embed=embed)
        
    async def _download_and_encode_image(self, url):
        async with self.session.get(url) as response:
            if response.status == 200:
                image_bytes = await response.read()
                base64_string = base64.b64encode(image_bytes).decode('utf-8')
                return base64_string
            return None
        
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
        webui = AutoWebUi.WebUi(self.ips[0])
        print(f'Change model to {model}')
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
    @app_commands.choices(
        aspect_ratio=[
            app_commands.Choice(name=key, value=key) 
            for key in config['aspect_ratios'].keys()
        ],
        sampler=[
            app_commands.Choice(name=sampler, value=sampler) 
            for sampler in config['command_params']['samplers']
        ]
    )
    async def generate(
        self, ctx: Context, 
        prompt: str,
        negative_prompt: str = None,
        aspect_ratio: str = None,
        steps: app_commands.Range[int, config['command_params']['min_steps'], config['command_params']['max_steps']] = None,
        seed: int = None,
        guidance_scale: float = None,
        sampler: str = None,
        batch_size: app_commands.Range[int, 1,4] = 1,
    ):
        aspect_ratio = aspect_ratio or config['command_params']['default_ratio']
        width, height = config['aspect_ratios'][aspect_ratio]
        await self.generate_base(ctx, prompt, negative_prompt, width, height, steps, seed, guidance_scale, sampler, batch_size)

    async def generate_base(
        self, ctx: Context, 
        prompt: str,
        negative_prompt: str = None,
        width: int = None,
        height: int = None,
        steps: int = None,
        seed: int = None,
        guidance_scale: float = None,
        sampler: str = None,
        batch_size: int = None
    ):
        # Remove /generate prompt: from the prompt (Fix common mistake)
        transformed_prompt = re.sub(r'^/generate prompt:\s*', '', prompt)

        # Transform prompt to replace <:emoji:ID> with :emoji: (Fix for mobile)
        transformed_prompt = re.sub(r'<:(\w+):\d+>', r':\1:', transformed_prompt)

        error_prompt= False
        if transformed_prompt != prompt:
            print(f'--- <Error Prompt>: --- \n{prompt}')
            prompt = transformed_prompt
            error_prompt= True

        negative_prompt = negative_prompt or config['command_params']['default_negative']
        steps = steps or config['command_params']['default_steps']
        seed = seed or -1
        guidance_scale = guidance_scale or config['command_params']['default_cfg']
        sampler = sampler or config['command_params']['default_sampler']

        # Check if sampler is valid, otherwise use default sampler
        valid_samplers = config['command_params']['samplers']
        default_sampler_used = False
        if sampler not in valid_samplers and sampler != None:
            sampler = config['command_params']['default_sampler']
            default_sampler_used = True

        # Check for banned words
        search = prompt if config['blacklist']['allow_in_negative'] else ' '.join([prompt, negative_prompt])
        for word in config['blacklist']['words']:
            for word2 in search.translate(str.maketrans('', '', string.punctuation)).split():
                if word.lower() == word2.lower():
                    print(f'Denied -- {ctx.author.name} tried to use banned word: {word}')
                    await ctx.send(f'**You tried to use a banned word.**\n `Word: {word}`', ephemeral=True)
                    return

        # Prevent randomness from going wild when short prompt
        if len(prompt) <= 20:
            if negative_prompt:
                negative_prompt += ', ' + ', '.join(config['blacklist']['words'])
            else:
                negative_prompt = ', '.join(config['blacklist']['words'])

        # Check for banned nsfw words
        if str(ctx.channel.id) not in config['blacklist']['nsfw_channels']:
            for word in config['blacklist']['nsfw_words']:
                for word2 in search.translate(str.maketrans('', '', string.punctuation)).split():
                    if word.lower() == word2.lower():
                        print(f'Denied -- {ctx.author.name} tried to use banned nsfw word: {word}')
                        await ctx.send(f'**Chill bro keep it Sfw.**\n `Word: {word}`', ephemeral=True)
                        return
            
            if len(prompt) <= 20:
                if negative_prompt:
                    negative_prompt += ', ' + ', '.join(config['blacklist']['nsfw_words'])
                else:
                    negative_prompt = ', '.join(config['blacklist']['nsfw_words'])

        # Process request
        print(f'--- <Prompt>: ---\n{prompt}')
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
                'sampler_index': sampler,
                'batch_size' : batch_size,
            }
        )

        response, info = self.load_distributor.add_to_queue(queue_obj)
        response_message = f'`Queue Position: {info}`'
        if error_prompt:
            response_message += ' `Auto-Fix Prompt`'
        if default_sampler_used:
            response_message += f' `Default Sampler: {config["command_params"]["default_sampler"]}`'

        if response == LoadDistributionManager.Status.QUEUED:
            await ctx.send(response_message)
        elif response == LoadDistributionManager.Status.IN_QUEUE:
            await ctx.send(f'**Chill bro I only have 1 GPU.**\n `Your Position: {info + 1}`', ephemeral=True)
        else:
            embed = discord.Embed(title='Encountered an error: ',
                                  description=str(response),
                                  color=0xff0000)
            await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="template",
        description="Get a prompt template of a character"
    )
    @app_commands.describe(character="Character template")
    @app_commands.choices(character=[
        app_commands.Choice(name=key, value=key) 
        for key in config['template'].keys()
    ])
    async def template(self, ctx: Context, character: str):
        template_value = config['template'][character]
        await ctx.send(f"**Copy paste the prompt of `{character}` below (you can also adjust to your likings):**")
        await ctx.channel.send(template_value)

    @commands.hybrid_command(
        name="generate_from_infotext", 
        description="Generate an image from a .txt file or a text"
    )
    @app_commands.describe(
        file="The .txt file containing the prompt and other parameters",
        text="The text prompt with parameters"
    )
    async def generate_from_infotext(
        self, ctx: Context, 
        file: discord.Attachment = None, 
        text: str = None
    ):
        if not file and not text:
            await ctx.send("Please provide either a .txt file or a text prompt.", ephemeral=True)
            return
        
        if file:
            content = await file.read()
            content = content.decode("utf-8")
        else:
            content = text

        params = self._parse_parameters(content)
        
        await self.generate_base(ctx, **params)

    def _parse_parameters(self, content: str) -> dict:
        params = {
            'prompt': '',
            'negative_prompt': None,
            'width': None,
            'height': None,
            'steps': None,
            'sampler': None,
            'guidance_scale': None,
            'seed': None,
        }
        
        step_match = re.search(r"Steps:\s*(\d+)", content)
        sampler_match = re.search(r"Sampler:\s*([a-zA-Z0-9\+\s]+)", content)
        guidance_scale_match = re.search(r"CFG scale:\s*([\d\.]+)", content)
        seed_match = re.search(r"Seed:\s*(\d+)", content)
        size_match = re.search(r"Size:\s*(\d+)x(\d+)", content)

        # Extracting negative prompt
        negative_prompt_start = content.find("Negative prompt:") + len("Negative prompt:")
        negative_prompt_end = content.find("Steps:")
        negative_prompt = content[negative_prompt_start:negative_prompt_end].strip()
        params['negative_prompt'] = negative_prompt
        
        # Update params dictionary if matches are found
        if step_match:
            params['steps'] = int(step_match.group(1))
        if sampler_match:
            params['sampler'] = sampler_match.group(1).strip()
        if guidance_scale_match:
            params['guidance_scale'] = float(guidance_scale_match.group(1))
        if seed_match:
            params['seed'] = int(seed_match.group(1))
        if size_match:
            params['width'] = int(size_match.group(1))
            params['height'] = int(size_match.group(2))
   
        # Extract the prompt part
        prompt_part = content.split("Negative prompt:")[0].strip()
        params['prompt'] = prompt_part
        return params
        
async def setup(bot) -> None:
    await bot.add_cog(Sd(bot))
