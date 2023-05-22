from code import interact
import aiohttp
from datetime import datetime
from discord import (
    Attachment,
    Embed,
    Guild,
    Interaction,
    CategoryChannel,
    FFmpegPCMAudio,
    VoiceChannel,
    VoiceClient,
    Member,
    PCMVolumeTransformer,
    TextChannel,
    VoiceState,
    app_commands,
    utils
)
from discord.ext import commands
from dotenv import load_dotenv
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from cog.cog_utils.resolver import get_guild_object
from manager.soundboard_service import SoundboardManager
from repository.db_config import Base
from repository.soundboard_repo import SoundboardRepository
from repository.soundboard_table import (
    SoundBiteCategory,
    SoundBiteGuild,
    Soundbite,
    SoundbiteGuildAssociation,
    SoundbiteViewMessage
)

from view.soundboard.sound_board import (
    ControlPanelView,
)
from view.soundboard.streamable_submission import StreamableSubmission
from view.soundboard.upload_submission import UploadSubmission

load_dotenv()

# Construct database url from environment variables
DATABASE_URL = "postgresql+asyncpg://{}:{}@{}:{}/{}".format(
    os.environ['SB_PG_USER'],
    os.environ['SB_PG_PASSWORD'],
    os.environ['SB_PG_HOST'],
    os.environ['SB_PG_PORT'],
    os.environ['SB_PG_DATABASE']
)

# Create database engine
engine = create_async_engine(
    DATABASE_URL,
    pool_size=3,
    future=True,
    echo=True,
)


# This is the database session factory, invoking this variable creates a new session
async_session = async_sessionmaker(
    engine,
    expire_on_commit=False,
)

