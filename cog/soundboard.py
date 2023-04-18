import aiohttp
from pathlib import Path
from discord.ext import commands
from discord import (
    Interaction,
    app_commands,
    CategoryChannel,
    VoiceClient,
    Member,
    VoiceState
)
import discord
from view.soundboard.sound_board import SoundBoardView, SoundButton
from view.soundboard.streamable_submission import StreamableSubmission

from view.soundboard.upload_submission import UploadSubmission


class SoundBoardCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.soundboard_channel: discord.TextChannel | None = None
        self.ffmpeg_path = Path("ffmpeg.exe")

        # Creates partially persistent view when cog is loaded
        for view in self.create_soundboard_view():
            # Will only add view if it already exist
            # TODO: Use db to store differences to determine if view needs to be updated
            self.bot.add_view(view=view)

        print('SoundBoardCog loaded')

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
                if before.channel.members is None: # type: ignore
                    return
                if len(before.channel.members) == 1 and self.bot.user in before.channel.members: # type: ignore # noqa
                    if before.channel.guild.voice_client: # type: ignore
                        await before.channel.guild.voice_client.disconnect(force=True) # type: ignore # noqa
            if member == self.bot.user:
                if len(after.channel.members) == 1 and self.bot.user in after.channel.members:# type: ignore # noqa
                    if after.channel.guild.voice_client: # type: ignore
                        await after.channel.guild.voice_client.disconnect(force=True)# type: ignore # noqa
        except AttributeError:
            pass


    @commands.Cog.listener()
    async def on_play(self, interaction: Interaction, custom_id: str):
        """Custom listener for when bot is going to play audio."""

        # Fetch voice client
        if not interaction.guild:
            raise ValueError("Interaction does not have a guild.")

        voice_client = interaction.guild.voice_client

        # Check if bot is connected to a voice channel
        if not voice_client:
            voice_client = \
                await interaction.user.voice.channel.connect()  # type: ignore

        # Check if bot is in the same voice channel as the user
        if self.bot.user not in interaction.channel.members:  # type: ignore
            voice_client = \
                await interaction.user.voice.channel.connect()  # type: ignore

        if not voice_client:
            return ValueError("Voice client could not be connected.")

        if voice_client.is_playing():  # type: ignore
            voice_client.stop()  # type: ignore

        # Prepare audio source
        file_path = Path(f"data/sound_bites/{custom_id}.mp3")
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(
                source=file_path,  # type: ignore
            ),
            volume=0.55
        )

        voice_client.play(  # type: ignore
            source=source,
        )

    def create_soundboard_view(self) -> list[SoundBoardView]:

        soundboard_view_list = []
        view = SoundBoardView()
        count = 1
        file_iterator = Path("data/sound_bites").iterdir()

        for file in file_iterator:
            view.add_item(SoundButton(self.bot, file.stem))
            count += 1
            # If there are more than 25 buttons, create a new view
            if count == 25:
                soundboard_view_list.append(view)
                view = SoundBoardView()
        else:  # Send the last view
            soundboard_view_list.append(view)
        return soundboard_view_list

    @commands.Cog.listener()
    async def on_soundboard_update(self, interaction: Interaction):
        if not interaction.guild:
            raise ValueError("Interaction does not have a guild.")

        # Find if category channel exists
        category: CategoryChannel | None = discord.utils.find(  # type: ignore
            lambda c: c.name == 'soundboard' and isinstance(
                c, discord.CategoryChannel),
            interaction.guild.channels
        )

        if category is None:
            category = await interaction.guild.create_category('soundboard')

        # Clone channel to delete old views
        channel = discord.utils.find(
            lambda c: c.name == 'page-1' and isinstance(
                c, discord.TextChannel),
            interaction.guild.channels
        )

        if channel is None:
            new_channel = await interaction.guild.create_text_channel(
                name='page-1',
                category=category
            )
            self.soundboard_channel = new_channel
        else:
            new_channel = await channel.clone()
            await channel.delete()

        soundboard_view_list = self.create_soundboard_view()

        for view in soundboard_view_list:
            if isinstance(new_channel, discord.TextChannel):
                await new_channel.send(
                    view=view,
                )

        # Confirmation message
        if interaction is not None:
            if interaction.type.value == 2:
                await interaction.response.send_message(
                    content='Soundboard updated.',
                    ephemeral=True
                )

    @app_commands.command(
        description="Server boost: T1 - 8mb, T2 - 50mb, T3 - 100mb", name='upload'
    )
    async def upload(self, interaction: Interaction, file: discord.Attachment):
        # TODO: check guild level for size limit.
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

        voice_client: VoiceClient = interaction.guild.voice_client  # type: ignore
        if interaction.user.voice is None:  # type: ignore
            await interaction.response.send_message(
                content='You need to be in a voice channel to use this command.'
            )
        elif voice_client is not None:
            if voice_client.is_connected() is True:
                name = interaction.channel.name  # type: ignore
                if not interaction.guild:
                    raise ValueError("Interaction does not have a guild.")
                try:
                    await interaction.guild.voice_client.disconnect()  # type: ignore
                except Exception as e:
                    print(e)
                await interaction.response.send_message(
                    content=f"Bearbot disconnected from {name}"
                )
        else:
            await interaction.response.send_message(
                content="Bearbot is not connected to a voice channel.",
                ephemeral=True
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

    async def cog_unload(self):
        if self.soundboard_channel is not None:
            await self.soundboard_channel.delete()
        await super().cog_unload()


async def setup(bot):
    await bot.add_cog(SoundBoardCog(bot))


async def teardown(bot):
    await bot.remove_cog(SoundBoardCog(bot))
