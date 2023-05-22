from pathlib import Path
from discord import Guild, TextChannel
from discord.ext.commands import Bot
from repository.soundboard_repo import SoundboardRepository

from cog.cog_utils.resolver import get_guild_object, get_message_object, get_channel_object

# Hash file to get a unique id
import hashlib

# Time hashing for performance testing
import time

from repository.soundboard_table import SoundBiteGuild
from view.soundboard.sound_board import SoundBoardView, SoundButton

def hash_file(file: Path) -> str:
    start = time.time()
    hash = hashlib.sha256(file.read_bytes()).hexdigest()
    end = time.time()

    print(f"Hashing took {end - start} seconds")
    return hash


class SoundboardManager:

    def __init__(
        self,
        repository: SoundboardRepository,
        bot: Bot,
    ):
        self.repository = repository
        self.bot = bot

    
    async def get_guild_model(self, guild_id: int) -> SoundBiteGuild:
        return await self.repository.get_guild(guild_id)
    
    async def get_channel_id(self, guild_id: int) -> int | None:
        guild = await self.repository.get_guild(guild_id)
        return guild.channel_id

    async def get_channel_object(self, guild_id: int) -> TextChannel:
        channel_id = await self.get_channel_id(guild_id)
        if channel_id is None:
            raise ValueError(f"Channel with id: {channel_id} not found")
        return await get_channel_object(self.bot, channel_id)

    async def create_soundboard(
        self,
        guild_id: int,
        channel_id: int,
        control_panel_message_id: int,
    ) -> None:
        current_guild_id = None
        try:
            guild = await self.repository.get_guild(guild_id)
            current_guild_id = guild.id
        except ValueError:
            guild_object = await get_guild_object(self.bot, guild_id)
            current_guild_id = await self.repository.add_guild(
                guild_id=guild_object.id,
                guild_name=guild_object.name,
                channel_id=channel_id,
                control_panel_message_id=control_panel_message_id,
            )
        
    async def create_soundbite(
        self,
        soundbite_name: str,
        file_name: str,
        file_size: float,
        file_path: str,
        guild_id: int,
    ) -> str | None:
        
        hash = hash_file(Path(file_path))

        try:
            await self.repository.get_soundbite(hash)
        except ValueError:
            return await self.repository.create_soundbite(
                id=hash,
                soundbite_name=soundbite_name,
                file_name=file_name,
                file_size=file_size,
                file_path=file_path,
                guild_id=guild_id,
            )

    async def add_category(
        self,
        id: int,
        category_name: str,
        guild_id: int,
        message_id: int | None = None,
        priority: int = 0,
    ) -> int:
        return await self.repository.add_category(
            id=id,
            category_name=category_name,
            guild_id=guild_id,
            message_id=message_id,
            priority=priority,
        )

    async def update_category(
        self,
        category_id: int,
        category_name: str | None = None,
        message_id: int | None = None,
        priority: int | None = None,
    ):
        await self.repository.update_category(
            category_id=category_id,
            category_name=category_name,
            message_id=message_id,
            priority=priority,
        )
        self.bot.dispatch("category_edited", category_id)

    async def remove_category(self, category_id: int):
        await self.repository.remove_category(category_id=category_id)

    async def add_view_message(
        self,
        category_id: int,
        view_message_id: int,
    ):
        await self.repository.add_view_message(
            category_id=category_id,
            view_message_id=view_message_id,
        )

    async def initialise_database(self, guild_id: int):

        # Fetch all soundbites from the data directory
        file_iterator = Path("data/sound_bites").iterdir()

        for file in file_iterator:
            if not file.is_file():
                continue

            file_name = file.name
            file_size = file.stat().st_size
            file_path = file.absolute()

            hash = hash_file(file)

            try:
                await self.repository.get_soundbite(hash)
            except ValueError:
                guild = await get_guild_object(self.bot, guild_id)
                try:
                    await self.repository.get_guild(guild_id)
                except ValueError:
                    await self.repository.add_guild(
                        guild_id=guild_id,
                        guild_name=guild.name,
                        channel_id=None,
                        control_panel_message_id=None,
                    )
                await self.repository.create_soundbite(
                    id=hash,
                    soundbite_name=file_name,
                    file_name=file_name,
                    file_size=file_size,
                    file_path=str(file_path),
                    guild_id=guild_id,
                )


    def create_soundboard_view_list(self, bot: Bot)-> list[SoundBoardView]:
        soundboard_view_list = []
        view = SoundBoardView()
        count = 1
        file_iterator = Path("data/sound_bites").iterdir()

        for file in file_iterator:
            view.add_item(SoundButton(bot, file.stem))
            count += 1
            # If there are more than 25 buttons, create a new view
            if count == 25:
                soundboard_view_list.append(view)
                view = SoundBoardView()
        else:  # Send the last view
            soundboard_view_list.append(view)
        return soundboard_view_list
