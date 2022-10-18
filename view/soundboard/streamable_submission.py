from datetime import timedelta
import time
from typing import Any
import aiohttp
import aiofiles
import os
import ffmpeg
from discord.ext import commands
from discord.ui import TextInput, Modal
from discord import Interaction


class StreamableSubmission(Modal):
    def __init__(self, bot: commands.Bot, video_url: str, file_name: str):
        super().__init__(title="Soundboard Submission")
        self.bot = bot
        self.video_url = video_url
        self.file_name = file_name
        self.bite_file_path = "data/sound_bites/"
        self.temp_file_path = "data/temp/"

    name_input: TextInput[Any] = TextInput(
        label="File Name:",
        placeholder="Enter a name for the soundbite file",
        max_length=15,
        min_length=1
    )

    start_trim_input: TextInput[Any] = TextInput(
        label="Start Time:",
        default="00:00",
        placeholder="Start = 00:00, MM:SS",
        max_length=5,
        min_length=5
    )

    end_trim_input: TextInput[Any] = TextInput(
        label="End Time:",
        default="00:00",
        placeholder="End = 00:00, MM:SS",
        max_length=5,
        min_length=5
    )

    async def on_submit(self, interaction: Interaction) -> None:
        name_input = self.name_input.value.lower()
        output = self.bite_file_path + name_input + ".mp3"
        temp_output = f"{self.temp_file_path}/{self.file_name}"
        temp_second = f"{self.temp_file_path}/temp_{self.file_name}.mp3"

        try:
            time1 = time.strptime(self.start_trim_input.value, "%M:%S")
            input1 = timedelta(minutes=time1.tm_min, seconds=time1.tm_sec).total_seconds()
            time2 = time.strptime(self.end_trim_input.value, "%M:%S")
            input2 = timedelta(minutes=time2.tm_min, seconds=time2.tm_sec).total_seconds()
            print(input1, input2)
        except ValueError:
            await interaction.response.send_message(
                "Invalid time format. Please try again.", ephemeral=True
            )
            return

        if input1 > input2:
            await interaction.response.send_message(
                content="Start time must be less than end time", ephemeral=True
            )
            return

        await interaction.response.defer()

        async with aiohttp.ClientSession() as session:
            async with session.get(self.video_url) as resp:
                if resp.status != 200:
                    return await interaction.response.send_message(
                        content="Could not download file...",
                        ephemeral=True
                    )
                else:
                    async with aiofiles.open(temp_output, mode="wb") as file_handler:
                        data = await resp.read()
                        await file_handler.write(data)

        def dl_convert() -> None:
            # Turn MP4 file into MP3
            input_file = ffmpeg.input(temp_output)
            output_file = ffmpeg.output(
                input_file,
                temp_second,
                vn=None,
                format="mp3"
            )
            audio_file = ffmpeg.run(output_file)
            # Trim MP3 file
            second_input_file = ffmpeg.input(temp_second)
            audio_file = second_input_file.filter(
                "atrim",
                start=int(input1),
                end=int(input2)
            )
            audio_file.output(output).run()
            # Clean up directories
            os.remove(temp_output)
            os.remove(temp_second)

        if not self.file_name.endswith(".mp3"):
            # https://stackoverflow.com/questions/46778936/how-to-catch-exceptions-in-a-python-run-in-executor-method-call
            # If we need to catch exceptions
            await self.bot.loop.run_in_executor(
                None,
                dl_convert
            )

        print(ffmpeg.probe(output))
        # Send message
        await interaction.followup.send(
            content=f"File saved as {name_input}!",
            ephemeral=True
        )
        self.bot.dispatch("soundboard_update", interaction)
