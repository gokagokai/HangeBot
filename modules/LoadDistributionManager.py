import os
import base64
import io
import time
import traceback
from enum import Enum
from collections import deque
from threading import Thread
import asyncio

import discord

from api import AutoWebUi


def _worker(queue, ip, config):
    webui = AutoWebUi.WebUi(ip)
    if webui.heartbeat():
        # print('connected to webui at', ip)
        while True:
            if queue:
                try:
                    start_time = time.time()
                    queue_obj = queue[0]  # Peek at the first item in the queue without popping it
                    response, status_code = webui.txt_to_img(queue_obj)
                    if status_code != 200:
                        embed = discord.Embed(title='Encountered an error: ',
                                              description=f'Status code: {status_code}\n{response}',
                                              color=0xff0000)
                        queue_obj.event_loop.create_task(queue_obj.ctx.channel.send(embed=embed))
                        continue
                    embed = discord.Embed(description='**Enjoy!**', color=0xFFFFE0)
                    if queue_obj.ctx.author.avatar is None:
                        embed.set_footer(
                            text=f'{queue_obj.ctx.author.name}'
                                 f'   |   compute used: {time.time() - start_time:.2f} seconds'
                                 f'   |   react with ❌ to delete'
                        )
                    else:
                        embed.set_footer(
                            text=f'{queue_obj.ctx.author.name}'
                                 f'   |   compute used: {time.time() - start_time:.2f} seconds'
                                 f'   |   react with ❌ to delete',
                            icon_url=queue_obj.ctx.author.avatar.url
                        )
                    for index, i in enumerate(response['images']):
                        count = 1
                        image_path = f'images/{queue_obj.ctx.author.id}_{index+1}_{count}.png'
                        
                        # Find a unique file name for each image
                        while os.path.exists(image_path):
                            count += 1
                            image_path = f'images/{queue_obj.ctx.author.id}_{index+1}_{count}.png'

                        # Decode and save the image
                        image = io.BytesIO(base64.b64decode(i.split(",", 1)[0]))
                        with open(image_path, 'wb') as f:
                            f.write(image.getvalue())

                        # Send the image
                        queue_obj.event_loop.create_task(queue_obj.ctx.channel.send(
                            content=f'<@{queue_obj.ctx.author.id}>',
                            file=discord.File(fp=image_path, filename=f'image_{index+1}.png'),
                            embed=embed
                        ))
                    
                    # Pop the queue only after processing is successful
                    queue.popleft()

                except:
                    tb = traceback.format_exc()
                    # check if the queue object was retrieved before the error
                    if 'queue_obj' in locals():
                        embed = discord.Embed(title='Encountered an error: ',
                                              description=str(tb),
                                              color=0xff0000)
                        # send the error to the user who requested the command that errored
                        queue_obj.event_loop.create_task(queue_obj.ctx.channel.send(embed=embed))
                    else:
                        # otherwise print to console
                        print(tb)

            time.sleep(1)
    else:
        print('Connection to webui', ip, 'failed')

class Status(Enum):
    QUEUED = 0
    IN_QUEUE = 2


class LoadDist:
    def __init__(self, ips, config):
        self.instances = []
        self.queue = deque()
        self.config = config
        self.loop = asyncio.get_event_loop()
        
        for ip in ips:
            self.instances.append(Thread(target=_worker, args=(self.queue, ip, self.config)))
        for instance in self.instances:
            instance.start()
        
        self.loop.create_task(self.update_loading(ips[0]))

    def add_to_queue(self, queue_obj):
        try:
            status = (Status.QUEUED, len(self.queue))
            for i, queued_obj in enumerate(self.queue):
                if queued_obj.ctx.author.id == queue_obj.ctx.author.id:
                    status = (Status.IN_QUEUE, i)
            if status[0] != Status.IN_QUEUE:
                self.queue.append(queue_obj)
            return status
        except:
            return traceback.format_exc(), None

    async def update_loading(self, ip):
        webui = AutoWebUi.WebUi(ip)
        bar_length = 10
        
        while True:
            if self.queue:
                queue_obj = self.queue[0]

                await asyncio.sleep(2)
                last_timestamp = None

                while True:
                    progress, _ = webui.get_progress()
                    if progress:
                        percentage = int(progress['progress'] * 100)
                        eta_seconds = progress['eta_relative']
                        eta_formatted = f"{eta_seconds:.2f}"
                        job_timestamp = progress['state']['job_timestamp']

                        completed_blocks = int(progress['progress'] * bar_length)
                        remaining_blocks = bar_length - completed_blocks

                        bar = f"{'█' * completed_blocks}{'▒' * remaining_blocks}"

                        # If the job_timestamp has changed, send a new message
                        if job_timestamp != last_timestamp and percentage != 0:
                            progress_message = await queue_obj.ctx.channel.send(
                                f"{bar} **{percentage}%**・ETA: {eta_formatted} s"
                            )
                            last_timestamp = job_timestamp
                        else:
                            # Update message with loading bar, percentage, and ETA
                            await progress_message.edit(content=f"{bar} **{percentage}%**・ETA: {eta_formatted} s")

                        # Check if generation is complete
                        if eta_seconds <= 0 or job_timestamp != last_timestamp:
                            await progress_message.edit(content=f"{'█' * bar_length} **100%**")
                            # await progress_message.delete()
                            break

                    await asyncio.sleep(2)
            else:
                await asyncio.sleep(2)
