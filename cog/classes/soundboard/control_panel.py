from discord.ui import Button, View
from discord.ext.commands import Bot
from discord import ButtonStyle, Interaction

"""
Persistent View requirements:
- Timeout must be set to None
- Each component must have a unique custom_id
"""


class StopButton(Button):

    def __init__(self, bot: Bot, view: "ControlPanelView"):
        super().__init__(
            style=ButtonStyle.red,
            label="Stop",
            custom_id="sb_stop_button",
        )
        self.bot = bot
        self.parent_view = view

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        self.bot.dispatch("stop", interaction)


class DisconnectButton(Button):

    def __init__(self, bot: Bot, view: "ControlPanelView"):
        super().__init__(
            style=ButtonStyle.red,
            label="Disconnect",
            custom_id="sb_disconnect_button",
        )
        self.bot = bot
        self.parent_view = view

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        self.bot.dispatch("disconnect", interaction)


class ControlPanelView(View):

    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(StopButton(bot, self))
        self.add_item(DisconnectButton(bot, self))


class SoundButton(Button):
    def __init__(self, bot: Bot, file_path: str):
        super().__init__()
        self.bot = bot
        self.custom_id = file_path
        self.label = file_path
        self.style = ButtonStyle.blurple

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        self.bot.dispatch("play", interaction, self.custom_id)