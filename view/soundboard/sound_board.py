from discord import ButtonStyle, Interaction
from discord.ext import commands
from discord.ui import Button, View

"""
Persistent View requirements:
- Timeout must be set to None
- Each component must have a unique custom_id
"""


class SoundButton(Button):
    def __init__(self, bot: commands.Bot, file_path: str):
        super().__init__()
        self.bot = bot
        self.custom_id = file_path
        self.label = file_path
        self.style = ButtonStyle.blurple

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        self.bot.dispatch("play", interaction, self.custom_id)


class SoundBoardView(View):
    def __init__(self):
        super().__init__(timeout=None)
