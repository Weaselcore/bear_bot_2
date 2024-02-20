import asyncio
import logging
import logging.handlers
import os
from pathlib import Path
from typing import Literal

import discord
from discord.ext import commands
from discord.ext.commands import Context, Greedy
from dotenv import load_dotenv


class MyClient(commands.Bot):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(
            command_prefix="/",
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self) -> None:
        await self.load_extension("cog.scheduler")
        await self.load_extension("cog.reminder")
        await self.load_extension("cog.lobby")
        await self.load_extension("cog.soundboard")
        await self.load_extension("cog.poll")
        await self.load_extension("cog.utils")
        await self.load_extension("cog.timezone")
        await self.load_extension("cog.piper")

    async def close(self) -> None:
        await super().close()


async def main():
    logger = logging.getLogger("discord")
    logger.setLevel(logging.INFO)

    log_dir = Path("logs")
    # Ensure the directory exists; create it if it doesn't
    log_dir.mkdir(parents=True, exist_ok=True)

    handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "discord.log",
        encoding="utf-8",
        maxBytes=32 * 1024 * 1024,  # 32 MiB
        backupCount=5,  # Rotate through 5 files
    )
    dt_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(
        "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    load_dotenv()
    print("Retrieving token...")

    async with MyClient(intents=discord.Intents.all()) as bot:

        @bot.event
        async def on_ready():
            # type: ignore
            print(f"Logged in as {bot.user} (ID: {bot.user.id})")
            print("------")

        # Register the commands.
        @bot.tree.command(name="hi")
        async def hi(interaction: discord.Interaction):
            await interaction.response.send_message(f"Hi, {interaction.user.mention}")

        @bot.tree.command(name="ping")
        async def ping(interaction: discord.Interaction):
            await interaction.response.send_message(f"Pong! {bot.latency * 1000:.2f}ms")

        @bot.command()
        @commands.guild_only()
        @commands.is_owner()
        async def mitsync(
            ctx: Context,
            guilds: Greedy[discord.Object],
            option: Literal["~", "*", "^"] | None = None,
        ) -> None:
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

                suffix = "globally" if option is None else "to the current guild."

                await ctx.send(
                    f"Whoeauh! Synced {len(synced)} commands {suffix} \
in a very Mit manner."
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
        await bot.start(os.environ["TOKEN"])


asyncio.run(main(), debug=False)
