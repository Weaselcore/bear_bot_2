import os
import ffmpeg
import discord
from discord.ext import commands


class UploadSubmission(discord.ui.Modal, title="Soundboard Submission"):
    def __init__(self, bot: commands.Bot, file: discord.Attachment):
        super().__init__()
        self.bot = bot
        self.file = file
        self.bite_file_path = "data/sound_bites/"
        self.temp_file_path = "data/temp/"

    name_input = discord.ui.TextInput(
        label="File Name:",
        placeholder="Enter a name for the soundbite file",
        max_length=15,
        min_length=1
    )

    async def on_submit(self, interaction: discord.Interaction):
        name_input = self.name_input.value.lower()
        output = self.bite_file_path + name_input + ".mp3"
        temp_output = f"{self.temp_file_path} + {self.file.filename}"

        def convert():
            stream = ffmpeg.input(temp_output, vn=None)
            stream = ffmpeg.output(stream, output, vn=None)
            ffmpeg.run(stream)
            os.remove(temp_output)

        if not self.file.filename.endswith(".mp3"):
            await self.file.save(temp_output)
            await self.bot.loop.run_in_executor(
                None,
                convert
            )
        else:
            await self.file.save(output)

        print(ffmpeg.probe(output))
        # Send message
        await interaction.response.send_message(
            content=f"File saved as {name_input}!",
            ephemeral=True
        )
        self.bot.dispatch("soundboard_update", interaction)
