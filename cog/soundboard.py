import asyncio
from typing import Any, Optional, cast
import aiohttp
from pathlib import Path
from discord.ext import commands
from discord.ext.commands import Bot, Cog
from discord import Interaction, app_commands, VoiceClient, Member, TextChannel, VoiceState, VoiceChannel, \
    InteractionType
import discord
from view.soundboard.sound_board import SoundBoardView, SoundButton
from view.soundboard.streamable_submission import StreamableSubmission

from view.soundboard.upload_submission import UploadSubmission


class SoundBoardCog(Cog):  # type: ignore
    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        self.soundboard_channel: Optional[discord.TextChannel] = None
        self.ffmpeg_path = Path("ffmpeg.exe")
        print('SoundBoardCog loaded')

    @commands.Cog.listener()  # type: ignore
    async def on_play(self, interaction: Interaction, custom_id: str) -> None:
        # Get file from custom id
        # Fetch voice client
        if interaction.guild is None or interaction.user is None:
            return
        voice_client = interaction.guild.voice_client
        # Check if bot is connected to a voice channel
        if voice_client is None:
            member = cast(Member, interaction.user)
            voice_state = cast(VoiceState, member.voice)
            channel = cast(VoiceChannel, voice_state.channel)
            voice_client = await channel.connect()
        else:
            if interaction.type == InteractionType.application_command:
                await interaction.response.send_message(
                    content='Bearbot is already playing.',
                    ephemeral=True
                )
                return
            else:
                await interaction.response.defer()
                return
        # Prepare audio source
        file_path = Path(f"data/sound_bites/{custom_id}.mp3")
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(
                source=file_path,  # type: ignore
            ),
            volume=0.55
        )

        # Create callback co-routine to disconnect after playing
        def after_playing(error: Any, voice_client: VoiceClient) -> None:
            coroutine = voice_client.disconnect(force=False)
            future = asyncio.run_coroutine_threadsafe(coroutine, self.bot.loop)
            try:
                future.result()
            except Exception:
                print(error)

        client = cast(VoiceClient, voice_client)

        client.play(
            source=source,
            after=lambda error: after_playing(error, client)
        )
        # Responds if the event is fired by a command.
        if interaction.type == InteractionType.application_command:
            await interaction.response.send_message(
                content=f'Playing {custom_id}.mp3',
                ephemeral=True
            )
        else:
            await interaction.response.defer()

    @commands.Cog.listener()  # type: ignore
    async def on_soundboard_update(self, interaction: Interaction):
        if interaction.guild is None:
            return
        # Find if category channel exists
        category = discord.utils.find(
            lambda c: c.name == 'soundboard' and isinstance(c, discord.CategoryChannel),
            interaction.guild.categories
        )
        if category is None:
            category = await interaction.guild.create_category('soundboard')
        # Clone channel to delete old views
        channel = discord.utils.find(
            lambda c: c.name == 'page-1' and isinstance(c, discord.TextChannel),
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

        view = SoundBoardView()
        # Create persistent soundboard views
        count = 1
        file_iterator = Path("data/sound_bites").iterdir()
        for file in file_iterator:
            view.add_item(SoundButton(self.bot, file.stem))
            count += 1
            # If there are more than 25 buttons, create a new view
            if count == 25:
                await new_channel.send(
                    view=view,
                )
                view = SoundBoardView()
        else:  # Send the last view
            await new_channel.send(
                view=view,
            )

        # Confirmation message
        if interaction is not None:
            if interaction.type == InteractionType.application_command:
                await interaction.response.send_message(
                    content='Soundboard updated.',
                    ephemeral=True
                )

    @app_commands.command(
        description="Server boost: T1 - 8mb, T2 - 50mb, T3 - 100mb", name='upload'
    )
    async def upload(self, interaction: Interaction, file: discord.Attachment) -> None:
        # TODO check guild level for size limit.
        await interaction.response.send_modal(
            UploadSubmission(self.bot, file),
        )

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

    @app_commands.command(description="Manually update soundboard", name='update')
    async def update(self, interaction: Interaction) -> None:
        self.bot.dispatch("soundboard_update", interaction)

    @app_commands.command(description="Play soundbite", name='play')
    @app_commands.autocomplete(name=file_search)
    async def play(self, interaction: Interaction, name: str) -> None:
        self.bot.dispatch("play", interaction, name)

    @app_commands.command(description="Delete soundbite", name='delete')
    @app_commands.autocomplete(name=file_search)
    async def delete(self, interaction: Interaction, name: str) -> None:
        filename = Path(f"data/sound_bites/{name}.mp3")
        if filename.is_file():
            filename.unlink()
            self.bot.dispatch("soundboard_update", interaction)
        else:
            await interaction.response.send_message(
                content=f"{name}.mp3 does not exist. Please report this."
            )

    @app_commands.command(description="Stop voice client", name='stop')
    async def stop(self, interaction: Interaction) -> None:
        if interaction.guild is None:
            return
        voice_client = interaction.guild.voice_client
        user = cast(Member, interaction.user)
        if user.voice is None:
            await interaction.response.send_message(
                content='You need to be in a voice channel to use this command.'
            )
        elif voice_client is not None:
            client = cast(VoiceClient, voice_client)
            if client.is_connected() is True:
                name = cast(TextChannel, interaction.channel).name
                await cast(VoiceClient, interaction.guild.voice_client).disconnect()
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
    async def streamable(self, interaction: Interaction, url: str) -> None:

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response_text = await response.text()
                url_patterns = '<meta property="og:video:url" content="', '">'
                video_url = response_text.split(url_patterns[0])[1].split(url_patterns[1])[0] \
                    if url_patterns[0] in response_text else None
                name_patterns = '/video/mp4/', '?'
                file_name = response_text.split(name_patterns[0])[1].split(name_patterns[1])[0] \
                    if name_patterns[0] in response_text else 'video.mp4'
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
    async def create_soundboard_channel(self, interaction: Interaction) -> None:
        self.bot.dispatch("soundboard_update", interaction)

    async def cog_unload(self) -> None:
        if self.soundboard_channel is not None:
            await self.soundboard_channel.delete()
        await super().cog_unload()


async def setup(bot: Bot) -> None:
    await bot.add_cog(SoundBoardCog(bot))


async def teardown(bot: Bot) -> None:
    await bot.remove_cog(SoundBoardCog(bot).qualified_name)
