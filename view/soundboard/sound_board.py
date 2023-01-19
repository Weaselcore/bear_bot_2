import discord

"""
Persistent View requirements:
- Timeout must be set to None
- Each component must have a unique custom_id
"""


class SoundButton(discord.ui.Button):
    def __init__(self, bot: discord.ext.commands.Bot, file_path: str):
        super().__init__()
        self.bot = bot
        self.custom_id = file_path
        self.label = file_path
        self.style = discord.ButtonStyle.blurple

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.bot.dispatch("play", interaction, self.custom_id)


class SoundBoardView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
