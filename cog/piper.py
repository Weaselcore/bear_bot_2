import io
import os
import urllib.parse

import aiohttp
from discord import (DMChannel, FFmpegPCMAudio, Interaction, Member, PCMVolumeTransformer,
                     VoiceChannel, VoiceClient, VoiceState, app_commands)
from discord.ext import commands


class PiperCog(commands.GroupCog, name="piper"):
    def __init__(self, bot: commands.Bot, webserver_url: str):
        self.bot = bot
        self.webserver_url = webserver_url
        print(f"{self.__cog_name__} loaded")

    @commands.Cog.listener()
    async def on_tts_play(self, interaction: Interaction, audio: io.BytesIO):
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
        if self.bot.user not in interaction.channel.members:  # type: ignore
            voice_client = await interaction.user.voice.channel.connect()

        if not voice_client:
            return ValueError("Voice client could not be connected.")

        assert isinstance(voice_client, VoiceClient)

        if voice_client.is_playing():
            voice_client.stop()

        # Prepare audio source
        source = PCMVolumeTransformer(
            FFmpegPCMAudio(source=audio, pipe=True),
            volume=0.55,
        )

        assert interaction.channel is not None

        voice_client.play(  # type: ignore
            source=source,
        )

    @app_commands.command(description="Use custom text-to-speech server", name="speak")
    async def speak(self, interaction: Interaction, text: str):
        soundboard_cog = self.bot.get_cog("soundboard")
        if soundboard_cog is None:
            await interaction.response.send_message(
                content="Sorry, the audio player functionality has been disabled.",
                ephemeral=True,
            )
            return
        
        if isinstance(interaction.channel, DMChannel):
            await interaction.response.send_message(
                content="Sorry, you need to use this feature in a server.",
            )
            return            

        if interaction.user.voice is None:
            await interaction.response.send_message(
                content="Sorry, you need to be in a voice channel to use this feature.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        # Fetch audio clip
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.webserver_url}/voice/?script={urllib.parse.quote(text)}"
            ) as resp:
                if resp.status == 200:
                    buffer = (
                        io.BytesIO()
                    )  # Create a BytesIO buffer to store the response data
                    async for chunk in resp.content.iter_chunked(1024):
                        buffer.write(chunk)

                    buffer.seek(0)
                    self.bot.dispatch("tts_play", interaction, buffer)
                    await interaction.followup.send(
                        content=f"### {interaction.user.display_name} says: \n    {text}",
                    )

                else:
                    await interaction.followup.send(
                        content=f"Connection Issue to TTS server. Error code: {resp.status}",
                    )


async def setup(bot):
    WEBSERVER_URL = os.getenv("PIPER_WEBSERVER_URL")
    if WEBSERVER_URL:
        await bot.add_cog(PiperCog(bot, WEBSERVER_URL))


async def teardown(bot: commands.Bot):
    cog = bot.get_cog(__name__)
    if cog:
        await bot.remove_cog(cog)
