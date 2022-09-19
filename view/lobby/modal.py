from discord import ui
import discord


class DescriptionModal(ui.Modal, title='Edit Description'):
    def __init__(self, bot, lobby_id):
        super().__init__()
        self.bot = bot
        self.lobby_id = lobby_id

    answer = ui.TextInput(
        label='Edit Description',
        style=discord.TextStyle.paragraph,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.bot.dispatch(
            "descriptor_change",
            self.lobby_id,
            self.answer.value
        )
