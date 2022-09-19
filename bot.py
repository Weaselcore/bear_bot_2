import asyncio
import os
from typing import List
import discord
import logging
import logging.handlers
from discord.ext import commands

# MY_GUILD = discord.Object(id=613605418882564096)  # replace with your guild id
MY_GUILD = discord.Object(id=299536709778014210)  # replace with your guild id


class MyClient(commands.Bot):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(command_prefix="/", intents=intents)
        # A CommandTree is a special type that holds all the application command
        # state required to make it work. This is a separate class because it
        # allows all the extra state to be opt-in.
        # Whenever you want to work with application commands, your tree is used
        # to store and work with them.
        # Note: When using commands.Bot instead of discord.Client, the bot will
        # maintain its own tree instead.
        # self.tree = app_commands.CommandTree(self)

    # In this basic example, we just synchronize the app commands to one guild.
    # Instead of specifying a guild to every command, we copy over our global commands instead.
    # By doing so, we don't have to wait up to an hour until they are shown to the end-user.
    async def setup_hook(self) -> None:
        await self.load_extension('cog.lobby')
        await self.load_extension('cog.soundboard')
        # self.tree.copy_global_to(guild=MY_GUILD)
        # await self.tree.sync(guild=MY_GUILD)
        # TODO: Make this more dynamic
        self.lobby = {}
        # Any database would be initialised here.


async def main():
    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)

    handler = logging.handlers.RotatingFileHandler(
        filename='discord.log',
        encoding='utf-8',
        maxBytes=32 * 1024 * 1024,  # 32 MiB
        backupCount=5,  # Rotate through 5 files
    )
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(
        '[{asctime}] [{levelname:<8}] {name}: {message}',
        dt_fmt, style='{'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    async with MyClient(intents=discord.Intents.all()) as bot:

        # Register the commands.
        @bot.event
        async def on_ready():
            print(f'Logged in as {bot.user} (ID: {bot.user.id})')
            print('------')

        @bot.tree.command(name="hi")
        async def hi(interaction: discord.Interaction):
            await interaction.response.send_message(f'Hi, {interaction.user.mention}')

        @bot.tree.command(name="sync")
        async def sync(interaction: discord.Interaction):
            if interaction.user == interaction.guild.owner:
                # This copies the global commands over to your guild.
                bot.tree.copy_global_to(guild=MY_GUILD)
                synced_commands: List[discord.AppCommand] | None = await bot.tree.sync(
                    guild=MY_GUILD
                )
                if synced_commands is None:
                    await interaction.response.send_message(
                        content="No commands to sync"
                    )
                else:
                    await interaction.response.send_message(
                        content=f'Synced {len(synced_commands)} commands'
                    )
            else:
                await interaction.response.send_message(content="You are not the guild owner")

        # Start the bot.
        await bot.start(os.environ['TOKEN'])
asyncio.run(main())
