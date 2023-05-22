from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from repository.soundboard_table import (
    Soundbite,
    SoundBiteCategory,
    SoundBiteGuild,
    SoundbiteViewMessage,
)


class SoundboardRepository:
    def __init__(self, session: async_sessionmaker[AsyncSession]) -> None:
        self.database = session

    async def add_guild(
        self,
        guild_id: int,
        guild_name: str,
        channel_id: int | None,
        control_panel_message_id: int | None,
    ) -> int:
        async with self.database() as session:
            guild = await session.get(SoundBiteGuild, guild_id)
            if isinstance(guild, SoundBiteGuild):
                if guild.control_panel_message_id != control_panel_message_id:
                    guild.control_panel_message_id = control_panel_message_id
                elif guild.channel_id != channel_id:
                    guild.channel_id = channel_id
            else:
                guild = SoundBiteGuild(
                    id=guild_id,
                    name=guild_name,
                    control_panel_message_id=control_panel_message_id,
                    channel_id=channel_id,
                )
            session.add(guild)
            await session.commit()
            return guild.id

    async def get_guild(self, guild_id: int) -> SoundBiteGuild:
        async with self.database() as session:
            guild = await session.get(SoundBiteGuild, guild_id)
            if not isinstance(guild, SoundBiteGuild):
                raise ValueError("Guild not found")
            return guild


    async def get_control_panel_message_id(self, guild_id: int) -> int | None:
        async with self.database() as session:
            guild = await session.get(SoundBiteGuild, guild_id)
            if not isinstance(guild, SoundBiteGuild):
                raise ValueError("Guild not found")
            return guild.control_panel_message_id
        
    async def get_soundbite(self, soundbite_id: str) -> Soundbite:
        async with self.database() as session:
            soundbite = await session.get(Soundbite, soundbite_id)
            if not isinstance(soundbite, Soundbite):
                raise ValueError("Soundbite not found")
            return soundbite
    
    async def create_soundbite(
        self,
        id: str,
        soundbite_name: str,
        file_name: str,
        file_size: float,
        file_path: str,
        guild_id: int,
    ) -> str:
        async with self.database() as session:
            new_soundbite = Soundbite(
                id=id,
                soundbite_name=soundbite_name,
                file_name=file_name,
                file_size=file_size,
                file_path=file_path,
                guild_id=guild_id,
            )
            session.add(new_soundbite)
            await session.commit()

            guild = await session.get(SoundBiteGuild, guild_id)
            if not isinstance(guild, SoundBiteGuild):
                raise ValueError("Guild not found")
            return new_soundbite.id
    
    async def remove_soundbite(self, soundbite_id: int) -> None:
        async with self.database() as session:
            await session.delete(soundbite_id)
            await session.commit()

    async def add_category(
        self,
        id: int,
        category_name: str,
        guild_id: int,
        message_id: int | None = None,
        priority: int = 0,
    ) -> int:
        async with self.database() as session:
            new_category = SoundBiteCategory(
                id=id,
                name=category_name,
                guild_id=guild_id,
                message_id=message_id,
                priority=priority,
            )
            session.add(new_category)
            await session.commit()
            return new_category.id
    
    async def remove_category(self, category_id: int) -> None:
        async with self.database() as session:
            await session.delete(category_id)
            await session.commit()

    async def update_category(
        self,
        category_id: int,
        category_name: str | None = None,
        message_id: int | None = None,
        priority: int | None = None
    ) -> None:
        async with self.database() as session:
            category = await session.get(SoundBiteCategory, category_id)
            
            if not isinstance(category, SoundBiteCategory):
                raise ValueError("Category not found")

            category.name = category_name if category_name is not None else category.name
            category.message_id = message_id if message_id is not None else category.message_id
            category.priority = priority if priority is not None else category.priority
            await session.commit()

    async def add_view_message(
        self,
        category_id: int,
        view_message_id: int,
    ) -> int:
        async with self.database() as session:
            category = await session.get(SoundBiteCategory, category_id)
            
            if not isinstance(category, SoundBiteCategory):
                raise ValueError("Category not found")

            soundbite_view_message = SoundbiteViewMessage(
                id=view_message_id,
                category_id=category_id
            )

            category.soundbite_view_messages.append(soundbite_view_message)
            await session.commit()
            return soundbite_view_message.id
    
    async def remove_view_message(self, view_message_id: int) -> None:
        async with self.database() as session:
            view_message = await session.get(SoundbiteViewMessage, view_message_id)
            if view_message:
                await session.delete(view_message)
                await session.commit()

    async def add_soundbite_to_category(
        self,
        soundbite_id: int,
        category_id: int,
    ) -> None:
        async with self.database() as session:
            category = await session.get(SoundBiteCategory, category_id)
            
            if not isinstance(category, SoundBiteCategory):
                raise ValueError("Category not found")

            soundbite = await session.get(Soundbite, soundbite_id)
            
            if not isinstance(soundbite, Soundbite):
                raise ValueError("Soundbite not found")

            

            await session.commit()

