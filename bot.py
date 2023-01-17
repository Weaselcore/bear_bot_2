import asyncio
import os
from typing import List, Literal
import discord
import logging
import logging.handlers
from discord.ext import commands
from dotenv import load_dotenv
from discord.ext.commands import Context, Greedy


class MyClient(commands.Bot):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(command_prefix="/", intents=intents, help_command=None)
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
        await self.load_extension('cog.ai')
        # await self.load_extension('cog.quiz')
        self.lobby = {} # type: ignore
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

    load_dotenv()
    print("Retrieving token...")

    async with MyClient(intents=discord.Intents.all()) as bot:

        # Register the commands.
        @bot.event
        async def on_ready():
            print(f'Logged in as {bot.user} (ID: {bot.user.id})')
            print('------')

        @bot.tree.command(name="hi")
        async def hi(interaction: discord.Interaction):
            await interaction.response.send_message(f'Hi, {interaction.user.mention}')


        @bot.command()
        @commands.guild_only()
        @commands.is_owner()
        async def sync(
        ctx: Context, guilds: Greedy[discord.Object], option: Literal["~", "*", "^"] | None = None) -> None:
            if not guilds:
                if option == "~":
                    synced = await ctx.bot.tree.sync(guild=ctx.guild)
                elif option == "*":
                    ctx.bot.tree.copy_global_to(guild=ctx.guild)
                    synced = await ctx.bot.tree.sync(guild=ctx.guild)
                elif option == "^":
                    ctx.bot.tree.clear_commands(guild=ctx.guild)
                    await ctx.bot.tree.sync(guild=ctx.guild)
                    synced = []
                else:
                    synced = await ctx.bot.tree.sync()

                await ctx.send(
                    f"Synced {len(synced)} commands {'globally' if option is None else 'to the current guild.'}"
                )
                return

            returned = 0
            for guild in guilds:
                try:
                    await ctx.bot.tree.sync(guild=guild)
                except discord.HTTPException:
                    pass
                else:
                    returned += 1

            await ctx.send(f"Synced the tree to {returned}/{len(guilds)}.")


        # Start the bot.
        await bot.start(os.environ['TOKEN'])
asyncio.run(main())
