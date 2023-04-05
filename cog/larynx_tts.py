import os
import aiohttp
from discord import Interaction, app_commands
import discord
from discord.ext import commands

TEMP_AUDIO_PATH = "data/temp/larynx_tts.wav"

class LarynxTTS(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.base_url = os.environ["LARYNX_WEBSERVER_URL"]
        self.config = {
            "voice": "en-us/cmu_aup-glow_tts",
            #"voice": "en-us/blizzard_fls-glow_tts",
            "vocoder": "hifi_gan/vctk_small",
            "denoiserStrength": 0.003,
            "noiseScale": 0.222,
            "lengthScale": 1.2,
        }

    @commands.Cog.listener()
    async def on_tts_play(self, interaction: Interaction, audio: bytes):
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

        with open(TEMP_AUDIO_PATH, "wb") as f:
            f.write(audio)

        # Prepare audio source
        source = discord.PCMVolumeTransformer( # type: ignore
            discord.FFmpegPCMAudio(
                source=TEMP_AUDIO_PATH,  # type: ignore
            ),
            volume=0.55,

        )

        voice_client.play(  # type: ignore
            source=source,
        )


    @app_commands.command(name="speak", description="Make the bot speak")
    async def speak(
        self,
        interaction: Interaction,
        text: str,
        length: float | None = 1.2
    ):

        # Check if user is in a voice channel
        if not interaction.user.voice: # type: ignore
            await interaction.response.send_message("You are not in a voice channel")
            return
        
        await interaction.response.defer()
        
        # Create an async session
        async with aiohttp.ClientSession() as session:
        # Open an async request to the Larynx server
            full_url = f"{self.base_url}/api/tts"
            params = self.config.copy()
            params["text"] = text
            params["lengthScale"] = length
            # Necessary?
            session.headers["Content-Type"] = "audio/wav"

            async with session.get(full_url, params=params) as resp:
                # Retrieve audio file
                audio = await resp.read()
                
                if resp.status != 200:
                    await interaction.followup.send(
                        f"Something went wrong, got status: {resp.status}"
                    )
                    return
                if resp.status == 200:
                    await interaction.followup.send(
                        f"{interaction.user.display_name} said: {text}"
                    )
                    self.bot.dispatch("tts_play", interaction, audio)
                    return


async def setup(bot):
    await bot.add_cog(LarynxTTS(bot))

async def teardown(bot):
    await bot.remove_cog(LarynxTTS(bot))