class SoundBoardCog(commands.GroupCog, name="soundboard"):
    def __init__(self, bot: commands.Bot, soundboard_manager: SoundboardManager):
        self.bot: commands.Bot = bot
        self.soundboard_manager = soundboard_manager

        self.ffmpeg_path = Path("ffmpeg.exe")

        # Creates partially persistent view when cog is loaded
        self.bot.add_view(
            view=ControlPanelView(bot=self.bot)
        )

        for view in self.soundboard_manager.create_soundboard_view_list(self.bot):
            # Will only add view if it already exist
            self.bot.add_view(view=view)

        print('SoundBoardCog loaded')

    async def create_soundboard_channels(self, guild: Guild) -> TextChannel:
        """Creates a category channel for the guild if it does not exist."""

        # Find if category channel exists
        category: CategoryChannel | None = utils.find(  # type: ignore
            lambda c: c.name == 'soundboard' and isinstance(
                c, CategoryChannel),
            guild.channels
        )

        if category is None:
            category = await guild.create_category('soundboard')

        # Clone channel to delete old views
        channel = utils.find(
            lambda c: c.name == 'page-1' and isinstance(
                c, TextChannel),
            guild.channels
        )

        if channel is None:
            new_channel = await guild.create_text_channel(
                name='page-1',
                category=category
            )
            return new_channel
        else:
            new_channel = await channel.clone()
            await channel.delete()
            return new_channel # type: ignore

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: Member,
        before: VoiceState,
        after: VoiceState
    ):

        # If user is the only user and disconnects, disconnect bot
        try:
            if not member == self.bot.user:
                if before.channel.members is None:  # type: ignore
                    return
                if len(before.channel.members) == 1 and self.bot.user in before.channel.members:  # type: ignore # noqa
                    if before.channel.guild.voice_client:  # type: ignore
                        await before.channel.guild.voice_client.disconnect(force=True)  # type: ignore # noqa
            if member == self.bot.user:
                if len(after.channel.members) == 1 and self.bot.user in after.channel.members:  # type: ignore # noqa
                    if after.channel.guild.voice_client:  # type: ignore
                        await after.channel.guild.voice_client.disconnect(force=True)  # type: ignore # noqa
        except AttributeError:
            pass

    @commands.Cog.listener()
    async def on_play(self, interaction: Interaction, custom_id: str):
        """Custom listener for when bot is going to play audio."""

        # Fetch voice client
        if not interaction.guild:
            raise ValueError("Interaction does not have a guild.")
        
        voice_client = interaction.guild.voice_client

        assert isinstance(interaction.user, Member)
        assert isinstance(interaction.user.voice, VoiceState)
        assert isinstance(interaction.user.voice.channel, VoiceChannel)

        # Check if bot is connected to a voice channel
        if not voice_client:
            voice_client = await interaction.user.voice.channel.connect()

        # Check if bot is in the same voice channel as the user
        if self.bot.user not in interaction.channel.members: # type: ignore
            voice_client = await interaction.user.voice.channel.connect()

        if not voice_client:
            return ValueError("Voice client could not be connected.")
        
        assert isinstance(voice_client, VoiceClient)

        if voice_client.is_playing():
            voice_client.stop()

        # Prepare audio source
        file_path = Path(f"data/sound_bites/{custom_id}.mp3")
        source = PCMVolumeTransformer(
            FFmpegPCMAudio(
                source=file_path,  # type: ignore
            ),
            volume=0.55
        )

        assert interaction.channel is not None

        voice_client.play(  # type: ignore
            source=source,
        )

    @commands.Cog.listener()
    async def on_disconnect(self, interaction: Interaction):
        """Custom listener for when bot is going to stop audio."""

        if not interaction.guild:
            raise ValueError("Interaction does not have a guild.")

        voice_client = interaction.guild.voice_client

        if not voice_client:
            return

        assert isinstance(voice_client, VoiceClient)

        if voice_client.is_playing():
            voice_client.stop()
        
        await voice_client.disconnect(force=False)
        voice_client.cleanup()

    @commands.Cog.listener()
    async def on_stop(self, interaction: Interaction):
        """Custom listener for when bot is going to stop audio."""

        if not interaction.guild:
            raise ValueError("Interaction does not have a guild.")

        voice_client = interaction.guild.voice_client

        assert isinstance(voice_client, VoiceClient)

        if voice_client.is_playing():  # type: ignore
            voice_client.stop()  # type: ignore

    @commands.Cog.listener()
    async def on_soundboard_update(self, interaction: Interaction):
        await interaction.response.defer()

        if not interaction.guild:
            raise ValueError("Interaction does not have a guild.")

        channel = await self.create_soundboard_channels(interaction.guild)

        # Create control panel view
        control_panel_view = ControlPanelView(self.bot)

        message = await channel.send(
            view=control_panel_view,
        )

        # Create soundboard soundbite view with buttons
        soundboard_view_list = self.soundboard_manager.create_soundboard_view_list(self.bot)
        for view in soundboard_view_list:
            await channel.send(
                view=view,
            )

        await self.soundboard_manager.create_soundboard(
            guild_id=interaction.guild.id,
            channel_id=channel.id,
            control_panel_message_id=message.id,
        )
        
        # Confirmation message
        if interaction is not None:
            # If interaction was a slash command, respond.
            if interaction.type.value == 2:
                await interaction.followup.send(
                    content='Soundboard updated.',
                    ephemeral=True
                )


    @app_commands.command(
        description="Server boost: T1 - 25mb, T2 - 50mb, T3 - 100mb", name='upload'
    )
    async def upload(self, interaction: Interaction, file: Attachment):
        assert isinstance(interaction.guild, Guild)
        # Check file size
        file_size = file.size
        guild_filesize_limit = interaction.guild.filesize_limit

        # Discord does not provide a way to see if a user has nitro,
        # so this only works for people that have boosted the server. (Premium?)
        if interaction.user in interaction.guild.premium_subscribers:
            guild_filesize_limit = 104857600

        if guild_filesize_limit < file_size:
            await interaction.response.send_message(
                content=f'File size limit is {guild_filesize_limit} for this server.',
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            UploadSubmission(self.bot, file),
        )

    @app_commands.command(description="Manually update soundboard", name='update')
    async def update(self, interaction: Interaction):
        self.bot.dispatch("soundboard_update", interaction)

    async def file_search(
        self,
        interaction: Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:

        list_of_files = []
        count = 0
        for file in Path("data/sound_bites").iterdir():
            if file.stem.startswith(current):
                list_of_files.append(
                    app_commands.Choice(
                        name=file.stem,
                        value=file.stem
                    )
                )
                count += 1
                # Autocomplete only works with 25 choices
                if count == 25:
                    break
        return list_of_files

    @app_commands.command(description="Play soundbite", name='play')
    @app_commands.autocomplete(name=file_search)
    async def play(self, interaction: Interaction, name: str):
        self.bot.dispatch("play", interaction, name)

    @app_commands.command(description="Delete soundbite", name='delete')
    @app_commands.autocomplete(name=file_search)
    async def delete(self, interaction: Interaction, name: str):
        filename = Path(f"data/sound_bites/{name}.mp3")
        if filename.is_file():
            filename.unlink()
            self.bot.dispatch("soundboard_update", interaction)
        else:
            await interaction.response.send_message(
                content=f"{name}.mp3 does not exist. Please report this."
            )

    @app_commands.command(description="Stops and disconnects voice client", name='stop')
    async def stop(self, interaction: Interaction):

        if not interaction.guild:
            raise ValueError("Interaction does not have a guild.")
        
        if not isinstance(interaction.guild.voice_client, VoiceClient):
            await interaction.response.send_message(
            content="Bearbot is not connected to a voice channel.",
                ephemeral=True
            )
            return

        channel = interaction.guild.voice_client.channel

        voice_client = interaction.guild.voice_client 

        assert isinstance(interaction.user, Member)

        if interaction.user.voice is None:
            await interaction.response.send_message(
                content='You need to be in a voice channel to use this command.'
            )
        elif voice_client is not None:
            
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message(
                content=f"Bearbot disconnected from {channel.name}"
            )


    @app_commands.command(
        description="Create soundbite from Streamable URL",
        name='streamable'
    )
    async def streamable(self, interaction: Interaction, url: str):
        video_url = None
        file_name = None

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response_text = await response.text()
                url_patterns = '<meta property="og:video:url" content="', '">'
                video_url = response_text.split(
                    url_patterns[0]
                )[1].split(
                    url_patterns[1]
                )[0] if url_patterns[0] in response_text else None
                name_patterns = '/video/mp4/', '?'
                file_name = response_text.split(
                    name_patterns[0]
                )[1].split(
                    name_patterns[1]
                )[0] if name_patterns[0] in response_text else 'video.mp4'
        if video_url is None:
            await interaction.response.send_message(
                content="Invalid Streamable URL was given or video url not valid.",
            )
        else:
            await interaction.response.send_modal(
                StreamableSubmission(self.bot, video_url, file_name),
            )

    @app_commands.command(
        description="Initialise soundboard channel for guild.",
        name='createsoundboardchannel',
    )
    async def create_soundboard_channel(self, interaction: Interaction):
        self.bot.dispatch("soundboard_update", interaction)

    @app_commands.command(description="Create soundbite category", name='createsoundcategory')
    async def create_sound_category(self, interaction: Interaction, name: str, priority: int=0):

        if not interaction.guild:
            raise ValueError("Interaction does not have a guild.")

        # channel = await self.create_soundboard_channels(interaction.guild)
        channel = await self.soundboard_manager.get_channel_object(interaction.guild.id)
        
        message = await channel.send(
            embed=Embed(
                title="name",
                timestamp=datetime.utcnow(),
            )
        )

        await self.soundboard_manager.add_category(
            id=message.id,
            guild_id=interaction.guild.id,
            category_name=name,
            priority=priority,
            message_id=message.id,
        )

    async def cog_load(self):
        await super().cog_load()
        await self.soundboard_manager.initialise_database(613605418882564096)

    async def cog_unload(self):
        await super().cog_unload()


async def setup(bot):
    # Create all tables if they don't exist
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[
                SoundBiteGuild.__table__,
                Soundbite.__table__,
                SoundbiteGuildAssociation.__table__,
                SoundBiteCategory.__table__,
                SoundbiteViewMessage.__table__,
            ]
        )

    soundboard_repo = SoundboardRepository(session=async_session)
    soundboard_manager = SoundboardManager(
        repository=soundboard_repo,
        bot=bot,
    )
    
    soundboard_cog = SoundBoardCog(bot, soundboard_manager)

    await bot.add_cog(soundboard_cog)

async def teardown(bot):
    await bot.remove_cog(
        bot.get_cog('SoundBoardCog')
    )
