import asyncio
import os
import logging
import logging.handlers
from typing import Optional
from discord.ext.commands import Bot  # type: ignore
from discord import Object, Intents, Interaction
from discord.app_commands import AppCommand

from stubs.lobby_types import LobbyModel

GUILD = Object(id=299536709778014210)
TEST_GUILD = Object(id=613605418882564096)
DEV = True


class MyClient(Bot):  # type: ignore
    def __init__(self, *, intents: Intents):
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
    # noinspection PyAttributeOutsideInit
    async def setup_hook(self) -> None:
        # await self.load_extension('cog.lobby')
        # await self.load_extension('cog.soundboard')
        await self.load_extension('cog.battleship')
        if DEV:
            guild_to_sync = TEST_GUILD
        else:
            guild_to_sync = GUILD
        self.tree.copy_global_to(guild=guild_to_sync)
        await self.tree.sync(
            guild=guild_to_sync
        )
        # TODO: Persistent?
        self.lobby: dict[int, LobbyModel] = {}
        # Any database would be initialised here.


async def main() -> None:
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

    async with MyClient(intents=Intents.all()) as bot:

        # Register the commands.
        @bot.event  # type: ignore
        async def on_ready() -> None:
            print(f'Logged in as {bot.user} (ID: {bot.user.id})')
            print('------')

        @bot.tree.command(name="hi")  # type: ignore
        async def hi(interaction: Interaction) -> None:
            await interaction.response.send_message(f'Hi, {interaction.user.mention}')

        @bot.tree.command(name="sync")  # type: ignore
        async def sync(interaction: Interaction) -> None:
            if interaction.guild is None:
                return await interaction.response.send_message(
                    "This command can only be used in a guild.",
                    ephemeral=True
                )
            if interaction.user == interaction.guild.owner:
                # This copies the global commands over to your guild.
                if DEV:
                    guild_to_sync = TEST_GUILD
                else:
                    guild_to_sync = GUILD
                bot.tree.copy_global_to(guild=guild_to_sync)
                synced_commands: Optional[list[AppCommand]] = await bot.tree.sync(
                    guild=guild_to_sync
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
